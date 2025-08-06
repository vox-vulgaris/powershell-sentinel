# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# This module acts as the "brain" for the automated telemetry curation process.
# After a recent architectural pivot, this module no longer handles parsing.
# It now receives a list of already-parsed, structured TelemetryRule objects
# and uses pre-calculated statistics to recommend the most likely "golden signals".
#
# REQUIREMENTS:
# 1. Must accept a list of Pydantic `TelemetryRule` models as input.
# 2. Must annotate each rule with its corresponding rarity and relevance scores.
# 3. Must apply a heuristic to filter the rules (e.g., rarity OR relevance > threshold).
# 4. Must return a ranked list of the original `TelemetryRule` objects, sorted by relevance.

from typing import List, Dict
from pydantic import BaseModel
from powershell_sentinel.models import TelemetryRule, MitreTTPEnum

# Define static thresholds for the v0 MVP.
RARITY_THRESHOLD = 0.8
RELEVANCE_THRESHOLD = 0.75

class AnnotatedRule(BaseModel):
    """A temporary Pydantic model to hold a TelemetryRule and its calculated scores."""
    rule: TelemetryRule
    rarity_score: float = 0.0
    relevance_score: float = 0.0

def get_recommendations(
    parsed_rules: List[TelemetryRule],
    global_rarity: Dict[str, float],
    local_relevance: Dict[str, Dict[str, float]],
    primitive_ttps: List[MitreTTPEnum]
) -> List[TelemetryRule]:
    """
    Analyzes a list of pre-parsed telemetry rules and recommends the best signals
    based on statistical heuristics.

    Args:
        parsed_rules: The list of clean TelemetryRule models parsed by the manager CLI.
        global_rarity: The pre-calculated dictionary of global rarity scores.
        local_relevance: The pre-calculated nested dictionary of local relevance scores.
        primitive_ttps: The list of MitreTTPEnum members for the current primitive.

    Returns:
        A ranked list of recommended TelemetryRule objects.
    """
    # Handle the edge case of no input rules.
    if not parsed_rules:
        return []

    # [FIX] If statistics are empty (i.e., first run), return all parsed rules.
    # This is the "bootstrap" mode for the initial curation.
    is_bootstrap = not global_rarity and not local_relevance
    if is_bootstrap:
        return parsed_rules

    annotated_rules: List[AnnotatedRule] = []
    primitive_ttp_values = [ttp.value for ttp in primitive_ttps]

    # --- Step 1: Annotate each rule with its statistical scores ---
    for rule in parsed_rules:
        rule_key = rule.model_dump_json()
        rarity = global_rarity.get(rule_key, 0.0)
        
        max_relevance = 0.0
        for ttp_val in primitive_ttp_values:
            if ttp_val in local_relevance:
                relevance = local_relevance[ttp_val].get(rule_key, 0.0)
                if relevance > max_relevance:
                    max_relevance = relevance
        
        annotated_rules.append(
            AnnotatedRule(rule=rule, rarity_score=rarity, relevance_score=max_relevance)
        )

    # --- Step 2: Filter rules based on the defined thresholds ---
    recommended = [
        anno_rule for anno_rule in annotated_rules
        if anno_rule.rarity_score >= RARITY_THRESHOLD or anno_rule.relevance_score >= RELEVANCE_THRESHOLD
    ]

    # --- [NEW FALLBACK LOGIC] ---
    # If filtering removed all candidates, it means we've encountered new telemetry
    # that doesn't meet our current statistical model. In this case, we fall back
    # to showing all parsed rules so the user can curate them and improve the model.
    if not recommended:
        # We still sort the original list to be helpful, putting the most relevant ones first.
        annotated_rules.sort(key=lambda x: (x.relevance_score, x.rarity_score), reverse=True)
        return [anno_rule.rule for anno_rule in annotated_rules]
    
    # --- Step 3: Sort the filtered list to rank the best signals first ---
    recommended.sort(key=lambda x: (x.relevance_score, x.rarity_score), reverse=True)
    
    # --- Step 4: Return only the original TelemetryRule objects ---
    return [anno_rule.rule for anno_rule in recommended]
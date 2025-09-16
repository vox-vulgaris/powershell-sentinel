# Phase 2: Data Factory - Curation Tooling
# Index: [5]
#
# This module is responsible for calculating statistical metrics across the entire
# primitives knowledge base. These metrics are used by the recommendation engine
# to identify high-quality telemetry signals.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must accept a list of Pydantic `Primitive` models as input.
# 2. Must calculate Global Rarity (Inverse Primitive Frequency - IPF) for each unique `TelemetryRule`.
# 3. Must calculate Local Relevance (P(Log|Tag)) for each unique `TelemetryRule` and `MitreTTPEnum` combination.
# 4. Must return dictionaries keyed by a consistent representation of the rule and tag.

import math
from collections import defaultdict
from typing import List, Dict
from powershell_sentinel.models import Primitive, MitreTTPEnum, TelemetryRule

def calculate_global_rarity(primitives_library: List[Primitive]) -> Dict[str, float]:
    """
    Calculates the Global Rarity (IPF) for every unique TelemetryRule across all primitives.

    Args:
        primitives_library: The full list of Primitive objects.

    Returns:
        A dictionary where keys are a unique JSON string representation of a TelemetryRule
        and values are their IPF scores (e.g., log(total_primitives / count)).
    """
    
    total_primitives = len(primitives_library)
    if total_primitives == 0:
        return {}
    
    log_counts = defaultdict(int)
    for primitive in primitives_library:
        # Use a set to count each unique rule only once per primitive
        for rule in set(rule.model_dump_json() for rule in primitive.telemetry_rules):
            log_counts[rule] += 1
            
    rarity_scores = {
        log_repr: math.log(total_primitives / count)
        for log_repr, count in log_counts.items() if count > 0
    }
    
    return rarity_scores


def calculate_local_relevance(primitives_library: List[Primitive]) -> Dict[str, Dict[str, float]]:
    """
    Calculates the Local Relevance P(Log|Tag) for every log-tag combination.

    Args:
        primitives_library: The full list of Primitive objects.

    Returns:
        A nested dictionary: {mitre_ttp_string: {rule_json_string: relevance_score}}.
    """

    tag_counts = defaultdict(int)
    tag_log_counts = defaultdict(int)
    
    for primitive in primitives_library:
        unique_rules_in_primitive = {rule.model_dump_json() for rule in primitive.telemetry_rules}
        unique_tags_in_primitive = {tag.value for tag in primitive.mitre_ttps}
        
        for tag in unique_tags_in_primitive:
            tag_counts[tag] += 1
        
        for rule_repr in unique_rules_in_primitive:
            for tag in unique_tags_in_primitive:
                tag_log_counts[(tag, rule_repr)] += 1
                
    relevance_scores = defaultdict(dict)
    for (tag, rule_repr), count in tag_log_counts.items():
        if tag_counts[tag] > 0:
            relevance = count / tag_counts[tag]
            relevance_scores[tag][rule_repr] = relevance
            
    return dict(relevance_scores)
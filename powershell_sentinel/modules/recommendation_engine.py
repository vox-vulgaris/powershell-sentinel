# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# This module acts as the "brain" for the automated telemetry curation process.
# It takes the raw delta_logs from a primitive's execution and, using the
# pre-calculated statistics, recommends the most likely "golden signals".
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must accept a list of `SplunkLogEvent` models and the pre-calculated statistics as input.
# 2. Must parse raw logs to create structured `TelemetryRule` objects for lookup.
# 3. Must annotate each parseable log with its corresponding rarity and relevance scores.
# 4. Must apply a heuristic to filter the logs (e.g., rarity OR relevance > threshold).
# 5. Must return a ranked list of the original `SplunkLogEvent` objects, sorted by relevance.

from typing import List, Dict, Optional
from pydantic import BaseModel
import re
from powershell_sentinel.models import SplunkLogEvent, MitreTTPEnum, TelemetryRule

# Define static thresholds for the v0 MVP.
# These values are chosen as a starting point to balance signal and noise.
# A high rarity score suggests a log is uncommon and therefore potentially interesting.
RARITY_THRESHOLD = 0.8
# A high relevance score suggests a log is strongly correlated with a specific TTP.
RELEVANCE_THRESHOLD = 0.75

class AnnotatedLog(BaseModel):
    """
    A temporary Pydantic model to hold a log and its calculated scores.
    This provides a clean, type-safe way to manage the log and its metadata
    during the scoring and ranking process without modifying the original object.
    """
    log_event: SplunkLogEvent
    rarity_score: float = 0.0
    relevance_score: float = 0.0

def _parse_log_to_rule(log: SplunkLogEvent) -> Optional[TelemetryRule]:
    """
    Parses a raw SplunkLogEvent into a structured TelemetryRule.
    
    This is the critical translation step that bridges the gap between raw log data
    and the structured, curated data used to build our statistics. The keys in
    the statistics dictionaries are JSON strings of TelemetryRule objects, so we
    must create an identical object from the raw log to find its score.
    
    This v0 implementation uses simple regex for common, high-value event IDs.
    A more mature version could expand this with more sophisticated parsers.
    """
    raw_text = log.raw
    
    # Example parser for PowerShell Script Block Logging (Event ID 4104)
    if "EventCode=4104" in raw_text:
        # The most valuable part of an EID 4104 log is the actual script text.
        match = re.search(r"ScriptBlockText=(.*?)Message=", raw_text, re.DOTALL)
        details = match.group(1).strip() if match else "Could not parse ScriptBlockText"
        return TelemetryRule(source=log.source, event_id=4104, details=details)
        
    # Example parser for Sysmon Process Creation (Event ID 1)
    if "EventCode=1" in raw_text and log.sourcetype == "xmlwineventlog":
         # For process creation, the command line is the key detail.
        match = re.search(r"<Data Name='CommandLine'>(.*?)</Data>", raw_text)
        details = match.group(1).strip() if match else "Could not parse CommandLine"
        return TelemetryRule(source=log.source, event_id=1, details=details)

    # If the log format is unknown or doesn't match, we cannot create a rule.
    return None


def get_recommendations(
    delta_logs: List[SplunkLogEvent],
    global_rarity: Dict[str, float],
    local_relevance: Dict[str, Dict[str, float]],
    primitive_ttps: List[MitreTTPEnum]
) -> List[SplunkLogEvent]:
    """
    Analyzes delta logs and recommends the best signals based on statistical heuristics.

    Args:
        delta_logs: The list of new SplunkLogEvent models from snapshot_differ.
        global_rarity: The pre-calculated dictionary of global rarity scores.
        local_relevance: The pre-calculated nested dictionary of local relevance scores.
        primitive_ttps: The list of MitreTTPEnum members for the current primitive.

    Returns:
        A ranked list of recommended SplunkLogEvent objects.
    """
    # This list will hold our temporary AnnotatedLog objects.
    annotated_logs: List[AnnotatedLog] = []
    # Pre-calculate the string values of the TTPs for efficient lookup.
    primitive_ttp_values = [ttp.value for ttp in primitive_ttps]

    # --- Step 1: Annotate each log with its statistical scores ---
    for log in delta_logs:
        # Attempt to parse the raw log into a structured, scorable rule.
        rule = _parse_log_to_rule(log)
        
        # If the log is un-parseable, we cannot find its score. We treat its
        # scores as zero so it will likely be filtered out later.
        if rule is None:
            annotated_logs.append(
                AnnotatedLog(log_event=log, rarity_score=0.0, relevance_score=0.0)
            )
            continue

        # Create the JSON key from the parsed rule to match the statistics dictionary.
        rule_key = rule.model_dump_json()
        
        # Lookup the Global Rarity score. Default to 0.0 if not found.
        rarity = global_rarity.get(rule_key, 0.0)
        
        # Find the maximum Local Relevance score across all of the primitive's TTPs.
        # A log is highly relevant if it's strongly associated with ANY of the
        # intended malicious techniques.
        max_relevance = 0.0
        for ttp_val in primitive_ttp_values:
            if ttp_val in local_relevance:
                # Lookup the relevance for this specific log-TTP combination.
                relevance = local_relevance[ttp_val].get(rule_key, 0.0)
                if relevance > max_relevance:
                    max_relevance = relevance
        
        # Store the log and its calculated scores in our temporary list.
        annotated_logs.append(
            AnnotatedLog(log_event=log, rarity_score=rarity, relevance_score=max_relevance)
        )

    # --- Step 2: Filter logs based on the defined thresholds ---
    # The heuristic is inclusive: a log is a candidate if it's either very
    # rare OR very relevant to the primitive's intent.
    recommended = [
        anno_log for anno_log in annotated_logs
        if anno_log.rarity_score >= RARITY_THRESHOLD or anno_log.relevance_score >= RELEVANCE_THRESHOLD
    ]

    # --- Step 3: Sort the filtered list to rank the best signals first ---
    # We sort primarily by relevance (desc) and use rarity (desc) as a tie-breaker.
    # This prioritizes logs that are most indicative of the specific technique.
    recommended.sort(key=lambda x: (x.relevance_score, x.rarity_score), reverse=True)
    
    # --- Step 4: Return only the original SplunkLogEvent objects ---
    # The downstream modules only need the original log data, not the annotations.
    return [anno_log.log_event for anno_log in recommended]
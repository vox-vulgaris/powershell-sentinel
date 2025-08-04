# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# This module acts as the "brain" for the automated telemetry curation process.
# It takes the raw delta_logs from a primitive's execution and, using the
# pre-calculated statistics, recommends the most likely "golden signals".
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must accept a list of `SplunkLogEvent` models and the pre-calculated statistics as input.
# 2. Must annotate each log in the delta with its corresponding rarity and relevance scores.
# 3. Must apply a heuristic to filter the logs (e.g., rarity OR relevance > threshold).
# 4. Must return a ranked list of the original `SplunkLogEvent` objects, sorted by relevance.

from typing import List, Dict
from pydantic import BaseModel
from powershell_sentinel.models import SplunkLogEvent, MitreTTPEnum, TelemetryRule

# Define static thresholds for the v0 MVP
RARITY_THRESHOLD = 0.8
RELEVANCE_THRESHOLD = 0.75

class AnnotatedLog(BaseModel):
    """A temporary data structure to hold a log and its calculated scores."""
    log_event: SplunkLogEvent
    rarity_score: float = 0.0
    relevance_score: float = 0.0


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
    # TODO: Implement the logic.
    # 1. Initialize an empty list `annotated_logs`.
    # 2. For each log in `delta_logs`:
    #    a. Get its rarity score from `global_rarity` using `log.raw` as the key. Default to 0.
    #    b. Calculate its max relevance. Iterate through `primitive_ttps`:
    #       i. Get the tag's string value (e.g., `ttp.value`).
    #       ii. Look up the relevance score in `local_relevance`.
    #       iii. Keep track of the maximum relevance found across all tags.
    #    c. Create an `AnnotatedLog` instance with the log and its calculated scores.
    #    d. Append it to the `annotated_logs` list.
    # 3. Filter `annotated_logs` list. Keep an annotated_log if:
    #    `annotated_log.rarity_score >= RARITY_THRESHOLD` OR `annotated_log.relevance_score >= RELEVANCE_THRESHOLD`.
    # 4. Sort the filtered list in descending order based on `relevance_score`.
    # 5. Extract just the original `SplunkLogEvent` object from each sorted `AnnotatedLog`.
    # 6. Return the final list of recommended `SplunkLogEvent` objects.

    annotated_logs: List[AnnotatedLog] = []
    primitive_ttp_values = [ttp.value for ttp in primitive_ttps]

    for log in delta_logs:
        rarity = global_rarity.get(log.raw, 0.0)
        
        max_relevance = 0.0
        for ttp_val in primitive_ttp_values:
            if ttp_val in local_relevance:
                relevance = local_relevance[ttp_val].get(log.raw, 0.0)
                if relevance > max_relevance:
                    max_relevance = relevance
        
        annotated_logs.append(
            AnnotatedLog(log_event=log, rarity_score=rarity, relevance_score=max_relevance)
        )

    recommended = [
        anno_log for anno_log in annotated_logs 
        if anno_log.rarity_score >= RARITY_THRESHOLD or anno_log.relevance_score >= RELEVANCE_THRESHOLD
    ]

    # Sort by relevance first (primary), then rarity (secondary)
    recommended.sort(key=lambda x: (x.relevance_score, x.rarity_score), reverse=True)
    
    # Return only the original SplunkLogEvent objects in the recommended order
    return [anno_log.log_event for anno_log in recommended]
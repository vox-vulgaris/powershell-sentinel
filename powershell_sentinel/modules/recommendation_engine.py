# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# This module acts as the "brain" for the automated telemetry curation process.
# It takes the raw delta_logs from a primitive's execution and, using the
# pre-calculated statistics, recommends the most likely "golden signals".
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must accept a list of `delta_logs` and the pre-calculated statistics
#    (rarity and relevance) as input.
# 2. Must annotate each log in the delta with its corresponding rarity and relevance scores.
# 3. Must apply the percentile-based heuristic to filter the logs. For the v0 MVP, this can
#    be simplified to a static threshold (e.g., rarity >= 75th percentile OR relevance >= 75th percentile).
# 4. Must return a ranked list of recommended log objects (dictionaries), sorted by
#    a combined score or relevance.

def get_recommendations(delta_logs: list[dict], global_rarity: dict, local_relevance: dict, primitive_tags: list[str]) -> list[dict]:
    """
    Analyzes delta logs and recommends the best signals based on statistical heuristics.

    Args:
        delta_logs: The list of new log events from snapshot_differ.py.
        global_rarity: The pre-calculated dictionary of global rarity scores.
        local_relevance: The pre-calculated nested dictionary of local relevance scores.
        primitive_tags: The list of MITRE TTP tags associated with the current primitive.

    Returns:
        A ranked list of recommended log objects. Each object is a dictionary
        from delta_logs, potentially annotated with its scores.
    """
    # TODO: Implement the logic.
    # 1. Initialize an empty list `annotated_logs`.
    # 2. Iterate through each log in `delta_logs`.
    #    a. Create the unique, hashable representation for the current log.
    #    b. Look up its rarity score from `global_rarity`. Default to 0 if not found.
    #    c. Calculate its max relevance score. Iterate through `primitive_tags`. For each tag,
    #       look up the log's relevance in `local_relevance[tag]`. Take the maximum value found.
    #    d. Create a new dictionary for the log, adding 'rarity_score' and 'relevance_score' keys.
    #    e. Append this annotated log to `annotated_logs`.
    #
    # 3. Determine the filtering thresholds. For now, let's use a static threshold, but this
    #    could be evolved to use percentiles (e.g., np.percentile).
    #    - RARITY_THRESHOLD = 0.8
    #    - RELEVANCE_THRESHOLD = 0.75
    #
    # 4. Filter the `annotated_logs` list. Keep a log if:
    #    `log['rarity_score'] >= RARITY_THRESHOLD` OR `log['relevance_score'] >= RELEVANCE_THRESHOLD`.
    #
    # 5. Sort the filtered list to rank the best recommendations first. A good strategy is to
    #    sort by relevance score in descending order.
    #
    # 6. Return the final, sorted list of recommended logs.

    # Dummy implementation
    recommended_logs = []
    for log in delta_logs:
        # Pretend we did the scoring and filtering
        if log.get("EventID") == 4688: # Example heuristic
            log_copy = log.copy()
            log_copy['score'] = 0.95
            recommended_logs.append(log_copy)
    
    return sorted(recommended_logs, key=lambda x: x['score'], reverse=True)
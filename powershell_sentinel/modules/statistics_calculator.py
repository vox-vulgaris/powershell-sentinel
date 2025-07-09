# Phase 2: Data Factory - Curation Tooling
# Index: [5]
#
# This module is responsible for calculating statistical metrics across the entire
# primitives knowledge base. These metrics are used by the recommendation engine
# to identify high-quality telemetry signals.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must calculate Global Rarity (Inverse Primitive Frequency - IPF):
#    - How many primitives in the entire library generate a specific log event?
#    - A lower count means the log is more rare and potentially more significant.
# 2. Must calculate Local Relevance (P(Log|Tag)):
#    - Given a specific tag (e.g., a MITRE TTP like "T1057"), what is the probability
#      that a specific log event is generated?
#    - A higher probability means the log is highly relevant to that technique.
# 3. These functions will be called by `primitives_manager.py` to pre-calculate
#    and cache the statistics.

import math

def calculate_global_rarity(primitives_library: list[dict]) -> dict:
    """
    Calculates the Global Rarity (IPF) for every unique log event across all primitives.

    Args:
        primitives_library: The full list of primitive objects from primitives_library.json.

    Returns:
        A dictionary where keys are a unique representation of a log event and
        values are their IPF scores (e.g., log(total_primitives / count)).
    """
    # TODO: Implement the logic.
    # 1. Initialize a dictionary `log_counts` to store the frequency of each log.
    # 2. Iterate through each primitive in `primitives_library`.
    # 3. For each primitive, iterate through its `telemetry_rules`.
    # 4. For each rule (log), create a unique, hashable representation.
    # 5. Increment the count for that log in `log_counts`.
    # 6. After counting, iterate through `log_counts`.
    # 7. Calculate the IPF score for each log: log(total_primitives / count).
    # 8. Return the dictionary of log representations to IPF scores.

    # Dummy implementation
    return {"unique_log_repr_1": 1.5, "unique_log_repr_2": 0.8}


def calculate_local_relevance(primitives_library: list[dict]) -> dict:
    """
    Calculates the Local Relevance P(Log|Tag) for every log-tag combination.

    Args:
        primitives_library: The full list of primitive objects from primitives_library.json.

    Returns:
        A nested dictionary: {tag: {log_representation: relevance_score}}.
    """
    # TODO: Implement the logic.
    # 1. Initialize `tag_counts` (how many primitives have a certain tag).
    # 2. Initialize `tag_log_counts` (how many times a log appears with a certain tag).
    # 3. Iterate through each primitive in the library.
    #    a. For each tag in the primitive's `mitre_ttps`, increment its count in `tag_counts`.
    #    b. For each log in the primitive's `telemetry_rules`:
    #       c. For each tag in the primitive's `mitre_ttps`:
    #          d. Increment the count for that (log, tag) pair in `tag_log_counts`.
    # 4. After counting, calculate the final relevance scores:
    #    relevance = tag_log_counts[(log, tag)] / tag_counts[tag]
    # 5. Structure and return the final nested dictionary.

    # Dummy implementation
    return {
        "T1057": {"unique_log_repr_1": 0.9, "unique_log_repr_2": 0.2},
        "T1083": {"unique_log_repr_3": 0.75}
    }
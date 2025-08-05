# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# This is a pass-through utility module. In the new interactive parsing workflow,
# the parsing from raw logs into structured TelemetryRule objects happens upfront
# within the primitives_manager CLI. This module's role is simply to receive the
# final, user-selected list of TelemetryRule objects and return it, confirming
# the data is in its final, correct format before being saved.

from typing import List
from powershell_sentinel.models import TelemetryRule

def format_rules(selected_rules: List[TelemetryRule]) -> List[TelemetryRule]:
    """
    Accepts a list of selected TelemetryRule objects and returns them.

    In the current architecture, this is an identity function. It serves as a
    formal final step in the curation pipeline, ensuring the data passed to it
    is already in the desired final format.

    Args:
        selected_rules: A list of TelemetryRule models selected by the user.

    Returns:
        The same list of TelemetryRule models, ready for saving.
    """
    # In this workflow, the "formatting" is already complete.
    # The data is received in the exact format it needs to be saved in.
    return selected_rules
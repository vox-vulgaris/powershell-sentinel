# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# This is a small but crucial utility module. Its sole purpose is to take a list
# of selected raw SplunkLogEvent models and convert them into the final, clean,
# structured TelemetryRule format required for the `primitives_library.json`.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must contain a function, `format_rules`.
# 2. Must accept a list of `SplunkLogEvent` models as input.
# 3. For each log, it must parse the raw JSON to extract key details.
# 4. It must return a new list of validated `TelemetryRule` models.

import json
from typing import List, Optional
from powershell_sentinel.models import SplunkLogEvent, TelemetryRule

def _parse_raw_log(log: SplunkLogEvent) -> Optional[TelemetryRule]:
    """Helper function to parse a single raw log into a TelemetryRule."""
    try:
        # Splunk's _raw field is often a full JSON object within a string
        log_data = json.loads(log.raw)
        event_id = int(log_data.get('EventID', 0))

        # --- Rule Logic: Add more parsers here for different event IDs ---
        
        # Windows Security Auditing: Process Creation
        if event_id == 4688:
            process_name = log_data.get('NewProcessName', 'N/A').split('\\')[-1]
            command_line = log_data.get('CommandLine', 'N/A')
            return TelemetryRule(
                source="Security",
                event_id=event_id,
                details=f"Process created: {process_name} with command line: {command_line}"
            )

        # PowerShell Script Block Logging
        elif event_id == 4104:
            script_block = log_data.get('ScriptBlockText', 'N/A')
            truncated_script = (script_block[:100] + '...') if len(script_block) > 103 else script_block
            return TelemetryRule(
                source="PowerShell",
                event_id=event_id,
                details=f"Script block executed containing: '{truncated_script}'"
            )

        # Sysmon: Process Creation
        elif event_id == 1 and log.source == "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational":
            image = log_data.get('Image', 'N/A').split('\\')[-1]
            command_line = log_data.get('CommandLine', 'N/A')
            return TelemetryRule(
                source="Sysmon",
                event_id=event_id,
                details=f"Process created: {image} with command line: {command_line}"
            )
            
        # TODO: Add parsers for other important Event IDs (e.g., Sysmon EID 3, 10, 11)

    except (json.JSONDecodeError, KeyError, TypeError):
        # If the log isn't in the expected JSON format or is missing keys, skip it.
        return None
    
    return None


def format_rules(selected_logs: List[SplunkLogEvent]) -> List[TelemetryRule]:
    """
    Converts a list of raw SplunkLogEvent objects into the final structured TelemetryRule format.

    Args:
        selected_logs: A list of raw SplunkLogEvent models selected by the user or the
                       recommendation engine.

    Returns:
        A list of cleanly formatted and validated TelemetryRule models.
    """
    # TODO: Implement the logic.
    # 1. Initialize an empty list `formatted_rules`.
    # 2. Iterate through each `SplunkLogEvent` in `selected_logs`.
    # 3. Call the `_parse_raw_log` helper function for each log.
    # 4. If the helper returns a valid `TelemetryRule` object (not None),
    #    append it to the `formatted_rules` list.
    # 5. Return `formatted_rules`.

    formatted_rules = []
    for log in selected_logs:
        rule = _parse_raw_log(log)
        if rule:
            formatted_rules.append(rule)
    
    return formatted_rules
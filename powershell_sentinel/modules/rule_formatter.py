# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# This is a small but crucial utility module. Its sole purpose is to take a list
# of selected raw log events (which can be verbose and have many fields) and
# convert them into the final, clean, structured JSON format required for the
# `telemetry_rules` field in `primitives_library.json`.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must contain a function, e.g., `format_rules`.
# 2. Must accept a list of log dictionaries as input.
# 3. For each log, it must extract only the most important key-value pairs
#    (e.g., 'EventID', 'ProcessName', 'CommandLine', 'Message') to create a concise,
#    human-readable rule.
# 4. It must return a new list of these formatted rule dictionaries.

def format_rules(selected_logs: list[dict]) -> list[dict]:
    """
    Converts a list of raw log objects into the final structured telemetry_rules format.

    Args:
        selected_logs: A list of raw log dictionaries selected by the user or the
                       recommendation engine.

    Returns:
        A list of cleanly formatted rule dictionaries ready for saving.
    """
    # TODO: Implement the logic.
    # 1. Define the schema for the final rules. A good schema might include:
    #    - 'source': The log source (e.g., 'Sysmon', 'PowerShell', 'Security').
    #    - 'event_id': The Event ID.
    #    - 'details': A human-readable string summarizing the event's key details.
    #
    # 2. Initialize an empty list `formatted_rules`.
    # 3. Iterate through each log in `selected_logs`.
    # 4. Inside the loop, use a series of if/elif statements or a mapping dictionary
    #    to determine how to parse the log based on its source or EventID.
    #    - e.g., if EventID is 4688, extract 'ProcessName' and 'CommandLine'.
    #    - e.g., if EventID is 4104, extract the 'Message' or 'ScriptBlockText'.
    #    - e.g., if EventID is 1 (Sysmon ProcessCreate), extract 'Image' and 'CommandLine'.
    # 5. Construct the new, clean dictionary and append it to `formatted_rules`.
    # 6. Return `formatted_rules`.

    # Dummy implementation
    formatted_rules = []
    for log in selected_logs:
        rule = {}
        if log.get("EventID") == 4688:
            rule['source'] = 'Security'
            rule['event_id'] = 4688
            rule['details'] = f"Process created: {log.get('ProcessName')} with command line {log.get('CommandLine')}"
            formatted_rules.append(rule)
        elif log.get("EventID") == 4104:
            rule['source'] = 'PowerShell'
            rule['event_id'] = 4104
            rule['details'] = f"Script block executed containing: {log.get('Message', '')[:100]}..." # Truncate for brevity
            formatted_rules.append(rule)

    return formatted_rules
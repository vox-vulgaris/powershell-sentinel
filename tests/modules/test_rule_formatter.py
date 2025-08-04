# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# Unit tests for the rule_formatter.py module.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Test the core `format_rules` function.
# 2. Create mock `SplunkLogEvent` models as input, containing raw JSON strings
#    for different, realistic log types.
# 3. Define the exact expected output as a list of `TelemetryRule` models.
# 4. Assert that the function's output list of models exactly matches the expected models.

import unittest
import json
from powershell_sentinel.modules.rule_formatter import format_rules
from powershell_sentinel.models import SplunkLogEvent, TelemetryRule

# Helper to create dummy SplunkLogEvent objects with realistic raw JSON content
def create_splunk_log(raw_dict: dict) -> SplunkLogEvent:
    return SplunkLogEvent.model_validate({
        "_raw": json.dumps(raw_dict),
        "_time": "time",
        "source": "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational" if raw_dict.get('EventID') == 1 else "TestSource",
        "sourcetype": "st"
    })


class TestRuleFormatter(unittest.TestCase):

    def setUp(self):
        """Set up mock log data for testing."""
        self.mock_selected_logs = [
            create_splunk_log({"EventID": 4688, "NewProcessName": "C:\\Windows\\System32\\evil.exe", "CommandLine": "evil.exe -pwn"}),
            create_splunk_log({"EventID": 4104, "ScriptBlockText": "Invoke-Mimikatz"}),
            create_splunk_log({"EventID": 1, "Image": "C:\\Windows\\System32\\whoami.exe", "CommandLine": "whoami.exe"}),
            create_splunk_log({"EventID": 9999, "Details": "An unknown event type that should be ignored."})
        ]

        self.expected_rules = [
            TelemetryRule(source="Security", event_id=4688, details="Process created: evil.exe with command line: evil.exe -pwn"),
            TelemetryRule(source="PowerShell", event_id=4104, details="Script block executed containing: 'Invoke-Mimikatz'"),
            TelemetryRule(source="Sysmon", event_id=1, details="Process created: whoami.exe with command line: whoami.exe"),
        ]

    def test_format_rules(self):
        """
        Test that raw SplunkLogEvent models are correctly converted into clean TelemetryRule models.
        """
        # Act
        formatted = format_rules(self.mock_selected_logs)
        
        # Assert
        # Check that the unknown log type was correctly ignored
        self.assertEqual(len(formatted), 3)
        
        # Pydantic models with the same data are equal, so we can compare the lists directly
        self.assertCountEqual(formatted, self.expected_rules)

if __name__ == '__main__':
    unittest.main()
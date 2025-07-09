# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# Unit tests for the rule_formatter.py module.
#
# REQUIREMENTS:
# 1. Test the core `format_rules` function.
# 2. Create mock `selected_logs` input containing examples of different log types
#    (e.g., a Sysmon event, a PowerShell Script Block event).
# 3. Define the exact expected output for the formatted rules.
# 4. Assert that the function's output list of dictionaries exactly matches the expected structure and content.

import unittest
from powershell_sentinel.modules.rule_formatter import format_rules

class TestRuleFormatter(unittest.TestCase):

    def setUp(self):
        """Set up mock log data for testing."""
        self.mock_selected_logs = [
            {"EventID": 4688, "source": "Microsoft-Windows-Security-Auditing", "ProcessName": "evil.exe", "CommandLine": "evil.exe -pwn"},
            {"EventID": 4104, "source": "PowerShell", "ScriptBlockText": "Invoke-Mimikatz", "Message": "Some other details"},
            {"EventID": 1, "source": "Sysmon", "Image": "whoami.exe", "CommandLine": "whoami.exe"}
        ]

    def test_format_rules(self):
        """
        Test that raw logs are correctly converted into the clean, structured format.
        """
        # TODO: Implement the test based on the final formatting logic.
        #
        # # Act
        # formatted = format_rules(self.mock_selected_logs)
        #
        # # Assert
        # self.assertEqual(len(formatted), 3)
        #
        # # Check the first rule
        # self.assertEqual(formatted[0]['source'], 'Security')
        # self.assertEqual(formatted[0]['event_id'], 4688)
        # self.assertIn("evil.exe", formatted[0]['details'])
        #
        # # Check the second rule
        # self.assertEqual(formatted[1]['source'], 'PowerShell')
        # self.assertEqual(formatted[1]['event_id'], 4104)
        # self.assertIn("Invoke-Mimikatz", formatted[1]['details'])
        pass

if __name__ == '__main__':
    unittest.main()
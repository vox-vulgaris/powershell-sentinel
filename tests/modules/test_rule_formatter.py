# Phase 2: Data Factory - Curation Tooling
# Index: [7]
#
# Unit tests for the rule_formatter.py module.
#
# REQUIREMENTS:
# 1. Test that the `format_rules` function correctly returns the list of
#    TelemetryRule objects it was given, without modification.

import unittest
from powershell_sentinel.modules.rule_formatter import format_rules
from powershell_sentinel.models import TelemetryRule

class TestRuleFormatter(unittest.TestCase):

    def setUp(self):
        """Set up mock TelemetryRule data for testing."""
        self.mock_selected_rules = [
            TelemetryRule(source="Security", event_id=4688, details="Process created: evil.exe"),
            TelemetryRule(source="PowerShell", event_id=4104, details="Script block executed...")
        ]

    def test_format_rules_is_pass_through(self):
        """
        Test that the function returns its input list unchanged.
        """
        # Act
        formatted = format_rules(self.mock_selected_rules)

        # Assert
        # Check that the returned list is identical to the input list.
        self.assertEqual(formatted, self.mock_selected_rules)
        # Check that the objects within the list are the same.
        self.assertIs(formatted[0], self.mock_selected_rules[0])

if __name__ == '__main__':
    unittest.main()
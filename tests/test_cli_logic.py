# Phase 5: Final Deliverable & Documentation
# Index: [18]
#
# Unit tests for the deterministic, non-LLM features of the sentinel_toolkit.py CLI.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must test the logic of the "Threat Intel Lookup" feature.
# 2. It should NOT load the actual LLM.
# 3. It should use `unittest.mock` to patch the SentinelToolkit's primitives_db
#    with the data from `tests/test_data/test_cli_lookup.json`.
# 4. It should simulate user input and assert that the correct data is retrieved and printed.

# tests/test_cli_logic.py

import unittest
import json
from unittest.mock import patch, MagicMock

# Import the class to be tested and its required data models
from powershell_sentinel.sentinel_toolkit import SentinelToolkit
from powershell_sentinel.models import Primitive

class TestCliLogic(unittest.TestCase):

    def setUp(self):
        """This method is run before each test."""
        # Load the test database from a dedicated test file
        with open('tests/test_data/test_cli_lookup.json', 'r', encoding='utf-8') as f:
            self.test_primitives_data = json.load(f)
        # Convert the raw dictionary data into Pydantic models, just like the real app
        self.test_primitives = [Primitive.model_validate(p) for p in self.test_primitives_data]

    # Patch the __init__ method to prevent the real, slow model from loading during tests
    @patch('powershell_sentinel.sentinel_toolkit.SentinelToolkit.__init__', return_value=None)
    def test_threat_intel_lookup_found(self, mock_init):
        """
        Tests that the lookup feature correctly finds a known primitive and calls the display function.
        """
        # --- Arrange ---
        toolkit = SentinelToolkit(model_path=None) # __init__ is mocked, so this path is ignored
        toolkit.console = MagicMock()              # Mock the console to prevent printing to the screen
        toolkit.primitives_db = self.test_primitives # Manually inject the test database

        # Mock the display function to check if it's called, and mock user input to simulate typing "Get-Service"
        with patch.object(toolkit, '_display_primitive_report') as mock_display, \
             patch('rich.prompt.Prompt.ask', return_value='Get-Service') as mock_prompt:

            # --- Act ---
            toolkit.feature_threat_intel_lookup()

            # --- Assert ---
            mock_prompt.assert_called_once()  # Ensure the user was asked for input
            mock_display.assert_called_once() # Ensure the report display function was called

            # Check that the correct Pydantic object was passed to the display function
            called_with_primitive = mock_display.call_args[0][0]
            self.assertIsInstance(called_with_primitive, Primitive)
            self.assertEqual(called_with_primitive.primitive_command, "Get-Service")
            self.assertEqual(called_with_primitive.mitre_ttps[0].value, "T1007")
            # Check that the "found" message was printed to the console
            toolkit.console.print.assert_any_call("\n[green]Found entry for 'Get-Service':[/green]")

    @patch('powershell_sentinel.sentinel_toolkit.SentinelToolkit.__init__', return_value=None)
    def test_threat_intel_lookup_not_found(self, mock_init):
        """
        Tests that the lookup feature correctly handles a command that does not exist.
        """
        # --- Arrange ---
        toolkit = SentinelToolkit(model_path=None)
        toolkit.console = MagicMock()
        toolkit.primitives_db = self.test_primitives

        # Simulate user input for a command that is not in our test DB
        with patch.object(toolkit, '_display_primitive_report') as mock_display, \
             patch('rich.prompt.Prompt.ask', return_value='non-existent-command'):

            # --- Act ---
            toolkit.feature_threat_intel_lookup()

            # --- Assert ---
            mock_display.assert_not_called() # The display function should NOT be called
            # Check that the correct "not found" message was printed
            toolkit.console.print.assert_called_once_with("\n[yellow]No entry found for 'non-existent-command' in the primitives database.[/yellow]")

    @patch('powershell_sentinel.sentinel_toolkit.SentinelToolkit.__init__', return_value=None)
    def test_threat_intel_lookup_case_insensitivity(self, mock_init):
        """
        Tests that the lookup feature is case-insensitive as required.
        """
        # --- Arrange ---
        toolkit = SentinelToolkit(model_path=None)
        toolkit.console = MagicMock()
        toolkit.primitives_db = self.test_primitives

        # Simulate user input with mixed case
        with patch.object(toolkit, '_display_primitive_report') as mock_display, \
             patch('rich.prompt.Prompt.ask', return_value='nEt uSeR'):

            # --- Act ---
            toolkit.feature_threat_intel_lookup()

            # --- Assert ---
            mock_display.assert_called_once() # Should still find the entry
            called_with_primitive = mock_display.call_args[0][0]
            self.assertEqual(called_with_primitive.primitive_command, "net user") # Check it found the correct primitive
            self.assertEqual(called_with_primitive.mitre_ttps[0].value, "T1087.001")

if __name__ == '__main__':
    unittest.main()
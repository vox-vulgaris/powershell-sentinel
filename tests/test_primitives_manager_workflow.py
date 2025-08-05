# tests/test_primitives_manager_workflow.py
# Phase 3: The Curation Controller, Dataset Expansion & Validation
# Index: [8]
#
# This is an integration test for the PrimitivesManager CLI. It validates the
# full end-to-end workflow for telemetry curation, focusing on the new
# interactive parsing feature.
#
# REQUIREMENTS:
# 1. Test the `run_telemetry_curation` method.
# 2. Use a temporary file system to ensure tests are isolated and clean.
# 3. Use `unittest.mock.patch` to simulate user input from the CLI prompts.
# 4. Assert that a new parsing rule is created and saved when an unknown log is found.
# 5. Assert that the primitive is correctly updated with the newly parsed rule.

import unittest
import json
import tempfile
import os
from unittest.mock import patch

from powershell_sentinel.primitives_manager import PrimitivesManager
from powershell_sentinel.models import SplunkLogEvent, ParsingRule, ExtractionMethodEnum, TelemetryRule

class TestPrimitivesManagerWorkflow(unittest.TestCase):

    def setUp(self):
        """Create a temporary file system and mock data for a clean test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.parsing_rules_path = os.path.join(self.temp_dir.name, "parsing_rules.json")
        self.deltas_path = os.path.join(self.temp_dir.name, "deltas")
        os.makedirs(self.deltas_path)

        # Create a simple starting primitives library
        with open(self.primitives_path, 'w') as f:
            json.dump([{"primitive_id": "PS-999", "primitive_command": "test", "intent": ["Process Discovery"], "mitre_ttps": ["T1057"], "telemetry_rules": []}], f)
        
        # Start with an empty parsing rules file
        with open(self.parsing_rules_path, 'w') as f:
            json.dump([], f)
        
        # Create a mock delta log file with an unknown log type
        mock_log_content = 'EventCode=11 TargetFilename=secret.txt'
        mock_log = SplunkLogEvent.model_validate({"_raw": mock_log_content, "_time": "t", "source": "TestSource", "sourcetype": "Sysmon"})
        
        with open(os.path.join(self.deltas_path, "PS-999.json"), 'w') as f:
            json.dump([mock_log.model_dump(by_alias=True)], f)

    def tearDown(self):
        """Clean up the temporary directory and files after the test."""
        self.temp_dir.cleanup()

    # Patch the recommendation engine to simplify this test's focus.
    # We also patch the CLI prompts to simulate user input.
    @patch('powershell_sentinel.primitives_manager.recommendation_engine.get_recommendations')
    @patch('rich.prompt.Confirm.ask', return_value=True)
    @patch('rich.prompt.Prompt.ask')
    def test_curation_creates_new_parsing_rule(self, mock_prompt_ask, mock_confirm_ask, mock_get_recommendations):
        """
        Tests the full curation workflow, ensuring the interactive parsing prompt
        is triggered for an unknown log and that the system learns from the input.
        """
        # --- Arrange ---
        # 1. Mock the user's answers to the interactive prompts.
        mock_prompt_ask.side_effect = [
            "Sysmon-FileCreate-Test",  # rule_name
            "11",                      # event_id
            "key_value",               # extraction_method
            "TargetFilename",          # detail_key_or_pattern
            "all",                     # Accept all recommendations
        ]
        # 2. Mock the recommender to return the rule we expect to be parsed.
        expected_rule = TelemetryRule(source="TestSource", event_id=11, details="secret.txt")
        mock_get_recommendations.return_value = [expected_rule]


        # --- Act ---
        # Instantiate the manager pointing to our temporary test files and run curation.
        manager = PrimitivesManager(
            primitives_path=self.primitives_path,
            parsing_rules_path=self.parsing_rules_path,
            deltas_path=self.deltas_path
        )
        manager.run_telemetry_curation()

        # --- Assert ---
        # 1. Verify that a new parsing rule was created and saved to disk.
        with open(self.parsing_rules_path, 'r') as f:
            saved_rules = json.load(f)
        self.assertEqual(len(saved_rules), 1)
        self.assertEqual(saved_rules[0]['event_id'], 11)
        self.assertEqual(saved_rules[0]['detail_key_or_pattern'], "TargetFilename") # Correct field name

        # 2. Verify that the primitive in memory was updated with the new, parsed rule.
        updated_primitive = manager.primitives[0]
        self.assertEqual(len(updated_primitive.telemetry_rules), 1)
        self.assertEqual(updated_primitive.telemetry_rules[0].details, "secret.txt")
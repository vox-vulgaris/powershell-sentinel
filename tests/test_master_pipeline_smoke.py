# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [12]
#
# This is an End-to-End (E2E) "Smoke Test" for the main_data_factory.py script.
# Its purpose is not to check the content in detail, but to answer one simple question:
# "Does the factory turn on and produce something without crashing?"
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must call the main `generate_dataset` function from the master controller.
# 2. Must run it for a very small batch (e.g., 5 pairs).
# 3. Must use mock versions of the `lab_connector` and `obfuscator` to prevent
#    real network calls and complex execution validation during this test.
# 4. Must assert that the process completes successfully.
# 5. Must assert that a final dataset file was created and contains the correct number of pairs.

import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# [FIX] Import the necessary functions and models
from powershell_sentinel.main_data_factory import generate_dataset
from powershell_sentinel.models import CommandOutput

class TestMasterPipelineSmoke(unittest.TestCase):

    def setUp(self):
        """
        [REFACTOR] Use a temporary directory for true test isolation.
        """
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.output_path = os.path.join(self.temp_dir.name, "output.json")
        
        # [FIX] The mock primitive MUST have telemetry_rules to be considered "usable" by the factory.
        mock_primitives = [{
            "primitive_id": "PS-001",
            "primitive_command": "Get-Process",
            "intent": ["Process Discovery"],
            "mitre_ttps": ["T1057"],
            "telemetry_rules": [{"source": "A", "event_id": 1, "details": "B"}]
        }]
        with open(self.primitives_path, 'w') as f:
            json.dump(mock_primitives, f)

    def tearDown(self):
        """Clean up the temporary directory and its contents."""
        self.temp_dir.cleanup()

    @patch('powershell_sentinel.main_data_factory.LabConnection')
    @patch('powershell_sentinel.main_data_factory.generate_layered_obfuscation')
    def test_smoke_run_completes_successfully(self, mock_obfuscator, mock_lab_connection):
        """
        E2E smoke test to ensure the main data factory pipeline runs without errors for a small batch.
        """
        # --- Arrange: Configure mocks to always "succeed" ---
        
        # Mock the obfuscator to return a consistent, simple value.
        mock_obfuscator.return_value = ("obfuscated_cmd", ["obfuscate_concat"])
        
        # Mock the lab connector to return a successful CommandOutput Pydantic model.
        mock_lab_instance = mock_lab_connection.return_value
        mock_lab_instance.run_remote_powershell.return_value = CommandOutput(
            return_code=0, 
            stdout='Success', 
            stderr=''
        )
        
        # --- Act ---
        target_count = 5
        generate_dataset(target_count, self.primitives_path, self.output_path)
        
        # --- Assert ---
        
        # 1. Check that the output file was created.
        self.assertTrue(os.path.exists(self.output_path))
        
        # 2. Check that the file contains the correct number of pairs.
        with open(self.output_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), target_count)

        # 3. Spot-check the first generated pair for correct structure.
        self.assertIn("prompt", data[0])
        self.assertEqual(data[0]['prompt'], "obfuscated_cmd")
        self.assertIn("response", data[0])
        self.assertEqual(data[0]['response']['deobfuscated_command'], "Get-Process")


if __name__ == '__main__':
    unittest.main()
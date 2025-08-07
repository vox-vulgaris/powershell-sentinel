# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [12]

import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# Import the necessary functions and models
from powershell_sentinel.main_data_factory import generate_dataset
from powershell_sentinel.models import CommandOutput

class TestMasterPipelineSmoke(unittest.TestCase):

    def setUp(self):
        """Use a temporary directory for true test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.output_path = os.path.join(self.temp_dir.name, "output.json")
        
        # The mock primitive MUST have telemetry_rules to be considered "usable".
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
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    @patch('powershell_sentinel.main_data_factory.LabConnection')
    @patch('powershell_sentinel.main_data_factory.generate_layered_obfuscation')
    def test_smoke_run_completes_successfully(self, mock_obfuscator, mock_lab_connection):
        """
        E2E smoke test to ensure the main data factory pipeline runs without errors.
        """
        # --- Arrange: Configure mocks to always "succeed" ---
        
        mock_obfuscator.return_value = ("obfuscated_cmd", ["obfuscate_concat"])
        
        mock_lab_instance = mock_lab_connection.return_value
        
        # [DEFINITIVE FIX] The mock CommandOutput object MUST be created using the
        # aliased, PowerShell-style field names (PascalCase) to pass validation.
        mock_lab_instance.run_remote_powershell.return_value = CommandOutput(
            ReturnCode=0, 
            Stdout='Success', 
            Stderr=''
        )
        
        # --- Act ---
        target_count = 5
        generate_dataset(target_count, self.primitives_path, self.output_path)
        
        # --- Assert ---
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), target_count)
        self.assertEqual(data[0]['prompt'], "obfuscated_cmd")
        self.assertEqual(data[0]['response']['deobfuscated_command'], "Get-Process")


if __name__ == '__main__':
    unittest.main()
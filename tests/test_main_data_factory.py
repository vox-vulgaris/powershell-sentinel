# tests/test_main_data_factory.py

import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

from powershell_sentinel.main_data_factory import generate_dataset
from powershell_sentinel.models import CommandOutput
from scripts.verify_lab_config import parse_winrm_output


class TestMainDataFactoryLogic(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.output_path = os.path.join(self.temp_dir.name, "output.json")
        
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
        self.temp_dir.cleanup()

    @patch('powershell_sentinel.main_data_factory.PROPHYLACTIC_RESET_INTERVAL', 10)
    @patch('powershell_sentinel.main_data_factory.LabConnection')
    @patch('powershell_sentinel.main_data_factory.generate_layered_obfuscation')
    def test_prophylactic_reset_is_triggered(self, mock_obfuscator, mock_lab_connection):
        mock_obfuscator.return_value = ("obfuscated_cmd", ["chain"])
        mock_lab_instance = mock_lab_connection.return_value
        mock_lab_instance.run_remote_powershell.return_value = CommandOutput(
            ReturnCode=0, 
            Stdout='Success', 
            Stderr=''
        )
        target_count = 11
        generate_dataset(target_count, self.primitives_path, self.output_path)
        mock_lab_instance.reset_shell.assert_called_once()


class TestLabConfigVerifier(unittest.TestCase):

    def test_parse_winrs_output_success(self):
        sample_output = "MaxMemoryPerShellMB = 1024\nMaxShellsPerUser = 50"
        parsed = parse_winrm_output(sample_output)
        self.assertEqual(parsed.get("MaxShellsPerUser"), 50)

    def test_parse_empty_or_malformed_output(self):
        self.assertEqual(parse_winrm_output(""), {})
        self.assertEqual(parse_winrm_output(None), {})

if __name__ == '__main__':
    unittest.main()
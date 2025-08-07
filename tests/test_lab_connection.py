# tests/test_lab_connection.py

import unittest
import json
import base64 # [NEW] Import base64 to create a valid mock command
from unittest.mock import patch, MagicMock

from powershell_sentinel.models import CommandOutput, SplunkLogEvent

with patch.dict('os.environ', {
    'VICTIM_VM_IP': '1.2.3.4',
    'VICTIM_VM_USER': 'testuser',
    'VICTIM_VM_PASS': 'testpass',
    'SPLUNK_PASS': 'splunkpass'
}):
    from powershell_sentinel.lab_connector import LabConnection

class TestLabConnection(unittest.TestCase):

    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_run_remote_powershell_success(self, mock_protocol, mock_splunk_connect):
        """Tests that run_remote_powershell correctly parses the JSON wrapper output."""
        mock_winrm_instance = mock_protocol.return_value
        fake_shell_id = 'SHELL_ID_12345'
        mock_winrm_instance.open_shell.return_value = fake_shell_id
        
        # [DEFINITIVE FIX] The mock must now return a valid JSON payload,
        # just like our real PowerShell wrapper does.
        mock_response_dict = {
            "Stdout": "SuccessOutput",
            "Stderr": "",
            "ReturnCode": 0,
            "TimedOut": False
        }
        # Convert dict to JSON string, then encode to bytes for the transport layer mock.
        mock_response_bytes = json.dumps(mock_response_dict).encode('utf-8')

        mock_winrm_instance.run_command.return_value = 'COMMAND_ID_67890'
        mock_winrm_instance.get_command_output.return_value = (mock_response_bytes, b'', 0)

        lab_conn = LabConnection()
        result = lab_conn.run_remote_powershell("Get-Process")
        
        # Assert that the correct final command was constructed and sent
        mock_winrm_instance.run_command.assert_called_once()
        call_args = mock_winrm_instance.run_command.call_args[0]
        self.assertEqual(call_args[0], fake_shell_id) # Check shell ID
        self.assertEqual(call_args[1], 'powershell.exe') # Check executable
        self.assertIn('-EncodedCommand', call_args[2]) # Check for the correct switch

        # Assert that the JSON was parsed correctly and the CommandOutput model is correct
        self.assertIsInstance(result, CommandOutput)
        self.assertEqual(result.stdout, 'SuccessOutput')
        self.assertEqual(result.return_code, 0)

    @patch('powershell_sentinel.lab_connector.results.JSONResultsReader')
    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_query_splunk_success(self, mock_protocol, mock_splunk_connect, mock_json_reader):
        """Tests that query_splunk correctly processes data from a mocked JSONResultsReader."""
        # --- This test was already correct and needs no changes ---
        mock_service = mock_splunk_connect.return_value
        mock_job = MagicMock()
        mock_service.jobs.create.return_value = mock_job
        mock_dict_results = [
            {'_raw': 'log1', '_time': '2025-08-04T21:00:00.000+00:00', 'source': 'test.log', 'sourcetype': 'test'},
            {'_raw': 'log2', '_time': '2025-08-04T21:00:01.000+00:00', 'source': 'test.log', 'sourcetype': 'test'}
        ]
        mock_json_reader.return_value = mock_dict_results
        
        lab_conn = LabConnection()
        results_list = lab_conn.query_splunk("search index=main")
        
        mock_service.jobs.create.assert_called_once()
        self.assertEqual(len(results_list), 2)
        self.assertEqual(results_list[0].raw, 'log1')

if __name__ == '__main__':
    unittest.main()
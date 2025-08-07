# tests/test_lab_connection.py

import unittest
from unittest.mock import patch, MagicMock

from powershell_sentinel.models import CommandOutput, SplunkLogEvent

# This setup is still required to allow the module to be imported
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
        """Tests that run_remote_powershell correctly executes a command and returns its raw output."""
        # --- Arrange ---
        mock_winrm_instance = mock_protocol.return_value
        fake_shell_id = 'SHELL_ID_12345'
        fake_command_id = 'COMMAND_ID_67890'
        
        mock_winrm_instance.open_shell.return_value = fake_shell_id
        mock_winrm_instance.run_command.return_value = fake_command_id
        
        # [DEFINITIVE FIX] The mock now returns simple bytes, just like the real pywinrm library.
        # No more JSON.
        mock_winrm_instance.get_command_output.return_value = (b'SuccessOutput\r\n', b'', 0)

        # --- Act ---
        lab_conn = LabConnection()
        result = lab_conn.run_remote_powershell("Get-Process")
        
        # --- Assert ---
        # Assert that the raw command was passed directly to the protocol
        mock_winrm_instance.run_command.assert_called_once_with(fake_shell_id, "Get-Process")
        mock_winrm_instance.get_command_output.assert_called_once_with(fake_shell_id, fake_command_id)
        
        # Assert that the output model is correctly formed from the raw bytes
        self.assertIsInstance(result, CommandOutput)
        self.assertEqual(result.stdout, 'SuccessOutput')
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.return_code, 0)

    # This test was already correct and needs no changes, but is included for completeness.
    @patch('powershell_sentinel.lab_connector.results.JSONResultsReader')
    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_query_splunk_success(self, mock_protocol, mock_splunk_connect, mock_json_reader):
        """Tests that query_splunk correctly processes data from a mocked JSONResultsReader."""
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
# tests/test_lab_connection.py

import unittest
import json
from unittest.mock import patch, MagicMock

MOCK_ENV = {
    'VICTIM_VM_IP': '1.2.3.4',
    'VICTIM_VM_USER': 'testuser',
    'VICTIM_VM_PASS': 'testpass',
    'SPLUNK_PASS': 'splunkpass'
}

with patch.dict('os.environ', MOCK_ENV, clear=True):
    from powershell_sentinel.lab_connector import LabConnection
    from powershell_sentinel.models import CommandOutput, SplunkLogEvent

class TestLabConnection(unittest.TestCase):

    def setUp(self):
        self.connect_winrm_patcher = patch('powershell_sentinel.lab_connector.LabConnection._connect_winrm')
        self.connect_splunk_patcher = patch('powershell_sentinel.lab_connector.LabConnection._connect_splunk')
        self.mock_connect_winrm = self.connect_winrm_patcher.start()
        self.mock_connect_splunk = self.connect_splunk_patcher.start()
        self.addCleanup(self.connect_winrm_patcher.stop)
        self.addCleanup(self.connect_splunk_patcher.stop)

    def test_run_remote_powershell_success(self):
        lab = LabConnection()
        lab.winrm_protocol = MagicMock()
        lab.shell_id = 'mock_shell_id'
        
        mock_response_dict = {"Stdout": "Success", "Stderr": "", "ReturnCode": 0}
        mock_response_bytes = json.dumps(mock_response_dict).encode('utf-8')
        lab.winrm_protocol.get_command_output.return_value = (mock_response_bytes, b'', 0)

        result = lab.run_remote_powershell("hostname")

        lab.winrm_protocol.run_command.assert_called_once()
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "Success")

    def test_run_remote_powershell_failure(self):
        lab = LabConnection()
        lab.winrm_protocol = MagicMock()
        lab.shell_id = 'mock_shell_id'
        
        mock_response_dict = {"Stdout": "", "Stderr": "command not found", "ReturnCode": 1}
        mock_response_bytes = json.dumps(mock_response_dict).encode('utf-8')
        lab.winrm_protocol.get_command_output.return_value = (mock_response_bytes, b'', 0)
        
        result = lab.run_remote_powershell("invalid-command")
        
        lab.winrm_protocol.run_command.assert_called_once()
        self.assertEqual(result.return_code, 1)
        self.assertEqual(result.stderr, "command not found")

    @patch('powershell_sentinel.lab_connector.results.JSONResultsReader')
    def test_query_splunk_success(self, mock_json_reader):
        lab = LabConnection()
        lab.splunk_service = MagicMock()
        mock_job = MagicMock()
        lab.splunk_service.jobs.create.return_value = mock_job
        mock_json_reader.return_value = [{'_raw': 'log1', '_time': 'time', 'source': 's', 'sourcetype': 'st'}]
        
        results = lab.query_splunk("search *")
            
        self.assertEqual(len(results), 1)

if __name__ == '__main__':
    unittest.main()
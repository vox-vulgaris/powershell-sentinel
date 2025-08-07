# tests/test_lab_connection.py

import unittest
import json
from unittest.mock import patch, MagicMock

# Define MOCK_ENV at the module level
MOCK_ENV = {
    'VICTIM_VM_IP': '1.2.3.4',
    'VICTIM_VM_USER': 'testuser',
    'VICTIM_VM_PASS': 'testpass',
    'SPLUNK_PASS': 'splunkpass'
}

with patch.dict('os.environ', MOCK_ENV, clear=True):
    # This ensures that when the test runner imports these modules,
    # they see our mocked environment variables.
    from powershell_sentinel.lab_connector import LabConnection
    from powershell_sentinel.models import CommandOutput, SplunkLogEvent

class TestLabConnection(unittest.TestCase):

    def setUp(self):
        """Set up patches for each test to ensure isolation."""
        self.connect_winrm_patcher = patch('powershell_sentinel.lab_connector.LabConnection._connect_winrm')
        self.connect_splunk_patcher = patch('powershell_sentinel.lab_connector.LabConnection._connect_splunk')
        self.mock_connect_winrm = self.connect_winrm_patcher.start()
        self.mock_connect_splunk = self.connect_splunk_patcher.start()
        self.addCleanup(self.connect_winrm_patcher.stop)
        self.addCleanup(self.connect_splunk_patcher.stop)

    def test_run_remote_powershell_success(self):
        """[FIXED] Tests that a successful command returns a correct, parsed CommandOutput object."""
        lab = LabConnection()
        lab.winrm_protocol = MagicMock()
        lab.shell_id = 'mock_shell_id'
        
        # [FIXED] The mock MUST use the PowerShell-style keys (PascalCase) for validation.
        mock_response_dict = {"Stdout": "Success", "Stderr": "", "ReturnCode": 0}
        mock_response_bytes = json.dumps(mock_response_dict).encode('utf-8')
        lab.winrm_protocol.get_command_output.return_value = (mock_response_bytes, b'', 0)

        result = lab.run_remote_powershell("hostname")

        lab.winrm_protocol.run_command.assert_called_once()
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "Success")
        self.assertEqual(result.stderr, "")

    def test_run_remote_powershell_failure(self):
        """[FIXED] Tests that a failed command returns a correct, parsed CommandOutput object."""
        lab = LabConnection()
        lab.winrm_protocol = MagicMock()
        lab.shell_id = 'mock_shell_id'
        
        # [FIXED] Mock a response where our wrapper detected an internal script failure.
        mock_response_dict = {"Stdout": "", "Stderr": "command not found", "ReturnCode": 1}
        mock_response_bytes = json.dumps(mock_response_dict).encode('utf-8')
        lab.winrm_protocol.get_command_output.return_value = (mock_response_bytes, b'', 0)
        
        result = lab.run_remote_powershell("invalid-command")
        
        lab.winrm_protocol.run_command.assert_called_once()
        self.assertEqual(result.return_code, 1)
        self.assertEqual(result.stderr, "command not found")

    @patch('powershell_sentinel.lab_connector.results.JSONResultsReader')
    def test_query_splunk_success(self, mock_json_reader):
        """Tests a successful Splunk query."""
        lab = LabConnection()
        lab.splunk_service = MagicMock()
        mock_job = MagicMock()
        lab.splunk_service.jobs.create.return_value = mock_job
        mock_json_reader.return_value = [{'_raw': 'log1', '_time': 'time', 'source': 's', 'sourcetype': 'st'}]
        
        results = lab.query_splunk("search *")
            
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].raw, 'log1')

if __name__ == '__main__':
    unittest.main()
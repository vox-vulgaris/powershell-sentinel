# Phase 1: Foundation & Lab Setup
# Index: [3]
#
# This file contains the unit tests for the `lab_connector.py` module. [cite: 122]
# The primary purpose of these tests is to ensure that the connection logic
# is correctly structured and that it handles inputs and outputs as expected,
# WITHOUT making actual network calls during automated testing.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Use the `unittest.mock` library to patch the `winrm` and `splunklib` modules. 
# 2. Test that the `run_remote_powershell` function correctly calls the underlying WinRM library method. 
# 3. Test that the `query_splunk` function correctly calls the underlying Splunk SDK method. 
# 4. (Optional but recommended) Include a separate, clearly marked integration test that can be
#    run manually to verify actual connectivity to the configured lab environment.

# tests/test_lab_connection.py

import unittest
from unittest.mock import patch, MagicMock

# Import the Pydantic models we will be testing against
from powershell_sentinel.models import CommandOutput, SplunkLogEvent

# We need to set mock environment variables BEFORE the module is imported.
with patch.dict('os.environ', {
    'VICTIM_VM_IP': '1.2.3.4',
    'VICTIM_VM_USER': 'testuser',
    'VICTIM_VM_PASS': 'testpass',
    'SPLUNK_PASS': 'splunkpass'
}):
    # Import the class AFTER setting the mock environment
    from powershell_sentinel.lab_connector import LabConnection

class TestLabConnection(unittest.TestCase):

    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_run_remote_powershell_success(self, mock_protocol, mock_splunk_connect):
        """
        Test that run_remote_powershell correctly uses the multi-step WinRM
        process and returns a valid CommandOutput Pydantic model on success.
        """
        # --- Arrange: Configure the mock for the multi-step WinRM execution ---
        mock_winrm_instance = mock_protocol.return_value
        
        # Define the return values for each step in the new execution flow
        fake_shell_id = 'SHELL_ID_12345'
        fake_command_id = 'COMMAND_ID_67890'
        fake_stdout = b'SuccessOutput\r\n'
        fake_stderr = b''
        fake_return_code = 0

        mock_winrm_instance.open_shell.return_value = fake_shell_id
        mock_winrm_instance.run_command.return_value = fake_command_id
        mock_winrm_instance.get_command_output.return_value = (fake_stdout, fake_stderr, fake_return_code)

        lab_conn = LabConnection()
        command_to_run = "Get-Process"
        
        # --- Act: Run the method ---
        result = lab_conn.run_remote_powershell(command_to_run)
        
        # --- Assert: Verify the logic and the returned model ---
        # Verify that the entire multi-step process was called correctly
        mock_winrm_instance.open_shell.assert_called_once()
        mock_winrm_instance.run_command.assert_called_once_with(fake_shell_id, 'powershell.exe', ['-Command', command_to_run])
        mock_winrm_instance.get_command_output.assert_called_once_with(fake_shell_id, fake_command_id)
        mock_winrm_instance.cleanup_command.assert_called_once_with(fake_shell_id, fake_command_id)
        mock_winrm_instance.close_shell.assert_called_once_with(fake_shell_id)

        # Assert that the result is a Pydantic model with the correct data
        self.assertIsInstance(result, CommandOutput)
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, 'SuccessOutput') # Also tests that output is decoded and stripped
        self.assertEqual(result.stderr, '')

    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_query_splunk_success(self, mock_protocol, mock_splunk_connect):
        """
        Test that query_splunk correctly calls the splunk-sdk and
        returns a list of valid SplunkLogEvent Pydantic models.
        """
        # --- Arrange: Configure the mock service and job ---
        mock_service = mock_splunk_connect.return_value
        mock_job = MagicMock()
        
        # Create mock log data that will pass Pydantic validation
        mock_dict_results = [
            {'_raw': 'log1', '_time': '2025-08-04T21:00:00.000+00:00', 'source': 'test.log', 'sourcetype': 'test'},
            {'_raw': 'log2', '_time': '2025-08-04T21:00:01.000+00:00', 'source': 'test.log', 'sourcetype': 'test'}
        ]
        
        # Patch the ResultsReader to return our list of dictionaries
        with patch('splunklib.results.ResultsReader', return_value=mock_dict_results):
            mock_service.jobs.create.return_value = mock_job
            
            lab_conn = LabConnection()
            search_query = "search index=main"
            
            # --- Act: Run the method ---
            results_list = lab_conn.query_splunk(search_query)
            
            # --- Assert: Verify the logic and the returned models ---
            # Verify the job was created with the correct query and execution mode
            mock_service.jobs.create.assert_called_once_with(search_query, exec_mode="blocking", output_mode="json")
            
            # Assert that we received a list of Pydantic models with the correct data
            self.assertEqual(len(results_list), 2)
            self.assertIsInstance(results_list[0], SplunkLogEvent)
            self.assertEqual(results_list[0].raw, 'log1')
            self.assertEqual(results_list[1].sourcetype, 'test')
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

import unittest
from unittest.mock import patch, MagicMock, mock_open

# We need to set mock environment variables BEFORE the module is imported.
with patch.dict('os.environ', {
    'VICTIM_VM_IP': '1.2.3.4',
    'VICTIM_VM_USER': 'testuser',
    'VICTIM_VM_PASS': 'testpass',
    'SPLUNK_PASS': 'splunkpass'
}):
    from powershell_sentinel.lab_connector import LabConnection

class TestLabConnection(unittest.TestCase):

    # Patch the entire winrm.Protocol class and splunklib.client.connect function
    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_run_remote_powershell_success(self, mock_protocol, mock_splunk_connect):
        """
        Test that run_remote_powershell correctly calls the winrm library
        and returns the expected dictionary on success.
        """
        # TODO: This test needs to be properly implemented once LabConnection is built.
        # IMPLEMENTATION: The test is now fully implemented.
        
        # Arrange: Configure the mock to return a specific result
        # The return_value of the patch is the mock instance of the Protocol class
        mock_winrm_instance = mock_protocol.return_value
        
        # The run_ps method returns an object with attributes, so we use MagicMock
        mock_winrm_instance.run_ps.return_value = MagicMock(
            std_out=b'SuccessOutput\r\n', # Include carriage returns to test stripping
            std_err=b'',
            status_code=0
        )
        
        lab_conn = LabConnection()
        command_to_run = "Get-Process"
        
        # Act
        result = lab_conn.run_remote_powershell(command_to_run)
        
        # Assert
        # Verify that the run_ps method on our mocked instance was called exactly once with our command
        mock_winrm_instance.run_ps.assert_called_once_with(command_to_run)
        self.assertEqual(result['return_code'], 0)
        self.assertEqual(result['stdout'], 'SuccessOutput') # Also tests that output is decoded and stripped
        self.assertEqual(result['stderr'], '')


    @patch('splunklib.client.connect')
    @patch('winrm.Protocol')
    def test_query_splunk_success(self, mock_protocol, mock_splunk_connect):
        """
        Test that query_splunk correctly calls the splunk-sdk and
        returns a list of results.
        """
        # TODO: This test needs to be properly implemented once LabConnection is built.
        # IMPLEMENTATION: The test is now fully implemented.

        # Arrange: Configure the mock service and job
        mock_service = mock_splunk_connect.return_value
        mock_job = MagicMock()
        
        # Mock the results() method of the job object to return an iterable with our fake logs
        mock_results_reader = [
            {'_raw': 'log1', 'sourcetype': 'WinEventLog:Security'},
            {'_raw': 'log2', 'sourcetype': 'WinEventLog:Security'}
        ]
        # We patch the splunklib.results.ResultsReader to return our list directly
        with patch('splunklib.results.ResultsReader', return_value=mock_results_reader):
            mock_service.jobs.create.return_value = mock_job
            
            lab_conn = LabConnection()
            search_query = "search index=main"
            
            # Act
            results_list = lab_conn.query_splunk(search_query)
            
            # Assert
            # Verify the job was created with the correct query and execution mode
            mock_service.jobs.create.assert_called_once_with(search_query, exec_mode="blocking", output_mode="json")
            self.assertEqual(len(results_list), 2)
            self.assertEqual(results_list, mock_results_reader)

# To run tests from the command line from the project root:
# python -m unittest discover tests
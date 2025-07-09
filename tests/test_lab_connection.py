# Phase 1: Foundation & Lab Setup
# Index: [3]
#
# This file contains the unit tests for the `lab_connector.py` module.
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
from unittest.mock import patch, MagicMock

# Import the class/functions from the module we are testing
# from powershell_sentinel.lab_connector import LabConnection

class TestLabConnection(unittest.TestCase):

    @patch('winrm.Protocol')
    def test_run_remote_powershell_success(self, mock_protocol):
        """
        Test that run_remote_powershell correctly calls the winrm library
        and returns the expected dictionary on success.
        """
        # TODO: This test needs to be properly implemented once LabConnection is built.
        #
        # # Arrange: Configure the mock to return a specific result
        # mock_instance = mock_protocol.return_value
        # mock_instance.run_ps.return_value = MagicMock(
        #     std_out=b'SuccessOutput',
        #     std_err=b'',
        #     status_code=0
        # )
        #
        # lab_conn = LabConnection()
        # command_to_run = "Get-Process"
        #
        # # Act
        # result = lab_conn.run_remote_powershell(command_to_run)
        #
        # # Assert
        # mock_instance.run_ps.assert_called_once_with(command_to_run)
        # self.assertEqual(result['return_code'], 0)
        # self.assertEqual(result['stdout'], 'SuccessOutput')
        # self.assertEqual(result['stderr'], '')
        pass


    @patch('splunklib.client.connect')
    def test_query_splunk_success(self, mock_connect):
        """
        Test that query_splunk correctly calls the splunk-sdk and
        returns a list of results.
        """
        # TODO: This test needs to be properly implemented once LabConnection is built.
        #
        # # Arrange: Configure the mock service and job
        # mock_service = mock_connect.return_value
        # mock_job = MagicMock()
        # mock_results = [{'raw': 'log1'}, {'raw': 'log2'}]
        # mock_job.results.return_value = mock_results
        # mock_service.jobs.create.return_value = mock_job
        #
        # lab_conn = LabConnection()
        # search_query = "search index=main"
        #
        # # Act
        # results = lab_conn.query_splunk(search_query)
        #
        # # Assert
        # mock_service.jobs.create.assert_called_once_with(search_query, exec_mode="blocking")
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results, mock_results)
        pass

# To run tests from the command line from the project root:
# python -m unittest discover tests
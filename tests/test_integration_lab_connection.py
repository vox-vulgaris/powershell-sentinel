# tests/test_integration_lab_connection.py

import unittest
import os
import time
import uuid
import json

# This decorator will skip these tests unless the environment variable
# 'RUN_INTEGRATION_TESTS' is set to a non-empty value (e.g., '1' or 'true').
# This prevents the slow, network-dependent tests from running by default.
@unittest.skipIf(not os.environ.get('RUN_INTEGRATION_TESTS'),
                 "Skipping integration tests. Set RUN_INTEGRATION_TESTS=1 to run.")
class TestLiveLabConnection(unittest.TestCase):
    """
    Integration tests for the LabConnection class using Pydantic models.
    These tests make real network calls to the configured Azure and Splunk lab environment.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the connection once for all tests in this class."""
        # Import the refactored models and the connector
        from powershell_sentinel.models import CommandOutput, SplunkLogEvent
        from powershell_sentinel.lab_connector import LabConnection
        
        # Make models available to the test instance
        cls.CommandOutput = CommandOutput
        cls.SplunkLogEvent = SplunkLogEvent

        print("\n--- Initializing Live Lab Connection for Integration Test ---")
        try:
            cls.lab = LabConnection()
            print("[SUCCESS] LabConnection initialized successfully.")
        except Exception as e:
            raise unittest.SkipTest(f"Failed to initialize LabConnection, skipping all integration tests. Error: {e}")

    def test_full_loop_connectivity(self):
        """
        Tests the full data loop:
        1. Executes a unique PowerShell command on the victim VM.
        2. Polls Splunk until the corresponding log event (as a Pydantic model) appears.
        """
        # --- 1. ARRANGE: Create a unique "canary" string for this test run ---
        canary_string = f"integration-test-canary-{uuid.uuid4()}"
        command = f'Write-Host "{canary_string}"'
        print(f"\n[INFO] Executing canary command: {command}")

        # --- 2. ACT: Execute the command on the remote victim VM ---
        exec_result = self.lab.run_remote_powershell(command)
        
        # --- 3. ASSERT (Part 1): Check the command execution result ---
        # Assert that the result is a Pydantic model with the correct data
        self.assertIsInstance(exec_result, self.CommandOutput)
        self.assertEqual(exec_result.return_code, 0, f"PowerShell command failed. Stderr: {exec_result.stderr}")
        self.assertIn(canary_string, exec_result.stdout, "Canary string not found in command stdout.")
        print(f"[SUCCESS] Remote command executed successfully on host.")

        # --- 4. ASSERT (Part 2): Poll Splunk to find the resulting log event ---
        print(f"[INFO] Polling Splunk for log containing: '{canary_string}'")
        search_query = f'search index=main host=PS-VICTIM-01 "{canary_string}"'
        
        found_log = None
        timeout_seconds = 60
        poll_interval = 5

        for i in range(timeout_seconds // poll_interval):
            print(f"   -> Querying Splunk (attempt {i+1})...")
            logs = self.lab.query_splunk(search_query) # This now returns List[SplunkLogEvent]
            if logs:
                print("[SUCCESS] Found matching log event in Splunk!")
                found_log = logs[0]
                break
            time.sleep(poll_interval)
        
        # Assert that the test did not time out
        self.assertIsNotNone(found_log, f"TEST FAILED: Timed out after {timeout_seconds}s waiting for canary log.")
        
        # Assert that we received a valid Pydantic model for the log
        self.assertIsInstance(found_log, self.SplunkLogEvent)
        
        # Access the .raw attribute of the SplunkLogEvent model instead of using .get()
        self.assertIn(canary_string, found_log.raw, "Canary string not found in the raw log event.")
        print("[SUCCESS] Log content validated.")
        print("--- Full-Loop Integration Test PASSED ---")
# tests/test_integration_lab_connection.py

import unittest
import os
import time
import uuid
import json
from splunklib import results # [NEW] Import results reader directly

@unittest.skipIf(not os.environ.get('RUN_INTEGRATION_TESTS'),
                 "Skipping integration tests. Set RUN_INTEGRATION_TESTS=1 to run.")
class TestLiveLabConnection(unittest.TestCase):
    """
    Integration tests for the LabConnection class using Pydantic models.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the connection once for all tests in this class."""
        from powershell_sentinel.models import CommandOutput, SplunkLogEvent
        from powershell_sentinel.lab_connector import LabConnection
        
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
        Tests the full data loop: executes a command and polls Splunk for the result.
        """
        canary_string = f"integration-test-canary-{uuid.uuid4()}"
        command = f'Write-Host "{canary_string}"'
        print(f"\n[INFO] Executing canary command: {command}")

        exec_result = self.lab.run_remote_powershell(command)
        
        self.assertIsInstance(exec_result, self.CommandOutput)
        self.assertEqual(exec_result.return_code, 0, f"PowerShell command failed. Stderr: {exec_result.stderr}")
        self.assertIn(canary_string, exec_result.stdout, "Canary string not found in command stdout.")
        print(f"[SUCCESS] Remote command executed successfully on host.")

        print(f"[INFO] Polling Splunk for log containing: '{canary_string}'")
        search_query = f'search index=main host=PS-VICTIM-01 "{canary_string}"'
        
        found_log = None
        timeout_seconds = 120
        poll_interval = 5

        # [DEFINITIVE FIX] This is the robust, correct polling loop.
        # It creates the job once and polls the SAME job object for status.
        job = self.lab.splunk_service.jobs.create(search_query)
        
        try:
            for i in range(timeout_seconds // poll_interval):
                job.refresh()
                print(f"   -> Polling Splunk (attempt {i+1}). Job status: {job['dispatchState']}...")

                if job.is_done():
                    print("[SUCCESS] Splunk search job is complete.")
                    # Now that the job is done, get the results directly from THIS job.
                    reader = results.JSONResultsReader(job.results(output_mode='json'))
                    logs = [self.SplunkLogEvent.model_validate(item) for item in reader if isinstance(item, dict)]
                    
                    if logs:
                        print("[SUCCESS] Found matching log event in Splunk!")
                        found_log = logs[0]
                        break # Exit the polling loop
                
                time.sleep(poll_interval)
        finally:
            # Always cancel the job to be a good citizen.
            job.cancel()
        
        self.assertIsNotNone(found_log, f"TEST FAILED: Timed out after {timeout_seconds}s waiting for canary log.")
        self.assertIsInstance(found_log, self.SplunkLogEvent)
        self.assertIn(canary_string, found_log.raw, "Canary string not found in the raw log event.")
        print("[SUCCESS] Log content validated.")
        print("--- Full-Loop Integration Test PASSED ---")

if __name__ == '__main__':
    unittest.main()
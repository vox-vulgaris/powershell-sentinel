# tests/test_integration_lab_connection.py

import unittest
import os
import time
import uuid
import json
from splunklib import results

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
        
    @classmethod
    def tearDownClass(cls):
        """Close the connection after all tests in this class are done."""
        if hasattr(cls, 'lab') and cls.lab:
            cls.lab.close()

    def test_full_loop_connectivity(self):
        """
        Tests the full data loop: executes a command and polls Splunk for the result.
        """
        canary_string = f"integration-test-canary-{uuid.uuid4()}"
        
        # [DEFINITIVE FIX] Do not use Write-Host. Simply output the string to the
        # success stream so it can be captured by Receive-Job in our wrapper.
        command = f'"{canary_string}"'
        print(f"\n[INFO] Executing canary command: {command}")

        exec_result = self.lab.run_remote_powershell(command)
        
        self.assertIsInstance(exec_result, self.CommandOutput)
        self.assertEqual(exec_result.return_code, 0, f"PowerShell command failed. Stderr: {exec_result.stderr}")
        self.assertIn(canary_string, exec_result.stdout, "Canary string not found in command stdout.")
        print(f"[SUCCESS] Remote command executed successfully on host.")

        # --- The Splunk polling section is correct and remains unchanged ---
        print(f"[INFO] Polling Splunk for log containing: '{canary_string}'")
        search_query = f'search index=main host=PS-VICTIM-01 "{canary_string}"'
        
        found_log = None
        timeout_seconds = 120
        poll_interval = 5

        job = self.lab.splunk_service.jobs.create(search_query)
        
        try:
            for i in range(timeout_seconds // poll_interval):
                job.refresh()
                print(f"   -> Polling Splunk (attempt {i+1}). Job status: {job['dispatchState']}...")

                if job.is_done():
                    print("[SUCCESS] Splunk search job is complete.")
                    reader = results.JSONResultsReader(job.results(output_mode='json'))
                    logs = [self.SplunkLogEvent.model_validate(item) for item in reader if isinstance(item, dict)]
                    
                    if logs:
                        print("[SUCCESS] Found matching log event in Splunk!")
                        found_log = logs[0]
                        break
                
                time.sleep(poll_interval)
        finally:
            job.cancel()
        
        self.assertIsNotNone(found_log, f"TEST FAILED: Timed out after {timeout_seconds}s waiting for canary log.")
        self.assertIsInstance(found_log, self.SplunkLogEvent)
        # We search the raw log, because Splunk will log the entire original command line
        self.assertIn(canary_string, found_log.raw, "Canary string not found in the raw log event.")
        print("[SUCCESS] Log content validated.")
        print("--- Full-Loop Integration Test PASSED ---")

if __name__ == '__main__':
    unittest.main()
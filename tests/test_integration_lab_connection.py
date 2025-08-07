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
    @classmethod
    def setUpClass(cls):
        from powershell_sentinel.models import CommandOutput, SplunkLogEvent
        from powershell_sentinel.lab_connector import LabConnection
        
        cls.CommandOutput = CommandOutput
        cls.SplunkLogEvent = SplunkLogEvent

        print("\n--- Initializing Live Lab Connection for Integration Test ---")
        try:
            cls.lab = LabConnection()
            print("[SUCCESS] LabConnection initialized successfully.")
        except Exception as e:
            raise unittest.SkipTest(f"Failed to initialize LabConnection. Error: {e}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'lab') and cls.lab:
            cls.lab.close()

    def test_full_loop_connectivity(self):
        canary_string = f"integration-test-canary-{uuid.uuid4()}"
        
        # [REVISED] Use a command that produces pipeline output, not host output.
        command = f'"{canary_string}"'
        print(f"\n[INFO] Executing canary command: {command}")

        exec_result = self.lab.run_remote_powershell(command)
        
        self.assertIsInstance(exec_result, self.CommandOutput)
        self.assertEqual(exec_result.return_code, 0, f"PowerShell command failed. Stderr: {exec_result.stderr}")
        
        # [REVISED] The canary string is now in the parsed stdout field.
        self.assertIn(canary_string, exec_result.stdout, "Canary string not found in command stdout.")
        print(f"[SUCCESS] Remote command executed successfully on host.")

        # The Splunk polling logic is correct and remains unchanged.
        print(f"[INFO] Polling Splunk for log containing: '{canary_string}'")
        search_query = f'search index=main host=PS-VICTIM-01 "{canary_string}"'
        
        found_log = None
        timeout_seconds = 120
        poll_interval = 5

        job = self.lab.splunk_service.jobs.create(search_query)
        try:
            for i in range(timeout_seconds // poll_interval):
                job.refresh()
                if job.is_done():
                    reader = results.JSONResultsReader(job.results(output_mode='json'))
                    logs = [self.SplunkLogEvent.model_validate(item) for item in reader if isinstance(item, dict)]
                    if logs:
                        found_log = logs[0]
                        break
                time.sleep(poll_interval)
        finally:
            job.cancel()
        
        self.assertIsNotNone(found_log, f"TEST FAILED: Timed out waiting for canary log.")
        self.assertIsInstance(found_log, self.SplunkLogEvent)
        self.assertIn(canary_string, found_log.raw, "Canary string not found in raw log.")
        print("[SUCCESS] Log content validated.")

if __name__ == '__main__':
    unittest.main()
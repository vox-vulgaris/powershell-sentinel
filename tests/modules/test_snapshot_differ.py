# Phase 2: Data Factory - Curation Tooling
# Index: [4]
#
# Unit tests for the snapshot_differ.py module.
#
# REQUIREMENTS:
# 1. Test the core `get_delta_logs` function.
# 2. Use mock data to represent "before" and "after" log states.
# 3. Assert that the function correctly identifies only the new logs.
# 4. Assert that common/noise logs present in both lists are successfully excluded.
# 5. Test edge cases, such as empty input lists.

import unittest
from powershell_sentinel.modules.snapshot_differ import get_delta_logs

class TestSnapshotDiffer(unittest.TestCase):

    def setUp(self):
        """Set up common test data."""
        self.before_logs = [
            {"EventID": 4688, "ProcessName": "svchost.exe", "CommandLine": "C:\\Windows\\system32\\svchost.exe -k netsvcs"},
            {"EventID": 4104, "Message": "Noise script block"}
        ]
        
        # The "after" state contains the original logs plus new "golden signals"
        self.after_logs = [
            {"EventID": 4688, "ProcessName": "svchost.exe", "CommandLine": "C:\\Windows\\system32\\svchost.exe -k netsvcs"}, # Same
            {"EventID": 4104, "Message": "Noise script block"}, # Same
            {"EventID": 4688, "ProcessName": "powershell.exe", "CommandLine": "powershell.exe -c Get-Process"}, # New Signal 1
            {"EventID": 4104, "Message": "Executing Get-Process..."} # New Signal 2
        ]

        self.expected_delta = [
            {"EventID": 4688, "ProcessName": "powershell.exe", "CommandLine": "powershell.exe -c Get-Process"},
            {"EventID": 4104, "Message": "Executing Get-Process..."}
        ]

    def test_get_delta_logs_standard(self):
        """Test that new logs are correctly identified."""
        delta = get_delta_logs(self.before_logs, self.after_logs)
        self.assertEqual(len(delta), 2)
        # Using assertCountEqual to compare lists of dictionaries regardless of order
        self.assertCountEqual(delta, self.expected_delta)

    def test_get_delta_logs_no_new_logs(self):
        """Test that an empty list is returned when no new logs are present."""
        delta = get_delta_logs(self.before_logs, self.before_logs)
        self.assertEqual(delta, [])

    def test_get_delta_logs_empty_before(self):
        """Test that all logs are returned if the 'before' list is empty."""
        delta = get_delta_logs([], self.after_logs)
        self.assertCountEqual(delta, self.after_logs)

    def test_get_delta_logs_empty_after(self):
        """Test that an empty list is returned if the 'after' list is empty."""
        delta = get_delta_logs(self.before_logs, [])
        self.assertEqual(delta, [])

if __name__ == '__main__':
    unittest.main()
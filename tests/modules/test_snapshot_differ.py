# Phase 2: Data Factory - Curation Tooling
# Index: [4]
#
# Unit tests for the snapshot_differ.py module.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Test the core `get_delta_logs` function.
# 2. Use Pydantic `SplunkLogEvent` models to represent "before" and "after" log states.
# 3. Assert that the function correctly identifies only the new logs.
# 4. Assert that common/noise logs present in both lists are successfully excluded.
# 5. Test edge cases, such as empty input lists.

import unittest
from powershell_sentinel.modules.snapshot_differ import get_delta_logs
from powershell_sentinel.models import SplunkLogEvent

class TestSnapshotDiffer(unittest.TestCase):

    def setUp(self):
        """Set up common test data using Pydantic models."""
        # A helper function to create dummy SplunkLogEvent objects
        def create_log(raw_content: str) -> SplunkLogEvent:
            return SplunkLogEvent.model_validate({
                "_raw": raw_content,
                "_time": "2023-01-01T12:00:00.000+00:00",
                "source": "TestSource",
                "sourcetype": "TestSourcetype"
            })

        self.before_logs = [
            create_log("noise log 1: svchost.exe"),
            create_log("noise log 2: some other system event")
        ]
        
        # The "after" state contains the original logs plus new "golden signals"
        self.signal_1 = create_log("signal log 1: powershell.exe -c Get-Process")
        self.signal_2 = create_log("signal log 2: ScriptBlockText containing Get-Process")
        
        self.after_logs = [
            self.before_logs[0], # Same object
            self.before_logs[1], # Same object
            self.signal_1,
            self.signal_2
        ]

        self.expected_delta = [self.signal_1, self.signal_2]

    def test_get_delta_logs_standard(self):
        """Test that new logs are correctly identified."""
        delta = get_delta_logs(self.before_logs, self.after_logs)
        self.assertEqual(len(delta), 2)
        # Pydantic models are comparable by default, which is very convenient
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
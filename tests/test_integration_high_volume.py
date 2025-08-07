# tests/test_integration_high_volume.py

import unittest
import os
import json
import tempfile

@unittest.skipIf(not os.environ.get('RUN_INTEGRATION_TESTS'),
                 "Skipping integration tests. Set RUN_INTEGRATION_TESTS=1 to run.")
class TestHighVolumeGeneration(unittest.TestCase):
    """
    Integration test for the main_data_factory to ensure it can handle
    a high volume of connections without crashing, using the persistent shell.
    This test directly addresses the "frozen" process issue.
    """

    def setUp(self):
        """Set up a temporary directory and a sample primitives file."""
        from powershell_sentinel.main_data_factory import generate_dataset
        self.generate_dataset = generate_dataset
        
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.output_path = os.path.join(self.temp_dir.name, "output.json")
        
        # A simple, reliable primitive that always works.
        mock_primitives = [{
            "primitive_id": "PS-001",
            "primitive_command": "Get-Process -Name 'svchost' | Select-Object -First 1",
            "intent": ["Process Discovery"],
            "mitre_ttps": ["T1057"],
            "telemetry_rules": [{"source": "Sysmon", "event_id": 1, "details": "Process Create"}]
        }]
        with open(self.primitives_path, 'w') as f:
            json.dump(mock_primitives, f)
    
    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_high_volume_run_does_not_crash(self):
        """
        Runs the data generator for a batch large enough to have previously
        caused a crash (e.g., > 50), asserting that it completes successfully.
        """
        # We run for 100 pairs. The original crash happened at ~40.
        # This will prove the stability of the persistent connection.
        target_count = 100
        
        print(f"\n--- Starting High-Volume Integration Test ({target_count} pairs) ---")
        
        try:
            # We don't need to patch anything. We are testing the real components.
            self.generate_dataset(target_count, self.primitives_path, self.output_path)
        except Exception as e:
            self.fail(f"The data generation process crashed with an unexpected exception: {e}")
        
        # Verify the output
        self.assertTrue(os.path.exists(self.output_path), "Output file was not created.")
        
        with open(self.output_path, 'r') as f:
            data = json.load(f)
        
        self.assertGreater(len(data), 0, "The output file is empty.")
        # The actual number might be less than target_count if some obfuscations fail,
        # but the key is that the process finished and produced a result.
        print(f"[SUCCESS] High-volume test completed without crashing. Generated {len(data)} pairs.")
        self.assertEqual(data[0]['response']['deobfuscated_command'], "Get-Process -Name 'svchost' | Select-Object -First 1")


if __name__ == '__main__':
    unittest.main()
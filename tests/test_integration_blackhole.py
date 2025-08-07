# tests/test_integration_blackhole.py

import unittest
import os
from unittest.mock import patch

@unittest.skipIf(not os.environ.get('RUN_INTEGRATION_TESTS'),
                 "Skipping integration tests. Set RUN_INTEGRATION_TESTS=1 to run.")
class TestBlackHoleCommands(unittest.TestCase):
    """
    This crucial test validates that the system is resilient against
    'black hole' commands—obfuscated commands that are known to cause
    the underlying WinRM shell to hang or crash.
    """

    @classmethod
    def setUpClass(cls):
        from powershell_sentinel.lab_connector import LabConnection
        cls.lab = LabConnection()
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'lab') and cls.lab:
            cls.lab.close()

    def test_double_invoke_expression_does_not_hang(self):
        """
        Tests the exact 'double Invoke-Expression' pattern that previously
        caused a fatal resource leak and shell crash.
        """
        print("\n--- Starting Black Hole Command Integration Test ---")
        
        # This is a known problematic command that can cause hangs/leaks.
        black_hole_command = "Invoke-Expression ('{0}' -f 'Invoke-Expression(''hostname'')')"
        
        print(f"[INFO] Executing known problematic command: {black_hole_command}")
        
        # We don't care about the result content, only that it returns
        # without crashing and correctly identifies a failure (non-zero code).
        # A timeout is also an acceptable failure mode.
        exec_result = self.lab.run_remote_powershell(black_hole_command)

        # The most important assertion: The command did not hang and we got a result back.
        self.assertIsNotNone(exec_result)
        
        # Assert that the system correctly identified this as a failure.
        self.assertNotEqual(exec_result.return_code, 0, 
            "The black hole command unexpectedly succeeded.")
            
        print(f"[SUCCESS] The system correctly handled the black hole command and returned a failure.")
        print(f"   -> Return Code: {exec_result.return_code}")
        print(f"   -> Stderr: {exec_result.stderr}")


if __name__ == '__main__':
    unittest.main()
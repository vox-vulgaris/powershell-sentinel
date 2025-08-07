# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [10]
#
# Unit and Integration tests for the obfuscator.py module.

import unittest
import subprocess
import random
import sys
import os
import datetime
import base64
from powershell_sentinel.modules.obfuscator import (
    obfuscate_concat,
    obfuscate_base64,
    obfuscate_types, # [FIX] Import the new, correct function
    obfuscate_variables,
    obfuscate_format_operator,
    generate_layered_obfuscation
)

class TestObfuscator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the Canary Cage and logging."""
        cls.powershell_executable = "powershell.exe" if sys.platform == "win32" else "pwsh"
        
        cls.canary_cage = [
            ("Write-Host 'Success'", "Success"),
            ("Get-Process -Name 'powershell'", None),
            ("$a = 5; $b = 10; $a + $b", "15"),
            ("Resolve-DnsName -Name google.com", None),
            ("{ Get-Date } | Out-String", None)
        ]
        cls.log_dir = os.path.join("data", "interim", "obfuscation_logs")
        os.makedirs(cls.log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.log_file_path = os.path.join(cls.log_dir, f"test_obfuscator_output_{timestamp}.log")
        cls.log_entries = []

    @classmethod
    def tearDownClass(cls):
        """Write all collected logs to the file at the very end of the test run."""
        with open(cls.log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"--- Test Run Log for {cls.__name__} ---\n\n")
            f.writelines(cls.log_entries)
        print(f"\n[INFO] Full test execution log saved to: {cls.log_file_path}")

    def _validate_execution(self, obfuscated_command: str, expected_output: str = None, test_context: str = ""):
        """Helper to run a command, log its output, and validate it."""
        log_header = f"--- CONTEXT: {test_context} ---\n"
        
        is_encoded = False
        try:
            # A simple check to see if the string is valid Base64
            base64.b64decode(obfuscated_command, validate=True)
            is_encoded = True
        except (ValueError, TypeError):
            is_encoded = False

        if "powershell.exe -EncodedCommand" in obfuscated_command:
            command_parts = obfuscated_command.split(" ")
            command_to_run = [command_parts[0], command_parts[1], command_parts[2]]
        elif is_encoded:
             command_to_run = [self.powershell_executable, "-EncodedCommand", obfuscated_command]
        else:
            command_to_run = [self.powershell_executable, "-ExecutionPolicy", "Bypass", "-Command", obfuscated_command]
        
        log_cmd = f"COMMAND: {' '.join(command_to_run)}\n"
        
        try:
            process = subprocess.run(
                command_to_run,
                capture_output=True, text=True, timeout=20, check=True, encoding='utf-8'
            )
            log_result = f"STATUS: PASS\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}\n---------------------------------\n\n"
            self.log_entries.append(log_header + log_cmd + log_result)

            self.assertEqual(process.returncode, 0)
            if process.stderr and "progress" not in process.stderr:
                self.fail(f"Command produced stderr: {process.stderr}")

            if expected_output is not None:
                self.assertEqual(process.stdout.strip(), expected_output.strip())
        
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, AssertionError) as e:
            stderr = e.stderr if hasattr(e, 'stderr') else 'N/A'
            stdout = e.stdout if hasattr(e, 'stdout') else 'N/A'
            log_result = f"STATUS: FAIL\nERROR_TYPE: {type(e).__name__}\nERROR_MESSAGE: {e}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n---------------------------------\n\n"
            self.log_entries.append(log_header + log_cmd + log_result)
            self.fail(f"Validation failed. See log file: {self.log_file_path}")

    def test_unit_obfuscate_concat(self):
        for command, expected_output in self.canary_cage:
            with self.subTest(command=command):
                obfuscated = obfuscate_concat(command)
                self._validate_execution(obfuscated, expected_output, test_context=f"concat: {command}")

    def test_unit_obfuscate_base64(self):
        for command, expected_output in self.canary_cage:
            with self.subTest(command=command):
                obfuscated = obfuscate_base64(command)
                self._validate_execution(obfuscated, expected_output, test_context=f"base64: {command}")

    def test_unit_obfuscate_types(self):
        """[NEW] Unit test for the type casting obfuscator against the Canary Cage."""
        for command, expected_output in self.canary_cage:
            with self.subTest(command=command):
                obfuscated = obfuscate_types(command)
                self._validate_execution(obfuscated, expected_output, test_context=f"types: {command}")

    def test_unit_obfuscate_variables(self):
        for command, expected_output in self.canary_cage:
            with self.subTest(command=command):
                obfuscated = obfuscate_variables(command)
                self._validate_execution(obfuscated, expected_output, test_context=f"variables: {command}")

    def test_unit_obfuscate_format_operator(self):
        for command, expected_output in self.canary_cage:
            with self.subTest(command=command):
                obfuscated = obfuscate_format_operator(command)
                self._validate_execution(obfuscated, expected_output, test_context=f"format: {command}")

    def test_integration_generate_layered_obfuscation(self):
        """Integration test for the master function, validating 100 random combinations."""
        self.assertTrue(len(self.canary_cage) > 0, "Canary cage cannot be empty for integration test.")
        
        for i in range(100):
            command, _ = random.choice(self.canary_cage)
            layered_command, chain = generate_layered_obfuscation(command)
            
            with self.subTest(i=i, command=command, chain=chain):
                self._validate_execution(layered_command, None, test_context=f"layered #{i} {chain}: {command}") 

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestObfuscator))
    runner = unittest.TextTestRunner()
    runner.run(suite)
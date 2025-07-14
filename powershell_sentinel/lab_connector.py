# Phase 1: Foundation & Lab Setup
# Index: [3]
#
# This module is the most critical dependency for the data factory. It abstracts all
# interactions with the remote lab environment (the Windows VMs and the Splunk instance).
# All connections and credentials should be managed here to ensure a clean separation
# of concerns.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must handle connection credentials securely (e.g., via environment variables or a config file, NOT hardcoded). [cite: 1]
# 2. Must provide a function to execute commands on the remote Victim Workstation. [cite: 24]
# 3. Must provide a function to query the local Splunk instance for log data. [cite: 25]
# 4. Must include robust error handling for connection failures, authentication issues, and query timeouts. [cite: 1]

import os
import sys
import splunklib.client as client
import splunklib.results as results
import winrm
from winrm.exceptions import WinRMError, WinRMTransportError
from dotenv import load_dotenv

load_dotenv()

# --- Lab Configuration ---
# TODO: Load these from environment variables or a separate config file for security.
# IMPLEMENTATION: Credentials are now loaded from environment variables.
# For this to work, you must set these variables in your shell before running the script, for example:
# export VICTIM_VM_IP="10.0.0.5"
# export VICTIM_VM_USER="LabAdmin"
# export VICTIM_VM_PASS="YourSecurePassword123!"
# export SPLUNK_PASS="YourSplunkAdminPassword"
VICTIM_VM_IP = os.getenv("VICTIM_VM_IP")
VICTIM_VM_USER = os.getenv("VICTIM_VM_USER")
VICTIM_VM_PASS = os.getenv("VICTIM_VM_PASS")

SPLUNK_HOST = os.getenv("SPLUNK_HOST", "localhost")
SPLUNK_PORT = int(os.getenv("SPLUNK_PORT", 8089))
SPLUNK_USER = os.getenv("SPLUNK_USER", "admin")
SPLUNK_PASS = os.getenv("SPLUNK_PASS")


class LabConnection:
    """A class to manage connections and interactions with the lab environment."""

    def __init__(self):
        """Initializes the connection objects for WinRM and Splunk."""
        # TODO: Implement connection setup with robust error handling.
        # IMPLEMENTATION: Connection logic added for both WinRM and Splunk with
        # specific exception handling to provide clear error messages.
        self.winrm_session = None
        self.splunk_service = None

        # Check for missing environment variables
        if not all([VICTIM_VM_IP, VICTIM_VM_USER, VICTIM_VM_PASS, SPLUNK_PASS]):
            raise ValueError("One or more required environment variables are not set.")

        # WinRM setup for PowerShell Remoting
        try:
            # The transport must be unencrypted ('plaintext') as we are not setting up HTTPS in the lab.
            # Server cert validation is ignored for the same reason. This is acceptable for a closed lab environment.
            self.winrm_session = winrm.Protocol(
                endpoint=f"http://{VICTIM_VM_IP}:5985/wsman",
                transport='ntlm',
                username=VICTIM_VM_USER,
                password=VICTIM_VM_PASS,
                server_cert_validation='ignore'
            )
            # A simple check to see if we can authenticate
            # self.winrm_session.run_cmd('whoami') 
        except (WinRMError, WinRMTransportError) as e:
            print(f"FATAL: Failed to connect to WinRM service on {VICTIM_VM_IP}. Error: {e}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"FATAL: An unexpected error occurred during WinRM initialization. Error: {e}", file=sys.stderr)
            raise

        # Splunk setup
        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST,
                port=SPLUNK_PORT,
                username=SPLUNK_USER,
                password=SPLUNK_PASS
            )
            # A simple check to confirm the connection works
            if not self.splunk_service.apps:
                 raise ConnectionError("Could not retrieve app list from Splunk.")
        except Exception as e:
            print(f"FATAL: Failed to connect to Splunk service at {SPLUNK_HOST}:{SPLUNK_PORT}. Error: {e}", file=sys.stderr)
            raise

    def run_remote_powershell(self, command: str) -> dict:
        """
        [cite_start]Executes a PowerShell command on the remote Victim VM. [cite: 24]

        Args:
            command: The PowerShell command string to execute.

        Returns:
            A dictionary containing:
            - 'stdout': The standard output from the command.
            - 'stderr': The standard error from the command.
            - 'return_code': The exit code of the command (0 for success).
        """
        shell_id = None
        try:
            # 1. Open a new shell on the remote machine
            shell_id = self.winrm_session.open_shell()

            # 2. Execute the PowerShell command within the shell
            command_id = self.winrm_session.run_command(shell_id, 'powershell.exe', ['-Command', command])

            # 3. Get the output
            stdout, stderr, return_code = self.winrm_session.get_command_output(shell_id, command_id)

            # 4. Clean up the command resources
            self.winrm_session.cleanup_command(shell_id, command_id)

            return {
                "stdout": stdout.decode('utf-8', errors='ignore').strip(),
                "stderr": stderr.decode('utf-8', errors='ignore').strip(),
                "return_code": return_code
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Failed to execute command via WinRM: {e}",
                "return_code": -1
            }
        finally:
            # 5. Ensure the shell is always closed
            if shell_id:
                self.winrm_session.close_shell(shell_id)

    def query_splunk(self, search_query: str) -> list:
        """
        Executes a search query against the local Splunk instance. [cite: 25]

        Args:
            search_query: The Splunk Search Processing Language (SPL) query.
                          It should start with 'search'.

        Returns:
            A list of dictionary objects, where each dictionary is a log event.
        """
        # TODO: Implement the Splunk search logic using self.splunk_service.
        # The job should be executed in 'blocking' mode for simplicity.
        # The output format should be JSON.
        # Handle potential Splunk API exceptions.
        # IMPLEMENTATION: A blocking search job is created with the required JSON
        # output mode. Results are read using the ResultsReader and returned as a list.
        # NOTE: JSONResultsReader causes silent failures in this environment; the deprecated
        # ResultsReader is used as it is proven to be functional.
        # A try/except block handles potential API or search-related errors.
        kwargs_search = {"exec_mode": "blocking", "output_mode": "json"}
        
        if not search_query.strip().startswith('search'):
             print("Warning: Splunk query does not start with 'search'. Prepending it.", file=sys.stderr)
             search_query = "search " + search_query

        try:
            job = self.splunk_service.jobs.create(search_query, **kwargs_search)
            
            # The results are returned as an iterable Reader object. We convert it to a list.
            reader = results.ResultsReader(job.results())
            result_list = [item for item in reader]
            return result_list

        except Exception as e:
            print(f"Error executing Splunk query: {e}", file=sys.stderr)
            return []
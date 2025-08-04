# powershell_sentinel/lab_connector.py

import os
import sys
import splunklib.client as client
import splunklib.results as results
import winrm
from winrm.exceptions import WinRMError, WinRMTransportError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List

# Import our new Pydantic models
from .models import CommandOutput, SplunkLogEvent

load_dotenv()

# --- Lab Configuration ---
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
        self.winrm_session = None
        self.splunk_service = None

        if not all([VICTIM_VM_IP, VICTIM_VM_USER, VICTIM_VM_PASS, SPLUNK_PASS]):
            raise ValueError("One or more required environment variables are not set.")

        try:
            self.winrm_session = winrm.Protocol(
                endpoint=f"http://{VICTIM_VM_IP}:5985/wsman",
                transport='ntlm',
                username=VICTIM_VM_USER,
                password=VICTIM_VM_PASS,
                server_cert_validation='ignore'
            )
        except (WinRMError, WinRMTransportError) as e:
            print(f"FATAL: Failed to connect to WinRM service on {VICTIM_VM_IP}. Error: {e}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"FATAL: An unexpected error occurred during WinRM initialization. Error: {e}", file=sys.stderr)
            raise

        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST,
                port=SPLUNK_PORT,
                username=SPLUNK_USER,
                password=SPLUNK_PASS
            )
            if not self.splunk_service.apps:
                raise ConnectionError("Could not retrieve app list from Splunk.")
        except Exception as e:
            print(f"FATAL: Failed to connect to Splunk service at {SPLUNK_HOST}:{SPLUNK_PORT}. Error: {e}", file=sys.stderr)
            raise

    # CHANGED: Return type hint is now CommandOutput
    def run_remote_powershell(self, command: str) -> CommandOutput:
        """
        Executes a PowerShell command on the remote Victim VM.
        """
        shell_id = None
        try:
            shell_id = self.winrm_session.open_shell()
            command_id = self.winrm_session.run_command(shell_id, 'powershell.exe', ['-Command', command])
            stdout, stderr, return_code = self.winrm_session.get_command_output(shell_id, command_id)
            self.winrm_session.cleanup_command(shell_id, command_id)
            
            # CHANGED: Return a Pydantic model instance instead of a dict
            return CommandOutput(
                stdout=stdout.decode('utf-8', errors='ignore').strip(),
                stderr=stderr.decode('utf-8', errors='ignore').strip(),
                return_code=return_code
            )
        except Exception as e:
            # CHANGED: Return the Pydantic model even on failure for a consistent return type
            return CommandOutput(
                stdout="",
                stderr=f"Failed to execute command via WinRM: {e}",
                return_code=-1
            )
        finally:
            if shell_id:
                self.winrm_session.close_shell(shell_id)

    # CHANGED: Return type hint is now a list of SplunkLogEvent models
    def query_splunk(self, search_query: str) -> List[SplunkLogEvent]:
        """
        Executes a search query against the local Splunk instance.
        """
        kwargs_search = {"exec_mode": "blocking", "output_mode": "json"}
        
        if not search_query.strip().startswith('search'):
            print("Warning: Splunk query does not start with 'search'. Prepending it.", file=sys.stderr)
            search_query = "search " + search_query

        try:
            job = self.splunk_service.jobs.create(search_query, **kwargs_search)
            
            # NOTE: JSONResultsReader causes issues in this env; using the deprecated but functional ResultsReader.
            reader = results.ResultsReader(job.results())
            
            # CHANGED: Use a list comprehension to parse and validate each log event into a Pydantic model
            validated_results = []
            for item in reader:
                if isinstance(item, dict):
                    try:
                        validated_results.append(SplunkLogEvent(**item))
                    except ValidationError as e:
                        print(f"Warning: A Splunk log event failed validation and was skipped. Error: {e}", file=sys.stderr)
            return validated_results

        except Exception as e:
            print(f"Error executing Splunk query: {e}", file=sys.stderr)
            return []
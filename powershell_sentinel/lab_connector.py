# powershell_sentinel/lab_connector.py

import os
import sys
import splunklib.client as client
import splunklib.results as results
import winrm
from winrm.exceptions import WinRMError, WinRMTransportError, WinRMOperationTimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List
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
                server_cert_validation='ignore',
                operation_timeout_sec=30,
                read_timeout_sec=40
            )
        except (WinRMError, WinRMTransportError) as e:
            print(f"FATAL: Failed to connect to WinRM service on {VICTIM_VM_IP}. Error: {e}", file=sys.stderr)
            raise
        
        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST,
                port=SPLUNK_PORT,
                username=SPLUNK_USER,
                password=SPLUNK_PASS
            )
            self.splunk_service.apps.list()
        except Exception as e:
            print(f"FATAL: Failed to connect to Splunk service at {SPLUNK_HOST}:{SPLUNK_PORT}. Error: {e}", file=sys.stderr)
            raise

    def run_remote_powershell(self, command: str) -> CommandOutput:
        """Executes a PowerShell command on the remote Victim VM."""
        shell_id = None
        try:
            shell_id = self.winrm_session.open_shell()
            command_id = self.winrm_session.run_command(shell_id, 'powershell.exe', ['-Command', command])
            stdout, stderr, return_code = self.winrm_session.get_command_output(shell_id, command_id)
            self.winrm_session.cleanup_command(shell_id, command_id)
            
            return CommandOutput(
                stdout=stdout.decode('utf-8', errors='ignore').strip(),
                stderr=stderr.decode('utf-8', errors='ignore').strip(),
                return_code=return_code
            )
        except (WinRMError, WinRMTransportError, WinRMOperationTimeoutError, Exception) as e:
            return CommandOutput(
                stdout="",
                stderr=f"Failed to execute command via WinRM: {e}",
                return_code=-1
            )
        finally:
            if shell_id:
                self.winrm_session.close_shell(shell_id)

    def query_splunk(self, search_query: str) -> List[SplunkLogEvent]:
        """Executes a search query against the local Splunk instance."""
        # [FIX] Revert to using the modern JSONResultsReader with the correct output_mode.
        kwargs_search = {"exec_mode": "blocking", "output_mode": "json"}
        if not search_query.strip().startswith('search'):
            search_query = "search " + search_query
            
        try:
            job = self.splunk_service.jobs.create(search_query, **kwargs_search)
            reader = results.JSONResultsReader(job.results())
            
            validated_results = []
            for item in reader:
                if isinstance(item, dict):
                    try:
                        validated_results.append(SplunkLogEvent.model_validate(item))
                    except ValidationError:
                        continue
            return validated_results
        except Exception as e:
            print(f"Warning: A Splunk query failed to execute. Error: {e}", file=sys.stderr)
            return []
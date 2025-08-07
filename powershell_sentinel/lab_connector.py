# powershell_sentinel/lab_connector.py

import os
import sys
import json
import base64
import time
import winrm
import splunklib.client as client
import splunklib.results as results
from winrm.exceptions import WinRMError, WinRMTransportError, WinRMOperationTimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List
from .models import CommandOutput, SplunkLogEvent
from rich.console import Console

load_dotenv()
console = Console()

VICTIM_VM_IP = os.getenv("VICTIM_VM_IP")
VICTIM_VM_USER = os.getenv("VICTIM_VM_USER")
VICTIM_VM_PASS = os.getenv("VICTIM_VM_PASS")
SPLUNK_HOST = os.getenv("SPLUNK_HOST", "localhost")
SPLUNK_PORT = int(os.getenv("SPLUNK_PORT", 8089))
SPLUNK_USER = os.getenv("SPLUNK_USER", "admin")
SPLUNK_PASS = os.getenv("SPLUNK_PASS")

# [DEFINITIVE WRAPPER] This robust wrapper uses try/catch and explicit error checking
# to correctly report the success/failure of the script *inside* PowerShell.
POWERSHELL_ROBUST_WRAPPER = """
$commandToRun = @'
{command}
'@

$result = @{{
    Stdout = ""
    Stderr = ""
    ReturnCode = -1 # Default to failure
}}

try {{
    # Execute the command and capture the output stream
    $output = Invoke-Expression -Command $commandToRun 2>&1
    $result.Stdout = ($output | Out-String).Trim()

    # The '$?' variable is the most reliable way to check for non-terminating errors
    if ($?) {{
        $result.ReturnCode = 0
    }} else {{
        $result.ReturnCode = 1
        # If stdout is empty but there was an error, populate stderr from the output stream
        if (-not $result.Stdout.Trim()) {{
            $result.Stderr = "A non-terminating error occurred."
        }} else {{
            $result.Stderr = $result.Stdout # The error message is in the stdout stream
        }}
    }}
}} catch {{
    # This block catches script-terminating errors
    $result.Stderr = "Terminating Error: $($_.Exception.Message)"
    $result.ReturnCode = 1
}}

# Return the result object as a compressed JSON string
$result | ConvertTo-Json -Compress
"""

class LabConnection:
    def __init__(self):
        self.winrm_protocol = None
        self.splunk_service = None
        self.shell_id = None
        if not all([VICTIM_VM_IP, VICTIM_VM_USER, VICTIM_VM_PASS, SPLUNK_PASS]):
            raise ValueError("One or more required environment variables are not set.")
        self._connect_winrm()
        self._connect_splunk()

    def _connect_winrm(self):
        try:
            self.winrm_protocol = winrm.Protocol(
                endpoint=f"http://{VICTIM_VM_IP}:5985/wsman",
                transport='ntlm', username=VICTIM_VM_USER, password=VICTIM_VM_PASS,
                server_cert_validation='ignore',
                operation_timeout_sec=30,
                read_timeout_sec=40
            )
            self.shell_id = self.winrm_protocol.open_shell()
        except (WinRMError, WinRMTransportError) as e:
            console.print(f"FATAL: Failed to create WinRM connection. Error: {e}", style="bold red")
            raise

    def _connect_splunk(self):
        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST, port=SPLUNK_PORT, username=SPLUNK_USER, password=SPLUNK_PASS
            )
        except Exception as e:
            console.print(f"FATAL: Failed to connect to Splunk. Error: {e}", style="bold red")
            raise

    def close(self):
        if self.shell_id and self.winrm_protocol:
            try:
                self.winrm_protocol.close_shell(self.shell_id)
            except (WinRMError, WinRMTransportError):
                pass
        self.shell_id = None
        self.winrm_protocol = None

    def run_remote_powershell(self, command: str) -> CommandOutput:
        if not self.shell_id or not self.winrm_protocol:
             return CommandOutput(stdout="", stderr="FATAL: WinRM connection is not active.", return_code=-1)

        try:
            # Escape single quotes in the user command to prevent breaking the here-string
            safe_command = command.replace("'", "''")
            final_script = POWERSHELL_ROBUST_WRAPPER.format(command=safe_command)

            encoded_script = base64.b64encode(final_script.encode('utf-16-le')).decode('ascii')
            command_id = self.winrm_protocol.run_command(self.shell_id, 'powershell.exe', ['-EncodedCommand', encoded_script])
            stdout, stderr, return_code = self.winrm_protocol.get_command_output(self.shell_id, command_id)
            self.winrm_protocol.cleanup_command(self.shell_id, command_id)

            # The process exit code should be 0. We now parse our JSON for the *real* result.
            if return_code != 0:
                return CommandOutput(stdout="", stderr=f"WinRM Transport Error: Process exited with code {return_code}. Stderr: {stderr.decode('utf-8')}", return_code=return_code)

            try:
                response_str = stdout.decode('utf-8', errors='ignore').strip()
                response_json = json.loads(response_str)
                return CommandOutput.model_validate(response_json)
            except (json.JSONDecodeError, ValidationError) as e:
                return CommandOutput(stdout="", stderr=f"Failed to parse remote JSON response: {e}. Raw: {response_str}", return_code=-1)

        except (WinRMError, WinRMTransportError, WinRMOperationTimeoutError) as e:
            return CommandOutput(stdout="", stderr=f"Fatal WinRM Error: {e}", return_code=-1)
        except Exception as e:
            return CommandOutput(stdout="", stderr=f"Unexpected Python error: {e}", return_code=-1)

    def query_splunk(self, search_query: str) -> List[SplunkLogEvent]:
        kwargs_search = {"exec_mode": "blocking", "output_mode": "json"}
        if not search_query.strip().startswith('search'):
            search_query = "search " + search_query
        try:
            job = self.splunk_service.jobs.create(search_query, **kwargs_search)
            reader = results.JSONResultsReader(job.results(output_mode='json'))
            return [SplunkLogEvent.model_validate(item) for item in reader if isinstance(item, dict)]
        except Exception as e:
            print(f"Warning: A Splunk query failed. Error: {e}", file=sys.stderr)
            return []
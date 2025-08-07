# powershell_sentinel/lab_connector.py

import os
import sys
import json
import base64
import time
import splunklib.client as client
import splunklib.results as results
import winrm
from winrm.exceptions import WinRMError, WinRMTransportError, WinRMOperationTimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List
from .models import CommandOutput, SplunkLogEvent
from rich.console import Console

load_dotenv()
console = Console()

# --- Lab Configuration ---
VICTIM_VM_IP = os.getenv("VICTIM_VM_IP")
VICTIM_VM_USER = os.getenv("VICTIM_VM_USER")
VICTIM_VM_PASS = os.getenv("VICTIM_VM_PASS")
SPLUNK_HOST = os.getenv("SPLUNK_HOST", "localhost")
SPLUNK_PORT = int(os.getenv("SPLUNK_PORT", 8089))
SPLUNK_USER = os.getenv("SPLUNK_USER", "admin")
SPLUNK_PASS = os.getenv("SPLUNK_PASS")

# [DEFINITIVE FIX] This is the robust, self-contained timeout wrapper.
# It now expects the command to be injected into it BEFORE it is encoded.
POWERSHELL_TIMEOUT_WRAPPER_TEMPLATE = """
$commandToRun = @'
{command}
'@

$timeoutSeconds = 25

$result = @{{
    Stdout = ""
    Stderr = ""
    ReturnCode = -1
    TimedOut = $false
}}

try {{
    $scriptBlock = [scriptblock]::Create($commandToRun)
    $job = Start-Job -ScriptBlock $scriptBlock

    if (Wait-Job -Job $job -Timeout $timeoutSeconds) {{
        $output = Receive-Job -Job $job
        $result.Stdout = ($output | Out-String).Trim()
        
        if ($job.State -eq 'Failed') {{
            $result.Stderr = $job.ChildJobs[0].JobStateInfo.Reason.Message
            $result.ReturnCode = 1
        }} else {{
            $result.ReturnCode = 0
        }}
    }} else {{
        $result.Stderr = "Command timed out after $timeoutSeconds seconds."
        $result.TimedOut = $true
        $result.ReturnCode = 124
    }}
}} catch {{
    $result.Stderr = "PowerShell Wrapper Error: $($_.Exception.Message)"
    $result.ReturnCode = -1
}} finally {{
    if ($job) {{
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -ErrorAction SilentlyContinue -Force
    }}
}}

$result | ConvertTo-Json -Compress
"""


class LabConnection:
    """A class to manage connections and interactions with the lab environment."""

    def __init__(self):
        self.winrm_protocol = None
        self.splunk_service = None
        self.shell_id = None

        if not all([VICTIM_VM_IP, VICTIM_VM_USER, VICTIM_VM_PASS, SPLUNK_PASS]):
            raise ValueError("One or more required environment variables are not set.")
        
        try:
            self.winrm_protocol = winrm.Protocol(
                endpoint=f"http://{VICTIM_VM_IP}:5985/wsman",
                transport='ntlm', username=VICTIM_VM_USER, password=VICTIM_VM_PASS,
                server_cert_validation='ignore', 
                operation_timeout_sec=35, # Timeout must be > wrapper timeout
                read_timeout_sec=45
            )
            self.shell_id = self.winrm_protocol.open_shell()
        except (WinRMError, WinRMTransportError) as e:
            console.print(f"FATAL: Failed to connect or open a shell. Error: {e}", style="bold red")
            raise
        
        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST, port=SPLUNK_PORT, username=SPLUNK_USER, password=SPLUNK_PASS
            )
            self.splunk_service.apps.list()
        except Exception as e:
            console.print(f"FATAL: Failed to connect to Splunk. Error: {e}", style="bold red")
            if self.shell_id: self.winrm_protocol.close_shell(self.shell_id)
            raise

    def close(self):
        if self.shell_id:
            try:
                self.winrm_protocol.close_shell(self.shell_id)
                console.print("\n[green]Persistent WinRM shell closed.[/green]")
            except (WinRMError, WinRMTransportError):
                console.print("\n[yellow]Could not gracefully close WinRM shell (already terminated).[/yellow]")
            finally:
                self.shell_id = None

    def run_remote_powershell(self, command: str) -> CommandOutput:
        """Executes a command safely using an encoded, timed-out job wrapper."""
        if not self.shell_id:
            return CommandOutput(stdout="", stderr="WinRM shell is not open.", return_code=-1)
        
        try:
            # Step 1: Inject the command into the wrapper template.
            # Crucially, escape any single quotes in the command to prevent breaking the here-string.
            safe_command = command.replace("'", "''")
            final_script_string = POWERSHELL_TIMEOUT_WRAPPER_TEMPLATE.format(command=safe_command)
            
            # Step 2: Encode the ENTIRE wrapper script to Base64 using UTF-16LE.
            encoded_script_bytes = base64.b64encode(final_script_string.encode('utf-16-le'))
            encoded_script_string = encoded_script_bytes.decode('ascii')

            # Step 3: Execute using -EncodedCommand. This is the most robust method.
            command_id = self.winrm_protocol.run_command(self.shell_id, 'powershell.exe', ['-EncodedCommand', encoded_script_string])
            stdout, stderr, return_code = self.winrm_protocol.get_command_output(self.shell_id, command_id)
            self.winrm_protocol.cleanup_command(self.shell_id, command_id)

            if return_code != 0:
                 return CommandOutput(
                    stdout="", 
                    stderr=f"Underlying WinRM transport error: {stderr.decode('utf-8', errors='ignore').strip()}", 
                    return_code=return_code
                )
            
            try:
                response_str = stdout.decode('utf-8', errors='ignore').strip()
                if not response_str:
                    return CommandOutput(stdout="", stderr="Execution produced no JSON output.", return_code=-1)
                response_json = json.loads(response_str)
                return CommandOutput(
                    stdout=response_json.get("Stdout", ""),
                    stderr=response_json.get("Stderr", ""),
                    return_code=response_json.get("ReturnCode", -1)
                )
            except json.JSONDecodeError as e:
                return CommandOutput(stdout="", stderr=f"Failed to parse remote JSON: {e}. Raw: {stdout.decode('utf-8', errors='ignore')}", return_code=-1)

        except (WinRMError, WinRMTransportError, WinRMOperationTimeoutError) as e:
            self.shell_id = None
            return CommandOutput(stdout="", stderr=f"Fatal WinRM Error, shell has died: {e}", return_code=-1)
        except Exception as e:
            return CommandOutput(stdout="", stderr=f"Unexpected Python error in lab_connector: {e}", return_code=-1)

    def query_splunk(self, search_query: str) -> List[SplunkLogEvent]:
        # This function remains the same
        kwargs_search = {"exec_mode": "blocking", "output_mode": "json"}
        if not search_query.strip().startswith('search'):
            search_query = "search " + search_query
        try:
            job = self.splunk_service.jobs.create(search_query, **kwargs_search)
            reader = results.JSONResultsReader(job.results())
            validated_results = []
            for item in reader:
                if isinstance(item, dict):
                    try: validated_results.append(SplunkLogEvent.model_validate(item))
                    except ValidationError: continue
            return validated_results
        except Exception as e:
            print(f"Warning: A Splunk query failed to execute. Error: {e}", file=sys.stderr)
            return []
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

POWERSHELL_HYBRID_WRAPPER = """
$commandToRun = @'
{command}
'@
$timeoutSeconds = 25
$result = @{{
    Stdout = ""
    Stderr = ""
    ReturnCode = -1
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
        $result.Stderr = "Command timed out on the server after $timeoutSeconds seconds."
        $result.ReturnCode = 124
    }}
}} catch {{
    $result.Stderr = "Wrapper Script Error: $($_.Exception.Message)"
    $result.ReturnCode = 1
}} finally {{
    if ($job) {{
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -ErrorAction SilentlyContinue -Force
    }}
}}
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
                operation_timeout_sec=35,
                read_timeout_sec=45
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
    
    # [DEFINITIVE FIX] Add the reset_shell method back into the class.
    def reset_shell(self):
        """Performs a full teardown and rebuild of the WinRM connection."""
        console.print("\n[bold yellow]Shell Resetting:[/bold yellow] Discarding and rebuilding full WinRM connection...", end="")
        self.close()
        time.sleep(1) # Give OS resources a moment to clear
        try:
            self._connect_winrm()
            console.print("[bold green]...Reset Complete. New connection active.[/bold green]")
            return True
        except (WinRMError, WinRMTransportError) as e:
            console.print(f"[bold red]...FATAL: Failed to re-establish connection after reset! Error: {e}[/bold red]")
            return False

    def run_remote_powershell(self, command: str) -> CommandOutput:
        if not self.shell_id or not self.winrm_protocol:
             # If the connection is dead, try to reset it.
             if not self.reset_shell():
                 return CommandOutput(Stdout="", Stderr="FATAL: WinRM connection is dead and could not be recovered.", ReturnCode=-1)

        try:
            safe_command = command.replace("'", "''")
            final_script = POWERSHELL_HYBRID_WRAPPER.format(command=safe_command)
            encoded_script = base64.b64encode(final_script.encode('utf-16-le')).decode('ascii')
            command_id = self.winrm_protocol.run_command(self.shell_id, 'powershell.exe', ['-EncodedCommand', encoded_script])
            stdout, stderr, return_code = self.winrm_protocol.get_command_output(self.shell_id, command_id)
            self.winrm_protocol.cleanup_command(self.shell_id, command_id)

            if return_code != 0:
                return CommandOutput(Stdout="", Stderr=f"WinRM Transport Error: Process exited with code {return_code}. Stderr: {stderr.decode('utf-8')}", ReturnCode=return_code)

            try:
                response_str = stdout.decode('utf-8', errors='ignore').strip()
                return CommandOutput.model_validate_json(response_str)
            except (json.JSONDecodeError, ValidationError) as e:
                return CommandOutput(Stdout="", Stderr=f"Failed to parse remote JSON response: {e}. Raw: {response_str}", ReturnCode=-1)
        except (WinRMError, WinRMTransportError, WinRMOperationTimeoutError) as e:
            console.print(f"\n[bold red]Caught fatal transport error, triggering full reset. Error: {e}[/bold red]")
            self.reset_shell()
            return CommandOutput(Stdout="", Stderr=f"Fatal WinRM Error, connection was reset: {e}", ReturnCode=-1)
        except Exception as e:
            return CommandOutput(Stdout="", Stderr=f"Unexpected Python error: {e}", ReturnCode=-1)

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
# powershell_sentinel/lab_connector.py

import os
import sys
import json
import time
import splunklib.client as client
import splunklib.results as results
import winrm
from winrm.exceptions import WinRMError, WinRMTransportError, WinRMOperationTimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List
from .models import CommandOutput, SplunkLogEvent
from rich.console import Console # Import for better printing

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


class LabConnection:
    """A class to manage connections and interactions with the lab environment."""

    def __init__(self):
        """Initializes the connection objects for WinRM and Splunk."""
        self.winrm_protocol = None
        self.splunk_service = None
        self.shell_id = None

        if not all([VICTIM_VM_IP, VICTIM_VM_USER, VICTIM_VM_PASS, SPLUNK_PASS]):
            raise ValueError("One or more required environment variables are not set.")
        
        try:
            # [DEFINITIVE FIX] Define timeouts directly in the protocol.
            # operation_timeout_sec is the crucial one for catching hangs.
            self.winrm_protocol = winrm.Protocol(
                endpoint=f"http://{VICTIM_VM_IP}:5985/wsman",
                transport='ntlm', username=VICTIM_VM_USER, password=VICTIM_VM_PASS,
                server_cert_validation='ignore',
                operation_timeout_sec=30, # Max time for a single operation (like get_command_output)
                read_timeout_sec=40       # Max time to wait for a response packet
            )
            self.shell_id = self.winrm_protocol.open_shell()
        except (WinRMError, WinRMTransportError) as e:
            console.print(f"FATAL: Failed to connect or open a shell via WinRM. Error: {e}", style="bold red")
            raise
        
        try:
            self.splunk_service = client.connect(
                host=SPLUNK_HOST, port=SPLUNK_PORT, username=SPLUNK_USER, password=SPLUNK_PASS
            )
            self.splunk_service.apps.list()
        except Exception as e:
            console.print(f"FATAL: Failed to connect to Splunk service. Error: {e}", style="bold red")
            if self.shell_id: self.winrm_protocol.close_shell(self.shell_id)
            raise

    def close(self):
        """Closes the persistent WinRM shell."""
        if self.shell_id:
            try:
                self.winrm_protocol.close_shell(self.shell_id)
                console.print("\n[green]Persistent WinRM shell closed.[/green]")
            except (WinRMError, WinRMTransportError):
                console.print("\n[yellow]Could not gracefully close WinRM shell (it was likely already terminated).[/yellow]")
            finally:
                self.shell_id = None

    def run_remote_powershell(self, command: str) -> CommandOutput:
        """Executes a PowerShell command safely on the remote Victim VM."""
        if not self.shell_id:
            return CommandOutput(stdout="", stderr="WinRM shell is not open.", return_code=-1)
        
        try:
            # [DEFINITIVE FIX] No more PowerShell wrapper. We execute the command directly.
            # The protocol's `operation_timeout_sec` will handle hangs.
            command_id = self.winrm_protocol.run_command(self.shell_id, command)
            stdout, stderr, return_code = self.winrm_protocol.get_command_output(self.shell_id, command_id)
            self.winrm_protocol.cleanup_command(self.shell_id, command_id)
            
            return CommandOutput(
                stdout=stdout.decode('utf-8', errors='ignore').strip(),
                stderr=stderr.decode('utf-8', errors='ignore').strip(),
                return_code=return_code
            )

        except WinRMOperationTimeoutError:
            # This is the new, clean way to catch a hanging command.
            # We must now manually clean up the broken shell and open a new one.
            console.print(f"\n[bold yellow]Warning: A command timed out. Re-establishing shell to prevent instability...[/bold yellow]")
            try:
                self.winrm_protocol.close_shell(self.shell_id)
            except Exception:
                pass # The shell is likely already dead, so we don't care about errors here.
            
            self.shell_id = self.winrm_protocol.open_shell()
            console.print("[bold green]Shell re-established successfully.[/bold green]")
            
            return CommandOutput(
                stdout="",
                stderr=f"Command timed out after {self.winrm_protocol.operation_timeout_sec} seconds.",
                return_code=-1
            )
        except (WinRMError, WinRMTransportError) as e:
            # A fatal error occurred, the shell is dead.
            self.shell_id = None 
            return CommandOutput(
                stdout="", stderr=f"Fatal WinRM Error: {e}", return_code=-1
            )
        except Exception as e:
            return CommandOutput(
                stdout="", stderr=f"An unexpected Python error occurred in lab_connector: {e}", return_code=-1
            )

    def query_splunk(self, search_query: str) -> List[SplunkLogEvent]:
        """Executes a search query against the local Splunk instance."""
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
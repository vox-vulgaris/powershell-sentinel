# scripts/verify_lab_config.py

import re
from rich.console import Console
from powershell_sentinel.lab_connector import LabConnection

# Define the minimum required settings for our application
REQUIRED_SETTINGS = {
    "MaxShellsPerUser": 50,
    "MaxConcurrentOperationsPerUser": 1500,
    "MaxMemoryPerShellMB": 1024
}

def parse_winrm_output(output: str) -> dict:
    """Parses the key-value output of a 'winrm get' command."""
    # [DEFINITIVE FIX] Add a guard clause to handle None or empty string input.
    if not output:
        return {}
        
    settings = {}
    for line in output.splitlines():
        match = re.match(r'^\s*([A-Za-z]+)\s*=\s*(\d+)', line)
        if match:
            key = match.group(1)
            value = int(match.group(2))
            settings[key] = value
    return settings

def verify_lab_configuration():
    """
    Connects to the remote lab VM and verifies its WinRM configuration
    is suitable for the high-volume data generation task.
    """
    console = Console()
    console.print("[bold cyan]--- Lab Configuration Verifier ---[/bold cyan]")
    try:
        console.print("Attempting to connect to the lab VM...", end="")
        lab = LabConnection()
        console.print("[green]Success.[/green]")
    except Exception as e:
        console.print(f"\n[bold red]Error: Could not connect to the lab VM.[/bold red]")
        console.print(f"Please check your .env file and ensure the VM is running. Details: {e}")
        return

    try:
        console.print("Fetching current WinRM configuration...")
        winrs_config_raw = lab.run_remote_powershell("winrm get winrm/config/winrs").stdout
        service_config_raw = lab.run_remote_powershell("winrm get winrm/config/service").stdout
        
        current_settings = {
            **parse_winrm_output(winrs_config_raw),
            **parse_winrm_output(service_config_raw)
        }
    except Exception as e:
        console.print(f"\n[bold red]Error: Failed to fetch configuration from the VM.[/bold red]")
        console.print(f"Details: {e}")
    finally:
        lab.close()

    console.print("\n[bold]Verifying settings against required minimums:[/bold]")
    all_ok = True
    for key, required_value in REQUIRED_SETTINGS.items():
        current_value = current_settings.get(key)
        if current_value is not None and current_value >= required_value:
            status = f"[green]OK[/green]"
            console.print(f"- {key}: {current_value} >= {required_value} ({status})")
        else:
            status = f"[bold red]FAIL[/bold red]"
            console.print(f"- {key}: {current_value} < {required_value} ({status})")
            all_ok = False
            
    if all_ok:
        console.print("\n[bold green]✅ Lab configuration check passed.[/bold green]")
    else:
        console.print("\n[bold red]❌ Lab configuration check failed.[/bold red]")
        console.print("Please run the required [yellow]winrm set ...[/yellow] commands on the VM.")

if __name__ == '__main__':
    verify_lab_configuration()
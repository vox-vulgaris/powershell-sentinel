# Phase 2: Data Factory - Curation Tooling
# Index: [8]
#
# This file is the main user-facing tool for managing the primitives dataset.
# It's an interactive command-line interface (CLI) that orchestrates the
# modules developed in this phase (snapshot_differ, recommendation_engine, etc.)
# into a coherent, step-by-step workflow for the user.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Main Menu: Must offer options to [1] Manage a Dataset, [2] Re-calculate Global Statistics, and [q] Quit.
# 2. Dataset Workflow Menu: Must provide [1] Add/Edit a Primitive, [2] Run BATCH Telemetry Discovery, [3] Run BATCH Telemetry Curation.
# 3. Validation on Load: Must load the `primitives_library.json` and immediately validate its contents
#    into a list of Pydantic `Primitive` models. The program should exit with a clear error if validation fails.
# 4. BATCH Telemetry Discovery:
#    - Must iterate through all `Primitive` models in the library.
#    - For each, it will use `lab_connector.py` to run a "before" log query, execute the command, and run an "after" log query.
#    - It will then call `snapshot_differ.py` to get the `delta_logs` as `List[SplunkLogEvent]`.
#    - It must serialize and save these `delta_logs` to a corresponding file in `data/interim/delta_logs/`.
#    - Must prompt the user for confirmation if `delta_logs` for a primitive already exist.
# 5. BATCH Telemetry Curation:
#    - Must offer "Interactive" and "Automated" modes.
#    - It will load the `delta_logs` for each primitive and validate them into `List[SplunkLogEvent]`.
#    - It will call `recommendation_engine.py` to get recommendations (`List[SplunkLogEvent]`).
#    - In Interactive mode, it presents the recommendations and prompts the user for a y/n/manual selection.
#    - In Automated mode, it accepts any recommendations that meet a predefined confidence threshold.
#    - After selection, it calls `rule_formatter.py` to format the selections into `List[TelemetryRule]`.
#    - Finally, it updates the `telemetry_rules` attribute of the in-memory `Primitive` object.
# 6. Saving: After curation is complete, it must serialize the updated list of `Primitive` models back to the JSON file.


import json
import os
from typing import List, Dict
from pydantic import ValidationError

# To create a nice CLI, we'll use the 'rich' library. Add 'rich' to requirements.txt
from rich.console import Console
from rich.prompt import Prompt, Confirm

# Import all models and backend modules
from powershell_sentinel.models import Primitive, SplunkLogEvent, TelemetryRule
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules import snapshot_differ, statistics_calculator, recommendation_engine, rule_formatter

class PrimitivesManager:
    """An interactive CLI for managing and curating the primitives knowledge base."""

    def __init__(self, primitives_path: str, deltas_path: str):
        self.primitives_path = primitives_path
        self.deltas_path = deltas_path
        self.console = Console()
        self.lab = LabConnection()
        self.primitives: List[Primitive] = self._load_and_validate_primitives()

    def _load_and_validate_primitives(self) -> List[Primitive]:
        """Loads the primitives JSON and validates it into a list of Pydantic models."""
        self.console.print(f"Loading primitives from [cyan]{self.primitives_path}[/]...")
        try:
            with open(self.primitives_path, 'r') as f:
                data = json.load(f)
            # This is the validation step! It tries to create a list of Primitive models.
            # If the data is malformed, it raises a ValidationError.
            validated_primitives = [Primitive.model_validate(p) for p in data]
            self.console.print(f"[green]Successfully loaded and validated {len(validated_primitives)} primitives.[/green]")
            return validated_primitives
        except FileNotFoundError:
            self.console.print(f"[bold red]Error: Primitives file not found at {self.primitives_path}[/bold red]")
            exit(1)
        except (json.JSONDecodeError, ValidationError) as e:
            self.console.print(f"[bold red]Error loading or validating primitives: {e}[/bold red]")
            exit(1)

    def _save_primitives(self):
        """Serializes the list of Pydantic models back to a JSON file."""
        self.console.print(f"Saving primitives to [cyan]{self.primitives_path}[/]...")
        # Convert the list of Pydantic models back into a list of dictionaries
        primitives_as_dict = [p.model_dump(mode='json') for p in self.primitives]
        try:
            with open(self.primitives_path, 'w') as f:
                json.dump(primitives_as_dict, f, indent=2)
            self.console.print("[green]Save successful.[/green]")
        except IOError as e:
            self.console.print(f"[bold red]Error saving primitives: {e}[/bold red]")

    def run_telemetry_discovery(self):
        """Orchestrates the BATCH Telemetry Discovery workflow."""
        self.console.print("\n--- Starting BATCH Telemetry Discovery ---", style="bold blue")
        if not os.path.exists(self.deltas_path):
            os.makedirs(self.deltas_path)

        for primitive in self.primitives:
            self.console.print(f"\nProcessing [yellow]{primitive.primitive_id}[/yellow]: {primitive.primitive_command}")
            delta_file_path = os.path.join(self.deltas_path, f"{primitive.primitive_id}.json")

            if os.path.exists(delta_file_path):
                if not Confirm.ask(f"[yellow]Delta log already exists for {primitive.primitive_id}. Overwrite?[/yellow]"):
                    self.console.print("Skipping.")
                    continue
            
            # TODO: Implement the actual discovery logic.
            # 1. Query Splunk for "before" logs: `before_logs: List[SplunkLogEvent] = self.lab.query_splunk(...)`
            # 2. Execute `primitive.primitive_command` using `self.lab.run_remote_powershell`.
            # 3. Query Splunk for "after" logs: `after_logs: List[SplunkLogEvent] = self.lab.query_splunk(...)`
            # 4. Use `snapshot_differ.get_delta_logs` to get the `delta_logs: List[SplunkLogEvent]`.
            # 5. Save the `delta_logs` to the `delta_file_path`.
            #    - Serialize Pydantic models: `[log.model_dump(mode='json') for log in delta_logs]`
            self.console.print(f"[green]Delta log saved for {primitive.primitive_id}.[/green]")
        
        self.console.print("\n--- BATCH Telemetry Discovery Complete ---", style="bold blue")


    def run_telemetry_curation(self):
        """Orchestrates the BATCH Telemetry Curation workflow."""
        self.console.print("\n--- Starting BATCH Telemetry Curation ---", style="bold blue")
        # TODO: Implement the full curation logic.
        # 1. Pre-calculate statistics using `statistics_calculator` module.
        # 2. Loop through each `primitive` in `self.primitives`.
        # 3. Load its corresponding `delta_logs` file and validate into `List[SplunkLogEvent]`.
        # 4. Call `recommendation_engine.get_recommendations` passing the delta logs, stats, and `primitive.mitre_ttps`.
        # 5. This returns a `List[SplunkLogEvent]` of recommendations.
        # 6. Prompt user for selection (Interactive mode) or auto-accept (Automated mode).
        # 7. Call `rule_formatter.format_rules` on the selected logs to get a `List[TelemetryRule]`.
        # 8. Update the primitive object: `primitive.telemetry_rules = formatted_rules`.
        
        # After the loop...
        self._save_primitives()
        self.console.print("\n--- BATCH Telemetry Curation Complete ---", style="bold blue")

    def start(self):
        """The main entry point and loop for the CLI."""
        while True:
            self.console.print("\n--- Primitives Manager Main Menu ---", style="bold magenta")
            choice = Prompt.ask(
                "Choose an option",
                choices=["1", "2", "3", "q"],
                default="1",
                show_choices=True,
                description="[1] Telemetry Discovery\n[2] Telemetry Curation\n[3] Recalculate Stats\n[q] Quit"
            )
            if choice == '1':
                self.run_telemetry_discovery()
            elif choice == '2':
                self.run_telemetry_curation()
            elif choice == '3':
                # TODO: Implement call to statistics_calculator
                self.console.print("Statistics recalculated.", style="green")
            elif choice == 'q':
                self.console.print("Exiting.")
                break

if __name__ == '__main__':
    # This allows running the manager directly.
    # Example of how to run the manager
    PRIMITIVES_FILE = "data/source/primitives_library.json"
    DELTAS_DIR = "data/interim/delta_logs"
    manager = PrimitivesManager(primitives_path=PRIMITIVES_FILE, deltas_path=DELTAS_DIR)
    manager.start()
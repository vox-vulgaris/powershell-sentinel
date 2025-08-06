# Phase 3: The Curation Controller, Dataset Expansion & Validation
# Index: [8]
#
# This file is the main user-facing tool for managing the primitives dataset and,
# crucially, for teaching the system how to parse new telemetry. It's an
# interactive CLI that orchestrates the backend modules into a coherent,
# human-in-the-loop workflow.
#
# REQUIREMENTS:
# 1. Main Menu: Must offer options to manage the dataset and re-calculate statistics.
# 2. Validation on Load: Must load and validate all source JSON files using Pydantic.
# 3. BATCH Telemetry Discovery: Must orchestrate the execution of primitives in the lab
#    and save the resulting raw delta logs.
# 4. Interactive Parsing Workflow: If an unparseable log is found during curation,
#    it must prompt the analyst to define a new, persistent parsing rule.
# 5. BATCH Telemetry Curation: Must orchestrate the full workflow of parsing,
#    scoring, recommending, and final user selection of telemetry rules.
# 6. Persistence: Must save all changes to the primitives library and parsing rules.

import json
import os
import re
import time
import shutil
from typing import List, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from powershell_sentinel.models import Primitive, SplunkLogEvent, TelemetryRule, ParsingRule, ExtractionMethodEnum, IntentEnum, MitreTTPEnum
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules import snapshot_differ, statistics_calculator, recommendation_engine, rule_formatter

class PrimitivesManager:
    """An interactive CLI for managing the primitives knowledge base and parsing rules."""

    def __init__(self, primitives_path: str, parsing_rules_path: str, deltas_path: str, mitre_lib_path: str, parsing_logs_path: str, curating_logs_path: str):
        self.primitives_path = primitives_path
        self.parsing_rules_path = parsing_rules_path
        self.deltas_path = deltas_path
        self.mitre_lib_path = mitre_lib_path
        self.parsing_logs_path = parsing_logs_path
        self.curating_logs_path = curating_logs_path
        self.console = Console()
        self.lab = LabConnection()
        self.primitives: List[Primitive] = self._load_and_validate(self.primitives_path, Primitive)
        self.parsing_rules: List[ParsingRule] = self._load_and_validate(self.parsing_rules_path, ParsingRule, default=[])
        with open(self.mitre_lib_path, 'r', encoding='utf-8') as f:
            self.mitre_ttp_library = json.load(f)

    def _load_and_validate(self, path: str, model: Type[BaseModel], default: Optional[list] = None) -> List[BaseModel]:
        """Generic loader for our JSON data files, with Pydantic validation."""
        if not os.path.exists(path) and default is not None:
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content:
                    return default if default is not None else []
                data = json.loads(content)
            return [model.model_validate(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
            self.console.print(f"[bold red]Error loading or validating {path}: {e}[/bold red]")
            exit(1)

    def _save_json(self, path: str, data: List[BaseModel] | Dict):
        """Generic saver for our Pydantic model lists or dictionaries."""
        self.console.print(f"Saving data to [cyan]{path}[/]...")
        
        data_to_dump = data
        if isinstance(data, list) and all(isinstance(p, BaseModel) for p in data):
             data_to_dump = [p.model_dump(mode='json', by_alias=True) for p in data]
        elif isinstance(data, dict):
            data_to_dump = {k: [i.model_dump(mode='json', by_alias=True) for i in v] if isinstance(v, list) else v for k, v in data.items()}

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data_to_dump, f, indent=2)
            self.console.print("[green]Save successful.[/green]")
        except IOError as e:
            self.console.print(f"[bold red]Error saving file {path}: {e}[/bold red]")

    # --- Main Menu and Control Flow ---
    def start(self):
        """The main entry point and menu loop for the CLI."""
        self.console.print("[bold green]PowerShell-Sentinel Primitives Manager[/bold green]")
        while True:
            self.console.print("\n[bold]Main Menu[/bold]")
            self.console.print("1. Add New Primitive")
            self.console.print("2. Telemetry Discovery")
            self.console.print("3. Telemetry Curation")
            self.console.print("4. Assemble Practitioner Review Package")
            self.console.print("q. Quit")
            choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "q"], default="1")

            if choice == '1':
                self._add_primitive()
            elif choice == '2':
                self._telemetry_discovery_menu()
            elif choice == '3':
                self._telemetry_curation_menu()
            elif choice == '4':
                self._assemble_review_package()
            elif choice == 'q':
                self.console.print("Exiting.")
                break

    def _telemetry_discovery_menu(self):
        """Displays options for running telemetry discovery."""
        while True:
            self.console.print("\n[bold]Telemetry Discovery[/bold]")
            self.console.print("1. Batch Mode (All Primitives)")
            self.console.print("2. Individual Mode (Select a Primitive)")
            self.console.print("b. Back to Main Menu")
            choice = Prompt.ask("Choose an option", choices=["1", "2", "b"], default="1")

            if choice == '1':
                self.run_telemetry_discovery()
            elif choice == '2':
                primitive_id = self._select_primitive()
                if primitive_id:
                    self.run_telemetry_discovery(primitive_id=primitive_id)
            elif choice == 'b':
                break

    def _telemetry_curation_menu(self):
        """Displays options for running telemetry curation."""
        while True:
            self.console.print("\n[bold]Telemetry Curation[/bold]")
            self.console.print("1. Batch Mode (All Primitives)")
            self.console.print("2. Individual Mode (Select a Primitive)")
            self.console.print("3. Dump Unparsed Logs for Review")
            self.console.print("4. Dump Uncurated Logs for Review")
            self.console.print("b. Back to Main Menu")
            choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "b"], default="1")
            
            if choice == '1':
                self.run_telemetry_curation()
            elif choice == '2':
                primitive_id = self._select_primitive()
                if primitive_id:
                    self.run_telemetry_curation(primitive_id=primitive_id)
            elif choice == '3':
                self.dump_unparsed_logs()
            elif choice == '4':
                self.dump_uncurated_logs()
            elif choice == 'b':
                break
    
    def _select_primitive(self) -> Optional[str]:
        """Displays a menu of primitives and returns the selected ID."""
        self.console.print("\n--- Select a Primitive ---", style="bold blue")
        table = Table(title="Available Primitives")
        table.add_column("ID"); table.add_column("Command")
        
        primitive_map = {p.primitive_id: p for p in self.primitives}
        for primitive_id, primitive in primitive_map.items():
            table.add_row(primitive_id, primitive.primitive_command)
        
        self.console.print(table)
        
        choice = Prompt.ask("Enter the Primitive ID to select", choices=list(primitive_map.keys()))
        return choice

    def _add_primitive(self):
        """Handles the interactive workflow for adding a new primitive."""
        self.console.print("\n--- Adding New Primitive ---", style="bold blue")
        command = Prompt.ask("Enter the full primitive command")
        intent_map = {str(i + 1): item for i, item in enumerate(IntentEnum)}
        intent_table = Table(title="Select Intent(s)")
        intent_table.add_column("#"); intent_table.add_column("Intent")
        for i, item in intent_map.items():
            intent_table.add_row(i, item.value)
        self.console.print(intent_table)
        intent_selection_str = Prompt.ask("Enter numbers for intent (e.g., '1,3')")
        selected_intents = [intent_map[i.strip()] for i in intent_selection_str.split(',') if i.strip() in intent_map]
        ttp_map = {str(i + 1): key for i, key in enumerate(self.mitre_ttp_library.keys())}
        ttp_table = Table(title="Select MITRE TTP(s)")
        ttp_table.add_column("#"); ttp_table.add_column("TTP ID"); ttp_table.add_column("Name")
        for i, key in ttp_map.items():
            ttp_table.add_row(i, key, self.mitre_ttp_library[key]['name'])
        self.console.print(ttp_table)
        ttp_selection_str = Prompt.ask("Enter numbers for TTPs (e.g., '1,3')")
        selected_ttps = [MitreTTPEnum[ttp_map[i.strip()].replace('.', '_')] for i in ttp_selection_str.split(',') if i.strip() in ttp_map]
        new_id_num = max([int(p.primitive_id.split('-')[1]) for p in self.primitives] or [0]) + 1
        new_primitive = Primitive(
            primitive_id=f"PS-{new_id_num:03d}",
            primitive_command=command,
            intent=selected_intents,
            mitre_ttps=selected_ttps,
            telemetry_rules=[]
        )
        self.primitives.append(new_primitive)
        self._save_json(self.primitives_path, self.primitives)
        self.console.print(f"New primitive [cyan]{new_primitive.primitive_id}[/cyan] added successfully.")

    def run_telemetry_discovery(self, primitive_id: Optional[str] = None):
        """Orchestrates the BATCH Telemetry Discovery workflow."""
        self.console.print("\n--- Starting Telemetry Discovery ---", style="bold blue")
        
        primitives_to_run = self.primitives
        if primitive_id:
            primitives_to_run = [p for p in self.primitives if p.primitive_id == primitive_id]
            if not primitives_to_run:
                self.console.print(f"[red]Primitive ID {primitive_id} not found.[/red]")
                return

        if not Confirm.ask(f"This will execute {len(primitives_to_run)} command(s) on the remote lab. Continue?", default=True):
            return

        for primitive in primitives_to_run:
            delta_log_path = os.path.join(self.deltas_path, f"{primitive.primitive_id}.json")
            if os.path.exists(delta_log_path):
                if not Confirm.ask(f"Delta log for [cyan]{primitive.primitive_id}[/cyan] already exists. Overwrite?"):
                    continue
            self.console.print(f"Discovering telemetry for [cyan]{primitive.primitive_id}[/cyan]...")
            try:
                before_logs = self.lab.query_splunk('index=* earliest=-1m')
                time.sleep(2)
                self.lab.run_remote_powershell(primitive.primitive_command)
                time.sleep(5)
                after_logs = self.lab.query_splunk('index=* earliest=-1m')
                delta_logs = snapshot_differ.get_delta_logs(before_logs, after_logs)
                self._save_json(delta_log_path, delta_logs)
                self.console.print(f"Discovered and saved {len(delta_logs)} new delta logs.")
            except Exception as e:
                self.console.print(f"[bold red]Error during discovery for {primitive.primitive_id}: {e}[/bold red]")
        self.console.print("\n--- Telemetry Discovery Complete ---", style="bold blue")

    def _apply_parsing_rule(self, rule: ParsingRule, raw_text: str) -> Optional[str]:
        if rule.extraction_method == ExtractionMethodEnum.REGEX:
            match = re.search(rule.detail_key_or_pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match and match.groups() else None
        elif rule.extraction_method == ExtractionMethodEnum.KEY_VALUE:
            pattern = re.escape(rule.detail_key_or_pattern) + r'=(.*?)(?:\s*\w+=|$)'
            match = re.search(pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match and match.groups() else None
        return None

    def _parse_log_with_rules(self, log: SplunkLogEvent) -> Optional[TelemetryRule]:
        """Finds the first applicable parsing rule and uses it to parse a raw log."""
        for rule in self.parsing_rules:
            if str(rule.event_id) in log.raw:
                if rule.source_match and rule.source_match not in log.raw:
                    continue 
                
                details = self._apply_parsing_rule(rule, log.raw)
                if details:
                    return TelemetryRule(source=log.source, event_id=rule.event_id, details=details)
        return None

    def _prompt_for_new_parsing_rule(self, log: SplunkLogEvent) -> Optional[TelemetryRule]:
        """Handles the interactive workflow for defining a new parsing rule."""
        self.console.print("\n[bold yellow]-- New Log Type Encountered --[/bold yellow]")
        
        timestamp = int(time.time())
        log_dump_filename = f"unparseable_log_{timestamp}.txt"
        log_dump_path = os.path.join(self.parsing_logs_path, log_dump_filename)
        
        try:
            os.makedirs(self.parsing_logs_path, exist_ok=True)
            with open(log_dump_path, 'w', encoding='utf-8') as f:
                f.write(log.raw)
            self.console.print(f"Full log content saved to: [cyan]{log_dump_path}[/cyan]")
        except IOError as e:
            self.console.print(f"[bold red]Could not write log to file: {e}[/bold red]")

        if not Confirm.ask("\nWould you like to define a new parsing rule now?", default=True):
            return None

        rule_name = Prompt.ask("Enter a unique name for this rule (e.g., Sysmon-EID11-FileCreate)")
        event_id = int(Prompt.ask("What is the primary Event ID for this rule?"))
        
        source_match_input = Prompt.ask("Enter a 'source_match' string (optional, press Enter to skip)").strip()
        source_match = source_match_input if source_match_input else None

        method_str = Prompt.ask("What is the extraction method?", choices=["regex", "key_value"], default="key_value")
        extraction_method = ExtractionMethodEnum(method_str)
        detail_key_or_pattern = Prompt.ask("Enter the detail key or regex pattern to extract")
        
        new_rule = ParsingRule(
            rule_name=rule_name, 
            event_id=event_id, 
            source_match=source_match,
            extraction_method=extraction_method, 
            detail_key_or_pattern=detail_key_or_pattern
        )

        self.parsing_rules.append(new_rule)
        self._save_json(self.parsing_rules_path, self.parsing_rules)
        self.console.print(f"[green]New parsing rule '{rule_name}' saved.[/green]")
        
        return self._parse_log_with_rules(log)

    def run_telemetry_curation(self, primitive_id: Optional[str] = None):
        """Orchestrates the telemetry curation workflow."""
        self.console.print("\n--- Starting Telemetry Curation ---", style="bold blue")
        
        primitives_to_run = self.primitives
        if primitive_id:
            primitives_to_run = [p for p in self.primitives if p.primitive_id == primitive_id]
            if not primitives_to_run:
                self.console.print(f"[red]Primitive ID {primitive_id} not found.[/red]")
                return

        all_parsed_rules: Dict[str, List[TelemetryRule]] = {}
        for primitive in primitives_to_run:
            p_id = primitive.primitive_id
            delta_log_path = os.path.join(self.deltas_path, f"{p_id}.json")
            if not os.path.exists(delta_log_path): continue
            raw_logs = self._load_and_validate(delta_log_path, SplunkLogEvent, default=[])
            parsed_for_primitive = []
            for log in raw_logs:
                parsed_rule = self._parse_log_with_rules(log)
                if not parsed_rule:
                    parsed_rule = self._prompt_for_new_parsing_rule(log)
                if parsed_rule:
                    parsed_for_primitive.append(parsed_rule)
            all_parsed_rules[p_id] = parsed_for_primitive
        
        rarity = statistics_calculator.calculate_global_rarity(self.primitives)
        relevance = statistics_calculator.calculate_local_relevance(self.primitives)
        
        for primitive in primitives_to_run:
            if primitive.primitive_id not in all_parsed_rules: continue
            self.console.print(f"\n--- Curating Primitive: [bold cyan]{primitive.primitive_id}[/bold cyan] ---")
            self.console.print(f"Command: [green]{primitive.primitive_command}[/green]")
            parsed_rules_for_primitive = all_parsed_rules[primitive.primitive_id]
            if not parsed_rules_for_primitive:
                self.console.print("[yellow]No parseable logs for this primitive.[/yellow]")
                continue
            recommendations = recommendation_engine.get_recommendations(parsed_rules=parsed_rules_for_primitive, global_rarity=rarity, local_relevance=relevance, primitive_ttps=primitive.mitre_ttps)
            if not recommendations:
                self.console.print("[yellow]No high-confidence recommendations found.[/yellow]")
                continue
            table = Table(title="Recommended Telemetry Signals")
            table.add_column("#"); table.add_column("Event ID"); table.add_column("Source"); table.add_column("Details")
            for i, rule in enumerate(recommendations):
                table.add_row(str(i + 1), str(rule.event_id), rule.source, rule.details)
            self.console.print(table)
            selection_str = Prompt.ask("Enter rule numbers to keep (e.g., '1,3'), 'all', or 'none'", default="all")
            final_selection = []
            if selection_str.lower() == 'all':
                final_selection = recommendations
            elif selection_str.lower() != 'none':
                try:
                    indices = [int(i.strip()) - 1 for i in selection_str.split(',')]
                    final_selection = [recommendations[i] for i in indices if 0 <= i < len(recommendations)]
                except ValueError:
                    self.console.print("[red]Invalid selection. Defaulting to none.[/red]")
            primitive.telemetry_rules = rule_formatter.format_rules(final_selection)
            self.console.print(f"Saved {len(final_selection)} rules for {primitive.primitive_id}.")
        
        self._save_json(self.primitives_path, self.primitives)
        self.console.print("\n--- Telemetry Curation Complete ---", style="bold blue")

    def dump_unparsed_logs(self):
        """Finds all logs that can't be parsed by current rules and dumps them to a file."""
        self.console.print("\n--- Dumping Unparsed Logs for Review ---", style="bold blue")
        unparsed_logs_collection: List[SplunkLogEvent] = []
        
        for primitive in self.primitives:
            delta_log_path = os.path.join(self.deltas_path, f"{primitive.primitive_id}.json")
            if not os.path.exists(delta_log_path):
                continue
            
            self.console.print(f"Checking [cyan]{primitive.primitive_id}[/cyan]...")
            raw_logs = self._load_and_validate(delta_log_path, SplunkLogEvent, default=[])
            
            for log in raw_logs:
                if self._parse_log_with_rules(log) is None:
                    unparsed_logs_collection.append(log)
        
        if not unparsed_logs_collection:
            self.console.print("[green]No unparsed logs found. All telemetry is accounted for![/green]")
            return

        output_path = os.path.join(self.parsing_logs_path, "unparsed_for_review.json")
        self.console.print(f"\nFound {len(unparsed_logs_collection)} unparsed logs.")
        self._save_json(output_path, unparsed_logs_collection)
        self.console.print(f"Dumped unparsed logs to [cyan]{output_path}[/cyan]")

    def dump_uncurated_logs(self):
        """
        Finds all parsed logs for primitives that haven't been curated yet and
        dumps them to a single file for efficient, offline review.
        """
        self.console.print("\n--- Dumping Uncurated Logs for Review ---", style="bold blue")
        uncurated_data: Dict[str, List[TelemetryRule]] = {}
        
        for primitive in self.primitives:
            if primitive.telemetry_rules:
                continue

            delta_log_path = os.path.join(self.deltas_path, f"{primitive.primitive_id}.json")
            if not os.path.exists(delta_log_path):
                continue
            
            self.console.print(f"Checking [cyan]{primitive.primitive_id}[/cyan]...")
            raw_logs = self._load_and_validate(delta_log_path, SplunkLogEvent, default=[])
            
            parsed_logs_for_primitive = []
            for log in raw_logs:
                parsed_rule = self._parse_log_with_rules(log)
                if parsed_rule:
                    parsed_logs_for_primitive.append(parsed_rule)
            
            if parsed_logs_for_primitive:
                uncurated_data[primitive.primitive_id] = parsed_logs_for_primitive

        if not uncurated_data:
            self.console.print("[green]No uncurated primitives with parseable logs found.[/green]")
            return

        output_path = os.path.join(self.curating_logs_path, "uncurated_for_review.json")
        self.console.print(f"\nFound {len(uncurated_data)} primitives with uncurated logs.")
        self._save_json(output_path, uncurated_data)
        self.console.print(f"Dumped uncurated logs to [cyan]{output_path}[/cyan]")

    def _assemble_review_package(self):
        """Assembles and zips the practitioner review package."""
        self.console.print("\n--- [bold blue]Assembling Practitioner Review Package[/bold blue] ---")
        
        review_primitive_ids = [
            'PS-001', 'PS-006', 'PS-008', 'PS-009', 'PS-014', 'PS-016', 'PS-017', 
            'PS-019', 'PS-022', 'PS-028', 'PS-034', 'PS-038', 'PS-040', 'PS-042', 
            'PS-044', 'PS-045', 'PS-047', 'PS-048', 'PS-049', 'PS-050'
        ]
        
        package_dir = "./practitioner_package"
        
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        os.makedirs(package_dir)

        instructions_path = os.path.join(package_dir, "INSTRUCTIONS.md")
        with open(instructions_path, 'w', encoding='utf-8') as f:
            f.write(self._get_practitioner_instructions())

        primitive_map = {p.primitive_id: p for p in self.primitives}

        for pid in review_primitive_ids:
            if pid not in primitive_map:
                self.console.print(f"[yellow]Warning: Primitive ID '{pid}' not found. Skipping.[/yellow]")
                continue

            primitive = primitive_map[pid]
            delta_log_path = os.path.join(self.deltas_path, f"{pid}.json")

            if not os.path.exists(delta_log_path):
                self.console.print(f"[yellow]Warning: Delta log for '{pid}' not found. Skipping.[/yellow]")
                continue

            primitive_dir = os.path.join(package_dir, pid)
            os.makedirs(primitive_dir)

            with open(os.path.join(primitive_dir, "command.txt"), 'w', encoding='utf-8') as f:
                f.write(primitive.primitive_command)

            with open(os.path.join(primitive_dir, "context.txt"), 'w', encoding='utf-8') as f:
                f.write("INTENT:\n")
                for intent in primitive.intent:
                    f.write(f"- {intent.value}\n")
                f.write("\nMITRE TTPs:\n")
                for ttp in primitive.mitre_ttps:
                    f.write(f"- {ttp.value}\n")

            delta_logs = self._load_and_validate(delta_log_path, SplunkLogEvent, default=[])
            with open(os.path.join(primitive_dir, "delta_logs.json"), 'w', encoding='utf-8') as f:
                json.dump([log.model_dump(mode='json', by_alias=True) for log in delta_logs], f, indent=2)

        zip_filename = "practitioner_package"
        shutil.make_archive(zip_filename, 'zip', package_dir)
        
        shutil.rmtree(package_dir)
        
        self.console.print(f"\n[bold green]Success![/bold green] Package created at [cyan]{zip_filename}.zip[/cyan]")

    def _get_practitioner_instructions(self) -> str:
        """Returns the full, formatted markdown text for the practitioner instructions."""
        return """# PowerShell-Sentinel: Practitioner Review Package

Thank you for your time and expertise in helping to validate this research project.

**Project Goal:** The goal is to create a high-quality dataset for fine-tuning a Large Language Model to analyze obfuscated PowerShell commands. Your feedback is crucial for validating the quality of our data curation process.

This package contains several folders, each named with a unique `primitive_id` (e.g., `PS-007`). Inside each folder, you will find:
-   `command.txt`: The clean, deobfuscated PowerShell command that was executed.
-   `context.txt`: The `intent` and `MITRE ATT&CK TTPs` we have assigned to this command.
-   `delta_logs.json`: A file containing ALL the raw log events that were generated *only* when this command was run in a clean lab. This is noisy data.

---

### Your Tasks

You have two main tasks.

#### Task 1: Identify "Golden Signals" (for each folder)

Your primary task is to act as an expert analyst and identify the most important log events from the noisy `delta_logs.json`.

**For each folder (e.g., `PS-007`, `PS-011`, etc.):**

1.  Review the `command.txt` and `context.txt` to understand what the command does.
2.  Open the noisy `delta_logs.json` file.
3.  From the list of log objects, identify the **2 to 5 "golden signals"**—the log events that you believe are the most critical and definitive evidence that this specific command was executed.
4.  Create a **new file** in that same folder named **`expert_golden_signals.json`**.
5.  **Copy and paste** the full JSON objects of the golden signals you selected into this new file. The result should be a valid JSON list `[ {log1}, {log2}, ... ]`.

#### Task 2: Review Metadata (one-time task)

This is a quick sanity check of our manual curation.

1.  As you go through the folders, if you disagree with any of the `intent` or `mitre_ttps` listed in a `context.txt` file, please make a note of it.
2.  Create a **single, top-level text file** named **`metadata_review.txt`**.
3.  In this file, list the `primitive_id` and any suggested changes. For example:
    ```text
    PS-008: Suggest adding TTP T1592.002 (Gather Victim Host Information). Intent seems correct.
    PS-015: Intent "Local Groups" is too vague, suggest "Permission Groups Discovery: Local Groups". TTP is correct.
    ```
    If you agree with everything, you can simply write "All metadata looks correct."

---

### Final Step

Once you have completed both tasks, please re-zip the entire `practitioner_package` directory (which will now contain your new files) and send it back.

Thank you again for your invaluable contribution.
"""

if __name__ == '__main__':
    manager = PrimitivesManager(
        primitives_path="data/source/primitives_library.json",
        parsing_rules_path="data/source/parsing_rules.json",
        deltas_path="data/interim/delta_logs",
        mitre_lib_path="data/source/mitre_ttp_library.json",
        parsing_logs_path="data/interim/parsing_logs",
        curating_logs_path="data/interim/curating_logs"
    )
    manager.start()
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
from typing import List, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from powershell_sentinel.models import Primitive, SplunkLogEvent, TelemetryRule, ParsingRule, ExtractionMethodEnum
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules import snapshot_differ, statistics_calculator, recommendation_engine, rule_formatter

class PrimitivesManager:
    """An interactive CLI for managing the primitives knowledge base and parsing rules."""

    def __init__(self, primitives_path: str, parsing_rules_path: str, deltas_path: str):
        self.primitives_path = primitives_path
        self.parsing_rules_path = parsing_rules_path
        self.deltas_path = deltas_path
        self.console = Console()
        self.lab = LabConnection()
        self.primitives: List[Primitive] = self._load_and_validate(self.primitives_path, Primitive)
        self.parsing_rules: List[ParsingRule] = self._load_and_validate(self.parsing_rules_path, ParsingRule, default=[])

    def _load_and_validate(self, path: str, model: Type[BaseModel], default: Optional[list] = None) -> List[BaseModel]:
        """Generic loader for our JSON data files, with Pydantic validation."""
        if not os.path.exists(path) and default is not None:
            self.console.print(f"[yellow]File not found at {path}. Initializing with default empty list.[/yellow]")
            return default
        
        self.console.print(f"Loading data from [cyan]{path}[/]...")
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            validated_data = [model.model_validate(item) for item in data]
            self.console.print(f"[green]Successfully loaded and validated {len(validated_data)} items.[/green]")
            return validated_data
        except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
            self.console.print(f"[bold red]Error loading or validating {path}: {e}[/bold red]")
            exit(1)

    def _save_json(self, path: str, data: List[BaseModel]):
        """Generic saver for our Pydantic model lists."""
        self.console.print(f"Saving data to [cyan]{path}[/]...")
        data_as_dict = [p.model_dump(mode='json') for p in data]
        try:
            with open(path, 'w') as f:
                json.dump(data_as_dict, f, indent=2)
            self.console.print("[green]Save successful.[/green]")
        except IOError as e:
            self.console.print(f"[bold red]Error saving file {path}: {e}[/bold red]")
    
    def _apply_parsing_rule(self, rule: ParsingRule, raw_text: str) -> Optional[str]:
        """Applies a single parsing rule to extract details from raw text."""
        if rule.extraction_method == ExtractionMethodEnum.REGEX:
            match = re.search(rule.detail_key_or_pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match and match.groups() else None
        elif rule.extraction_method == ExtractionMethodEnum.KEY_VALUE:
            pattern = re.escape(rule.detail_key_or_pattern) + r'=(.*?)(?:\s*\w+=|$)'
            match = re.search(pattern, raw_text, re.DOTALL)
            return match.group(1).strip() if match and match.groups() else None
        return None

    def _parse_log_with_rules(self, log: SplunkLogEvent) -> Optional[TelemetryRule]:
        """Attempts to parse a raw log using the user-defined parsing rules."""
        for rule in self.parsing_rules:
            if str(rule.event_id) in log.raw:
                if rule.source_match and rule.source_match != log.sourcetype:
                    continue
                details = self._apply_parsing_rule(rule, log.raw)
                if details:
                    return TelemetryRule(source=log.source, event_id=rule.event_id, details=details)
        return None

    def _prompt_for_new_parsing_rule(self, log: SplunkLogEvent) -> Optional[TelemetryRule]:
        """The interactive prompt for teaching the system to parse a new log type."""
        self.console.print("\n[bold yellow]-- New Log Type Encountered --[/bold yellow]")
        self.console.print("The system does not have a rule to parse this log:")
        self.console.print(log.raw)

        if not Confirm.ask("\nWould you like to define a new parsing rule now?", default=True):
            return None
        
        # --- Interactively gather details for the new rule ---
        rule_name = Prompt.ask("Enter a unique name for this rule (e.g., Sysmon-EID11-FileCreate)")
        event_id = int(Prompt.ask("What is the primary Event ID for this rule?"))
        method_str = Prompt.ask("What is the extraction method?", choices=["regex", "key_value"], default="key_value")
        extraction_method = ExtractionMethodEnum(method_str)
        detail_key_or_pattern = Prompt.ask("Enter the detail key or regex pattern to extract")
        
        # --- Create, append, and save the new rule ---
        new_rule = ParsingRule(
            rule_name=rule_name,
            event_id=event_id,
            extraction_method=extraction_method,
            detail_key_or_pattern=detail_key_or_pattern
        )
        self.parsing_rules.append(new_rule)
        self._save_json(self.parsing_rules_path, self.parsing_rules)
        self.console.print(f"[green]New parsing rule '{rule_name}' saved.[/green]")

        # --- Immediately use the new rule to parse the current log ---
        return self._parse_log_with_rules(log)

    def run_telemetry_curation(self):
        """Orchestrates the BATCH Telemetry Curation workflow with interactive parsing."""
        self.console.print("\n--- Starting BATCH Telemetry Curation ---", style="bold blue")
        
        # Phase 1: Parse all delta logs, prompting for new rules as needed.
        all_parsed_rules: Dict[str, List[TelemetryRule]] = {}
        for primitive in self.primitives:
            primitive_id = primitive.primitive_id
            delta_log_path = os.path.join(self.deltas_path, f"{primitive_id}.json")
            
            if not os.path.exists(delta_log_path):
                continue
            
            raw_logs = self._load_and_validate(delta_log_path, SplunkLogEvent)
            parsed_for_primitive = []
            for log in raw_logs:
                parsed_rule = self._parse_log_with_rules(log)
                if not parsed_rule:
                    parsed_rule = self._prompt_for_new_parsing_rule(log)
                
                if parsed_rule:
                    parsed_for_primitive.append(parsed_rule)
            all_parsed_rules[primitive_id] = parsed_for_primitive
        
        # Phase 2: Calculate fresh statistics.
        rarity = statistics_calculator.calculate_global_rarity(self.primitives)
        relevance = statistics_calculator.calculate_local_relevance(self.primitives)

        # Phase 3: Get recommendations and prompt user for final selection.
        for primitive in self.primitives:
            if primitive.primitive_id not in all_parsed_rules:
                continue

            self.console.print(f"\n--- Curating Primitive: [bold cyan]{primitive.primitive_id}[/bold cyan] ---")
            self.console.print(f"Command: [green]{primitive.primitive_command}[/green]")
            
            parsed_rules_for_primitive = all_parsed_rules[primitive.primitive_id]
            if not parsed_rules_for_primitive:
                continue

            recommendations = recommendation_engine.get_recommendations(
                parsed_rules=parsed_rules_for_primitive,
                global_rarity=rarity,
                local_relevance=relevance,
                primitive_ttps=primitive.mitre_ttps
            )

            if not recommendations:
                self.console.print("[yellow]No high-confidence recommendations found.[/yellow]")
                continue

            # --- Display recommendations in a formatted table ---
            table = Table(title="Recommended Telemetry Signals")
            table.add_column("#", style="dim")
            table.add_column("Event ID"); table.add_column("Source"); table.add_column("Details")
            for i, rule in enumerate(recommendations):
                table.add_row(str(i + 1), str(rule.event_id), rule.source, rule.details)
            self.console.print(table)
            
            # --- Prompt for final selection ---
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
            
            # --- Update the primitive with the final curated rules ---
            primitive.telemetry_rules = rule_formatter.format_rules(final_selection)
            self.console.print(f"Saved {len(final_selection)} rules for {primitive.primitive_id}.")

        # Phase 4: Persist all changes to the main library.
        self._save_json(self.primitives_path, self.primitives)
        self.console.print("\n--- BATCH Telemetry Curation Complete ---", style="bold blue")
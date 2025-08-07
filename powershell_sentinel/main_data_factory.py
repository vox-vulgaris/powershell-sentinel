# powershell_sentinel/main_data_factory.py

import json
import random
import argparse
import os
from datetime import datetime
from typing import List
from pydantic import ValidationError

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

from powershell_sentinel.models import Primitive, TrainingPair, LLMResponse, Analysis
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules.obfuscator import generate_layered_obfuscation

FAILURES_LOG_PATH = "data/generated/failures.log"
PROPHYLACTIC_RESET_INTERVAL = 250

def log_failure(primitive: Primitive, chain: List[str], broken_command: str, error_message: str):
    os.makedirs(os.path.dirname(FAILURES_LOG_PATH), exist_ok=True)
    failure_record = {
        "timestamp": datetime.now().isoformat(),
        "primitive_id": primitive.primitive_id,
        "primitive_command": primitive.primitive_command,
        "obfuscation_chain": chain,
        "broken_command": broken_command,
        "error_message": error_message.strip()
    }
    with open(FAILURES_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(failure_record) + "\n")

def generate_dataset(target_pair_count: int, primitives_path: str, output_path: str):
    console = Console()
    console.print("Initializing lab connection and persistent shell...")
    try:
        lab = LabConnection()
        console.print("Lab connection successful.")
    except Exception as e:
        console.print(f"[bold red]FATAL: Could not initialize lab connection. Exiting. Error: {e}[/bold red]")
        return
    
    try:
        with open(primitives_path, 'r', encoding='utf-8') as f:
            primitives_data = json.load(f)
        all_primitives = [Primitive.model_validate(p) for p in primitives_data]
        usable_primitives = [p for p in all_primitives if p.telemetry_rules]
        console.print(f"Successfully loaded and validated {len(all_primitives)} primitives.")
        console.print(f"Found {len(usable_primitives)} primitives with curated telemetry suitable for generation.")
        if not usable_primitives:
            console.print("[bold red]Error: No usable primitives with telemetry rules found.[/bold red]")
            return
    except (FileNotFoundError, ValidationError, json.JSONDecodeError) as e:
        console.print(f"[bold red]Error loading or validating primitives: {e}[/bold red]")
        return

    generated_pairs: List[TrainingPair] = []
    if os.path.exists(output_path):
        console.print(f"[bold blue]Found existing dataset at {output_path}. Resuming...[/bold blue]")
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            generated_pairs = [TrainingPair.model_validate(p) for p in existing_data]
            console.print(f"[bold green]Loaded and validated {len(generated_pairs)} existing pairs.[/bold green]")
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            console.print(f"[bold yellow]Warning: Could not load existing dataset. Starting fresh. Error: {e}[/bold yellow]")
            generated_pairs = []

    if len(generated_pairs) >= target_pair_count:
        console.print(f"[bold green]Target of {target_pair_count} pairs already met. Exiting.[/bold green]")
        lab.close()
        return
        
    total_failures = 0
    progress_columns = [
        TextColumn("[progress.description]{task.description}"), BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed} of {task.total})"), TimeRemainingColumn(),
        TextColumn("[green]Success: {task.fields[successes]}[/green]"),
        TextColumn("[red]Fail: {task.fields[failures]}[/red]")
    ]
    
    try:
        with Progress(*progress_columns, console=console) as progress:
            initial_completed = len(generated_pairs)
            task = progress.add_task("[cyan]Generating data...", total=target_pair_count, completed=initial_completed, successes=initial_completed, failures=0)
            primitive_index = 0
            consecutive_failures = 0
            MAX_CONSECUTIVE_FAILURES_PER_PRIMITIVE = 20
            commands_since_last_reset = 0

            while len(generated_pairs) < target_pair_count:
                if commands_since_last_reset >= PROPHYLACTIC_RESET_INTERVAL:
                    progress.console.print(f"\n[bold magenta]-- Prophylactic Maintenance: Resetting shell... --[/bold magenta]")
                    lab.reset_shell()
                    commands_since_last_reset = 0

                current_primitive = usable_primitives[primitive_index]
                obfuscated_cmd, chain = generate_layered_obfuscation(current_primitive.primitive_command)
                
                execution_result = lab.run_remote_powershell(obfuscated_cmd)
                commands_since_last_reset += 1
                
                # [FIX] Check the return code directly. 0 is success.
                if execution_result.return_code == 0:
                    consecutive_failures = 0
                    try:
                        analysis_obj = Analysis(intent=current_primitive.intent, mitre_ttps=current_primitive.mitre_ttps, telemetry_signature=current_primitive.telemetry_rules)
                        response_obj = LLMResponse(deobfuscated_command=current_primitive.primitive_command, analysis=analysis_obj)
                        pair_obj = TrainingPair(prompt=obfuscated_cmd, response=response_obj)
                        generated_pairs.append(pair_obj)
                        progress.update(task, advance=1, successes=len(generated_pairs))
                        
                        if len(generated_pairs) % 100 == 0:
                            console.print(f"\n[bold blue]Checkpoint: Saving {len(generated_pairs)} pairs...[/bold blue]")
                            temp_output_data = [pair.model_dump(mode='json') for pair in generated_pairs]
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(temp_output_data, f, indent=2)
                        
                        primitive_index = (primitive_index + 1) % len(usable_primitives)
                    except ValidationError as e:
                        log_failure(current_primitive, chain, obfuscated_cmd, f"Pydantic validation failed: {e}")
                        total_failures += 1
                        progress.update(task, failures=total_failures)
                else:
                    log_failure(current_primitive, chain, obfuscated_cmd, execution_result.stderr)
                    total_failures += 1
                    consecutive_failures += 1
                    progress.update(task, failures=total_failures)

                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES_PER_PRIMITIVE:
                        progress.console.print(f"[bold yellow]Warning: Skipped primitive {current_primitive.primitive_id} after {consecutive_failures} failures.[/bold yellow]")
                        primitive_index = (primitive_index + 1) % len(usable_primitives)
                        consecutive_failures = 0
    finally:
        lab.close()

    console.print(f"\nGeneration complete. Saving final {len(generated_pairs)} pairs...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_data = [pair.model_dump(mode='json') for pair in generated_pairs]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    console.print(f"[green]Save successful.[/green] Total failures logged: {total_failures}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate obfuscated PowerShell training data.")
    parser.add_argument("--count", type=int, required=True, help="The target number of pairs to generate.")
    parser.add_argument("--primitives", default="data/source/primitives_library.json", help="Path to the primitives library.")
    parser.add_argument("--output", default="data/generated/training_data_v0.json", help="Path to save the generated dataset.")
    args = parser.parse_args()
    generate_dataset(args.count, args.primitives, args.output)
# powershell_sentinel/main_data_factory.py

import json
import random
import argparse
import os
from datetime import datetime
from typing import List
from pydantic import ValidationError

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from powershell_sentinel.models import Primitive, TrainingPair, LLMResponse, Analysis
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules.obfuscator import generate_layered_obfuscation

FAILURES_LOG_PATH = "data/generated/failures.log"

# (log_failure function remains the same)
def log_failure(primitive: Primitive, chain: List[str], broken_command: str, error_message: str):
    """Appends a structured failure record to the failures log."""
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
    """Main function to generate the training dataset."""
    print("Initializing lab connection and persistent shell...")
    lab = LabConnection() # [FIX] Lab is initialized once here
    print("Lab connection successful.")
    
    try:
        with open(primitives_path, 'r', encoding='utf-8') as f:
            primitives_data = json.load(f)
        all_primitives = [Primitive.model_validate(p) for p in primitives_data]
        usable_primitives = [p for p in all_primitives if p.telemetry_rules]
        
        print(f"Successfully loaded and validated {len(all_primitives)} primitives.")
        print(f"Found {len(usable_primitives)} primitives with curated telemetry suitable for generation.")
        
        if not usable_primitives:
            print("[bold red]Error: No usable primitives with telemetry rules found. Cannot generate data.[/bold red]")
            return
            
    except (FileNotFoundError, ValidationError, json.JSONDecodeError) as e:
        print(f"[bold red]Error loading or validating primitives: {e}[/bold red]")
        return

    generated_pairs: List[TrainingPair] = []
    total_failures = 0
    
    progress_columns = [
        TextColumn("[progress.description]{task.description}"), BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed} of {task.total})"), TimeRemainingColumn(),
        TextColumn("[green]Success: {task.fields[successes]}[/green]"),
        TextColumn("[red]Fail: {task.fields[failures]}[/red]")
    ]
    
    # [REFACTOR] Use a try...finally block to ensure lab.close() is always called
    try:
        with Progress(*progress_columns) as progress:
            task = progress.add_task("[cyan]Generating data...", total=target_pair_count, successes=0, failures=0)

            primitive_index = 0
            consecutive_failures = 0
            MAX_CONSECUTIVE_FAILURES_PER_PRIMITIVE = 20

            while len(generated_pairs) < target_pair_count:
                current_primitive = usable_primitives[primitive_index]
                
                obfuscated_cmd, chain = generate_layered_obfuscation(current_primitive.primitive_command)
                
                # If the shell died for some reason, we must stop.
                if not lab.shell_id:
                    progress.console.print("[bold red]FATAL: The persistent WinRM shell has died. Aborting generation.[/bold red]")
                    break

                execution_result = lab.run_remote_powershell(obfuscated_cmd)
                
                if execution_result.return_code == 0:
                    consecutive_failures = 0
                    try:
                        analysis_obj = Analysis(
                            intent=current_primitive.intent,
                            mitre_ttps=current_primitive.mitre_ttps,
                            telemetry_signature=current_primitive.telemetry_rules
                        )
                        response_obj = LLMResponse(
                            deobfuscated_command=current_primitive.primitive_command,
                            analysis=analysis_obj
                        )
                        pair_obj = TrainingPair(prompt=obfuscated_cmd, response=response_obj)
                        generated_pairs.append(pair_obj)
                        progress.update(task, advance=1, successes=len(generated_pairs))
                        
                        primitive_index = (primitive_index + 1) % len(usable_primitives)

                    except ValidationError as e:
                        error_msg = f"Pydantic validation failed for {current_primitive.primitive_id}. Error: {e}"
                        log_failure(current_primitive, chain, obfuscated_cmd, error_msg)
                        total_failures += 1
                        progress.update(task, advance=0, failures=total_failures)
                else:
                    log_failure(current_primitive, chain, obfuscated_cmd, execution_result.stderr)
                    total_failures += 1
                    consecutive_failures += 1
                    progress.update(task, advance=0, failures=total_failures)

                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES_PER_PRIMITIVE:
                        progress.console.print(f"[bold yellow]Warning: Skipped primitive {current_primitive.primitive_id} after {consecutive_failures} consecutive failures.[/bold yellow]")
                        primitive_index = (primitive_index + 1) % len(usable_primitives)
                        consecutive_failures = 0
    finally:
        # [DEFINITIVE FIX] This will run no matter what, ensuring the connection is closed.
        lab.close()

    # --- Final Serialization ---
    print(f"\nGeneration complete. Saving {len(generated_pairs)} pairs to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_data = [pair.model_dump(mode='json') for pair in generated_pairs]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    print(f"[green]Save successful.[/green] Total failures logged: {total_failures}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate obfuscated PowerShell training data.")
    parser.add_argument("--count", type=int, required=True, help="The target number of pairs to generate.")
    parser.add_argument("--primitives", default="data/source/primitives_library.json", help="Path to the primitives library.")
    parser.add_argument("--output", default="data/generated/training_data_v0.json", help="Path to save the generated dataset.")
    args = parser.parse_args()

    generate_dataset(args.count, args.primitives, args.output)
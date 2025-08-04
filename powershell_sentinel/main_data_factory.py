# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [11]
#
# This script is the master controller for the entire data generation pipeline.
# It brings together the curated primitives library, the obfuscation engine, and the
# lab connector to produce the final, large-scale, and VALIDATED training dataset.
#
# REQUIREMENTS (Pydantic-aware):
# 1. User Input: Must allow the user to specify a `target_pair_count`.
# 2. Data Loading: Must load and validate the `primitives_library.json` into a list of `Primitive` models.
# 3. Main Loop: Must loop until the target number of `TrainingPair` models is generated.
#    - In each iteration, it should randomly select a `Primitive` object.
# 4. Obfuscation: It must call `obfuscator.generate_layered_obfuscation`.
# 5. Two-Stage QA (Execution Validation):
#    - It must use `lab_connector.run_remote_powershell` to execute the *obfuscated* command.
#    - It must check if the execution was successful (`return_code == 0`).
#    - If execution fails, it must log the failure details to `failures.log` and discard the pair.
# 6. Output Validation: For each successful pair, it must construct a `TrainingPair` Pydantic model.
#    This serves as a final validation step ensuring the output data conforms to our schema.
# 7. Serialization: The final list of `TrainingPair` models must be serialized to a JSON file.

import json
import random
import argparse
from datetime import datetime
from typing import List
from pydantic import ValidationError

from rich.progress import Progress

from powershell_sentinel.models import Primitive, TrainingPair, LLMResponse, Analysis
from powershell_sentinel.lab_connector import LabConnection
from powershell_sentinel.modules.obfuscator import generate_layered_obfuscation

FAILURES_LOG_PATH = "data/generated/failures.log"

def log_failure(primitive: Primitive, chain: List[str], broken_command: str, error_message: str):
    """Appends a structured failure record to the failures log."""
    failure_record = {
        "timestamp": datetime.now().isoformat(),
        "primitive_id": primitive.primitive_id,
        "primitive_command": primitive.primitive_command,
        "obfuscation_chain": chain,
        "broken_command": broken_command,
        "error_message": error_message.strip()
    }
    with open(FAILURES_LOG_PATH, 'a') as f:
        f.write(json.dumps(failure_record) + "\n")

def generate_dataset(target_pair_count: int, primitives_path: str, output_path: str):
    """Main function to generate the training dataset."""
    # 1. Initialize lab connection and load/validate primitives
    lab = LabConnection()
    try:
        with open(primitives_path, 'r') as f:
            primitives_data = json.load(f)
        primitives = [Primitive.model_validate(p) for p in primitives_data]
        print(f"Successfully loaded and validated {len(primitives)} primitives.")
    except (FileNotFoundError, ValidationError, json.JSONDecodeError) as e:
        print(f"Error loading primitives: {e}")
        return

    generated_pairs: List[TrainingPair] = []
    
    # Use rich.progress for a nice progress bar
    with Progress() as progress:
        task = progress.add_task("[cyan]Generating data...", total=target_pair_count)

        # 2. Main generation loop
        while len(generated_pairs) < target_pair_count:
            # a. Select a random primitive
            current_primitive = random.choice(primitives)
            
            # b. Obfuscate the command
            obfuscated_cmd, chain = generate_layered_obfuscation(current_primitive.primitive_command)
            
            # c. Execute the obfuscated command
            execution_result = lab.run_remote_powershell(obfuscated_cmd)
            
            # d. Two-Stage QA: Check for execution success
            if execution_result.return_code != 0:
                log_failure(current_primitive, chain, obfuscated_cmd, execution_result.stderr)
                progress.console.print(f"[yellow]WARN: Execution failed for primitive {current_primitive.primitive_id}. See failures.log.[/yellow]")
                continue # Skip to the next iteration

            # e. Construct the final, validated TrainingPair model
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
                pair_obj = TrainingPair(
                    prompt=obfuscated_cmd,
                    response=response_obj
                )
                generated_pairs.append(pair_obj)
                progress.update(task, advance=1)
            except ValidationError as e:
                progress.console.print(f"[bold red]FATAL: Pydantic validation failed while creating TrainingPair for {current_primitive.primitive_id}. This should not happen. Error: {e}[/bold red]")
                # This indicates a bug in our own code, so we should be loud about it.
                continue

    # 5. Serialize the final list of Pydantic models and save to disk
    print(f"\nGeneration complete. Saving {len(generated_pairs)} pairs to {output_path}...")
    
    output_data = [pair.model_dump(mode='json') for pair in generated_pairs]
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
        
    print("Save successful.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate obfuscated PowerShell training data.")
    parser.add_argument("--count", type=int, required=True, help="The target number of pairs to generate.")
    parser.add_argument("--primitives", default="data/source/primitives_library.json", help="Path to the primitives library.")
    parser.add_argument("--output", default="data/generated/training_data_v0.json", help="Path to save the generated dataset.")
    args = parser.parse_args()

    generate_dataset(args.count, args.primitives, args.output)
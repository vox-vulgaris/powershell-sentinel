# scripts/migrate_dataset_to_flat.py

import json
import argparse
from typing import List
from pydantic import BaseModel, Field
from rich.console import Console
from tqdm import tqdm

# To make this script a robust, standalone utility, we will define the necessary
# old and new Pydantic models directly within it. This prevents any dependency
# on the current (and future) state of the main models.py file.

# --- Data Structures Definition ---

# These classes represent the OLD, NESTED structure.
class TelemetryRule(BaseModel):
    source: str
    event_id: int
    details: str

class NestedAnalysis(BaseModel):
    intent: List[str]
    mitre_ttps: List[str]
    telemetry_signature: List[TelemetryRule]

class NestedLLMResponse(BaseModel):
    deobfuscated_command: str
    analysis: NestedAnalysis

class OldTrainingPair(BaseModel):
    prompt: str
    response: NestedLLMResponse

# These classes represent the NEW, FLATTENED structure.
class FlattenedLLMResponse(BaseModel):
    deobfuscated_command: str
    intent: List[str]
    mitre_ttps: List[str]
    telemetry_signature: List[TelemetryRule]

class NewTrainingPair(BaseModel):
    prompt: str
    response: FlattenedLLMResponse


def migrate_dataset(input_path: str, output_path: str):
    """
    Loads a dataset with a nested response structure, converts it to a
    flattened structure, and saves it to a new file.
    """
    console = Console()
    console.print(f"\n[bold blue]Starting dataset migration...[/bold blue]")
    console.print(f"[cyan]Input file:[/cyan] {input_path}")
    console.print(f"[cyan]Output file:[/cyan] {output_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            nested_data = json.load(f)
        console.print(f"Loaded [magenta]{len(nested_data)}[/magenta] records from input file.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]FATAL: Could not read or parse input file: {e}[/bold red]")
        return

    flattened_data = []
    
    console.print("Processing and migrating records...")
    for item in tqdm(nested_data, desc="Migrating"):
        try:
            # 1. Validate the record against the old, nested structure
            old_pair = OldTrainingPair.model_validate(item)

            # 2. Extract data from the nested structure
            nested_response = old_pair.response
            nested_analysis = nested_response.analysis

            # 3. Build the new, flattened response object
            flattened_response = FlattenedLLMResponse(
                deobfuscated_command=nested_response.deobfuscated_command,
                intent=nested_analysis.intent,
                mitre_ttps=nested_analysis.mitre_ttps,
                telemetry_signature=nested_analysis.telemetry_signature
            )

            # 4. Create the final, new training pair
            new_pair = NewTrainingPair(
                prompt=old_pair.prompt,
                response=flattened_response
            )

            # Add the Pydantic model to the list for JSON serialization
            flattened_data.append(new_pair.model_dump())

        except Exception as e:
            console.print(f"[bold yellow]WARNING: Skipping a record due to validation/migration error: {e}[/bold yellow]")
            continue

    console.print(f"Successfully migrated [magenta]{len(flattened_data)}[/magenta] records.")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(flattened_data, f, indent=2)
        console.print(f"[bold green]Migration complete! Flattened dataset saved successfully.[/bold green]")
    except IOError as e:
        console.print(f"[bold red]FATAL: Could not write to output file: {e}[/bold red]")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Migrate a PowerShell-Sentinel dataset from a nested to a flattened JSON structure.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_path",
        help="Path to the source JSON file with the nested structure (e.g., training_data_v0_clean.json)."
    )
    parser.add_argument(
        "output_path",
        help="Path to save the destination JSON file with the new flattened structure (e.g., training_data_v0_flat.json)."
    )

    args = parser.parse_args()
    migrate_dataset(args.input_path, args.output_path)
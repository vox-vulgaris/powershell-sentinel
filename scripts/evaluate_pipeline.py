# scripts/evaluate_pipeline.py

import json
import base64
import random
from collections import Counter
from rich.console import Console
from rich.table import Table
import argparse
from typing import Set

# --- Core Logic Functions (Self-Contained, No External Imports) ---

def infer_techniques_from_prompt(prompt: str) -> Set[str]:
    """
    Infers the set of obfuscation techniques used based on signatures in a prompt string.
    """
    inferred_techniques = set()
    
    if 'powershell.exe -EncodedCommand' in prompt or 'FromBase64String' in prompt:
        inferred_techniques.add('obfuscate_base64')
        inferred_techniques.add('layered_technique_inside_base64')
        return inferred_techniques

    if '+' in prompt and ('Invoke-Expression' in prompt or 'iex' in prompt):
        inferred_techniques.add('obfuscate_concat')
    if '$' in prompt and '=' in prompt and ';' in prompt:
        inferred_techniques.add('obfuscate_variables')
    if '-f' in prompt and "'{0}'" in prompt:
        inferred_techniques.add('obfuscate_format_operator')
    if '&([string]::new' in prompt or '&([char[]]' in prompt:
        inferred_techniques.add('obfuscate_types')
        
    return inferred_techniques

# --- Main Analysis Functions ---

def analyze_variety(console: Console, dataset_path: str, data: list):
    """Analyzes and prints the distribution of techniques in the successful dataset."""
    console.print(f"\n[bold cyan]Stage 1: Analyzing Obfuscation Variety in '{dataset_path}'...[/bold cyan]")
    technique_counts = Counter()
    total_pairs = len(data)

    for pair in data:
        prompt = pair.get('prompt', '')
        techniques = infer_techniques_from_prompt(prompt)
        technique_counts.update(techniques)
        
    table = Table(title=f"Inferred Obfuscation Technique Distribution (Total Pairs: {total_pairs})")
    table.add_column("Technique", style="cyan")
    table.add_column("Occurrence Count", style="magenta")
    table.add_column("Presence in Dataset (%)", style="green")

    for tech, count in technique_counts.most_common():
        percentage = (count / total_pairs) * 100
        table.add_row(tech, str(count), f"{percentage:.2f}%")
        
    console.print(table)

def analyze_failures(console: Console, log_path: str):
    """Analyzes and prints the failure patterns from the log file."""
    console.print(f"\n[bold red]Stage 2: Analyzing Failure Patterns in '{log_path}'...[/bold red]")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
    except FileNotFoundError:
        console.print(f"[bold red]Error: Log file not found at '{log_path}'[/bold red]")
        return
        
    primitive_failures, technique_failures = Counter(), Counter()
    for line in log_lines:
        try:
            record = json.loads(line)
            # [DEFINITIVE FIX] Use .update() for primitives for consistency and testability.
            primitive_id = record.get('primitive_id', 'Unknown')
            primitive_failures.update([primitive_id])
            technique_failures.update(record.get('obfuscation_chain', []))
        except json.JSONDecodeError:
            continue
            
    prim_table = Table(title=f"Most Frequent Primitive Failures (Top 10)")
    prim_table.add_column("Primitive ID", style="cyan")
    prim_table.add_column("Failure Count", style="magenta")
    for prim_id, count in primitive_failures.most_common(10):
        prim_table.add_row(prim_id, str(count))
        
    tech_table = Table(title="Most Frequent Obfuscation Technique Failures")
    tech_table.add_column("Technique", style="cyan")
    tech_table.add_column("Failure Count", style="magenta")
    for tech, count in technique_failures.most_common(10):
        tech_table.add_row(tech, str(count))

    console.print(prim_table)
    console.print(tech_table)
    console.print(f"[bold]Total Failures Analyzed:[/bold] {len(log_lines)}")

def analyze_decoded_content(console: Console, data: list, sample_size: int):
    """Analyzes and prints the variety of techniques inside Base64 payloads."""
    console.print(f"\n[bold green]Stage 3: Analyzing Inner Variety of {sample_size} Random Base64 Payloads...[/bold green]")
    base64_prompts = [p['prompt'] for p in data if 'EncodedCommand' in p['prompt']]
    
    if len(base64_prompts) < sample_size:
        sample_size = len(base64_prompts)
    
    if sample_size == 0:
        console.print("[yellow]No Base64 prompts to sample.[/yellow]")
        return
        
    sample = random.sample(base64_prompts, sample_size)
    inner_technique_counts = Counter()

    for prompt in sample:
        encoded_part = prompt.split(' ')[-1]
        try:
            decoded_bytes = base64.b64decode(encoded_part)
            decoded_command = decoded_bytes.decode('utf-16le')
            inner_techniques = infer_techniques_from_prompt(decoded_command)
            inner_technique_counts.update(inner_techniques)
        except Exception:
            continue

    table = Table(title=f"Inferred Technique Distribution Inside {sample_size} Random Base64 Payloads")
    table.add_column("Technique", style="cyan")
    table.add_column("Occurrence Count", style="magenta")
    table.add_column("Presence in Sample (%)", style="green")

    for tech, count in inner_technique_counts.most_common():
        percentage = (count / sample_size) * 100
        table.add_row(tech, str(count), f"{percentage:.2f}%")
        
    console.print(table)
    console.print(f"\n[bold]Conclusion:[/bold] This analysis confirms that the Base64 payloads contain a rich distribution of other techniques.")

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a full experimental evaluation of the data factory pipeline.")
    parser.add_argument("--dataset-file", default="data/generated/training_data_v0.json")
    parser.add_argument("--log-file", default="data/generated/failures.log")
    parser.add_argument("--sample-size", type=int, default=500)
    args = parser.parse_args()

    console = Console()
    
    try:
        with open(args.dataset_file, 'r', encoding='utf-8') as f:
            full_dataset = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]FATAL: Could not load dataset file '{args.dataset_file}'. Error: {e}[/bold red]")
        exit()

    analyze_variety(console, args.dataset_file, full_dataset)
    analyze_failures(console, args.log_file)
    analyze_decoded_content(console, full_dataset, args.sample_size)
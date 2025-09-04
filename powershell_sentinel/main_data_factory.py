import json
import argparse
import os
import subprocess
import itertools
from datetime import datetime
from typing import List, Tuple, Set, Dict, Any

from pydantic import ValidationError
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

from powershell_sentinel.models import Primitive, TrainingPair, LLMResponse, Analysis, CommandOutput
from powershell_sentinel.lab_connector import LabConnection

# --- V2 CONFIGURATION ---
# Default file paths
DEFAULT_PRIMITIVES_PATH = "data/source/primitives_library.json"
OUTPUT_FILE = "data/generated/training_data_v2.json"
COMPLETION_LOG_FILE = "data/generated/completion_log.json"
AUDIT_LOG_FILE = "data/generated/audit_log.jsonl"

# Engine configuration
MODULES_DIR = os.path.dirname(os.path.realpath(__file__))
OBFUSCATION_MODULE_PATH = os.path.join(MODULES_DIR, "modules/PowerShellSentinelObfuscator.psm1")

# Hardening and Stability
PROPHYLACTIC_RESET_INTERVAL = 250

# Logic Configuration
EXCLUSION_LIST = {
    'PS-051': {'Invoke-SentinelCommand'}, 'PS-054': {'Invoke-SentinelCommand'},
    'PS-055': {'Invoke-SentinelCommand'}, 'PS-057': {'Invoke-SentinelCommand'},
    'PS-058': {'Invoke-SentinelCommand'},
}

# --- V2 HELPER FUNCTIONS ---

def generate_all_recipes() -> List[List[str]]:
    recipes = []
    wrappers = ['Invoke-SentinelType', 'Invoke-SentinelFormat']
    l1_wrappers = [[]]
    for length in range(1, 5):
        for p in itertools.product(wrappers, repeat=length):
            if p.count('Invoke-SentinelType') <= 2 and p.count('Invoke-SentinelFormat') <= 2:
                l1_wrappers.append(list(p))
    l2_concat = [[], ['Invoke-SentinelConcat'], ['Invoke-SentinelConcat']*2, ['Invoke-SentinelConcat']*3]
    argument_recipes = [l1 + l2 for l1 in l1_wrappers for l2 in l2_concat]
    finishers = [[], ['Invoke-SentinelCommand'], ['Invoke-SentinelBase64']]
    for arg_recipe in argument_recipes:
        for finisher in finishers:
            if 'Invoke-SentinelCommand' in finisher and 'Invoke-SentinelBase64' in finisher:
                continue
            recipes.append(arg_recipe + finisher)
    return recipes

def load_state(output_path: str, completion_log_path: str) -> Tuple[List[TrainingPair], Set[Tuple[str, Tuple[str, ...]]]]:
    console = Console()
    generated_pairs = []
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                loaded_json = json.load(f)
            generated_pairs = [TrainingPair.model_validate(p) for p in loaded_json]
        except (json.JSONDecodeError, ValidationError) as e:
            console.print(f"[bold yellow]Warning: Could not load dataset at {output_path}. Starting fresh. Error: {e}[/bold yellow]")
    completed_jobs = set()
    if os.path.exists(completion_log_path):
        try:
            with open(completion_log_path, 'r', encoding='utf-8') as f:
                # --- THIS IS THE FIX ---
                # Explicitly convert the inner list (the recipe) to a tuple
                completed_jobs = {(job[0], tuple(job[1])) for job in json.load(f)}
        except (json.JSONDecodeError):
             console.print(f"[bold yellow]Warning: Could not load completion log at {completion_log_path}. Starting fresh.[/bold yellow]")
    console.print(f"Resuming. Found {len(generated_pairs)} existing pairs and {len(completed_jobs)} completed jobs.")
    return generated_pairs, completed_jobs

def save_state(generated_pairs: List[TrainingPair], completed_jobs: Set, output_path: str, completion_log_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([p.model_dump(mode='json') for p in generated_pairs], f, indent=2)
    with open(completion_log_path, 'w', encoding='utf-8') as f:
        json.dump([list(job) for job in completed_jobs], f, indent=2)

def log_audit_event(primitive_id: str, recipe: List[str], status: str, details: str = "", audit_log_path: str = AUDIT_LOG_FILE):
    log_entry = {"timestamp": datetime.now().isoformat(), "primitive_id": primitive_id, "recipe": recipe, "status": status, "details": details.strip()}
    with open(audit_log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + "\n")

def invoke_sentinel_engine(command: str, technique: str) -> Tuple[bool, str]:
    try:
        # Use a list of arguments for better handling of paths and commands with spaces
        ps_args = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-Command", f"Import-Module -Name '{OBFUSCATION_MODULE_PATH}'; {technique} -Command \"{command.replace('"', '`"')}\""
        ]
        result = subprocess.run(ps_args, capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
        if result.returncode != 0:
            return False, f"ENGINE_ERROR: PowerShell process exited with code {result.returncode}. Stderr: {result.stderr}"
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "ENGINE_ERROR: PowerShell process timed out."
    except Exception as e:
        return False, f"ENGINE_ERROR: Unexpected Python error: {e}"

# --- V2 MAIN ORCHESTRATOR ---

def main(primitives_path: str, dry_run: bool):
    console = Console()
    
    # --- Load Primitives ---
    try:
        with open(primitives_path, 'r', encoding='utf-8') as f:
            all_primitives = [Primitive.model_validate(p) for p in json.load(f)]
        console.print(f"Successfully loaded and validated {len(all_primitives)} primitives.")
    except (FileNotFoundError, ValidationError, json.JSONDecodeError) as e:
        console.print(f"[bold red]FATAL: Error loading primitives: {e}[/bold red]"); return

    # --- Prepare Recipes and State ---
    generated_pairs, completed_jobs = load_state(OUTPUT_FILE, COMPLETION_LOG_FILE)
    all_recipes = generate_all_recipes()

    # --- DRY RUN LOGIC ---
    if dry_run:
        console.print("[bold yellow]--- DRY RUN MODE ACTIVATED ---[/bold yellow]")
        all_primitives = [p for p in all_primitives if p.primitive_id in ('PS-009', 'PS-051')]
        all_recipes = [[], ['Invoke-SentinelConcat'], ['Invoke-SentinelCommand'], ['Invoke-SentinelType', 'Invoke-SentinelBase64']]
        console.print(f"Dry run will use {len(all_primitives)} primitives and {len(all_recipes)} recipes.")

    total_jobs = len(all_primitives) * len(all_recipes)

    # --- Initialize Lab Connection ---
    console.print("Initializing lab connection...")
    try: lab = LabConnection(); console.print("Lab connection successful.")
    except Exception as e: console.print(f"[bold red]FATAL: Lab connection failed: {e}[/bold red]"); return

    # --- Main Generation Loop ---
    progress_columns = [TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("({task.completed} of {task.total})"), TimeRemainingColumn(), TextColumn("[green]Success: {task.fields[successes]}[/green]"), TextColumn("[red]Fail: {task.fields[failures]}[/red]")]
    jobs_processed_since_reset = 0

    try:
        with Progress(*progress_columns, console=console) as progress:
            task = progress.add_task("[cyan]Generating V2 dataset...", total=total_jobs, completed=len(completed_jobs), successes=len(generated_pairs), failures=(len(completed_jobs) - len(generated_pairs)))
            for primitive in all_primitives:
                for recipe in all_recipes:
                    if jobs_processed_since_reset >= PROPHYLACTIC_RESET_INTERVAL:
                        progress.console.print(f"\n[bold magenta]-- Prophylactic Maintenance: Resetting WinRM shell... --[/bold magenta]")
                        lab.reset_shell(); jobs_processed_since_reset = 0
                    
                    job_id = (primitive.primitive_id, tuple(recipe)); jobs_processed_since_reset += 1
                    if job_id in completed_jobs: continue
                    
                    is_excluded = any(technique in EXCLUSION_LIST.get(primitive.primitive_id, {}) for technique in recipe)
                    if is_excluded:
                        log_audit_event(primitive.primitive_id, recipe, "skipped_exclusion"); completed_jobs.add(job_id)
                        progress.update(task, advance=1, failures=progress.tasks[0].fields['failures'] + 1); continue

                    current_command = primitive.primitive_command; engine_succeeded = True
                    for technique in recipe:
                        success, result = invoke_sentinel_engine(current_command, technique)
                        if not success:
                            log_audit_event(primitive.primitive_id, recipe, "failure_engine", result); engine_succeeded = False; break
                        current_command = result
                    
                    if not engine_succeeded:
                        completed_jobs.add(job_id); progress.update(task, advance=1, failures=progress.tasks[0].fields['failures'] + 1); continue

                    obfuscated_cmd = current_command
                    execution_result = None # Initialize to None

                    # PRE-FLIGHT LENGTH CHECK (THE NEW, REFINED TWEAK)
                    if len(obfuscated_cmd) > 8000:
                        # SIMULATE a lab failure instead of skipping.
                        # We will create a fake "CommandOutput" object that mirrors the real error.
                        error_message = "WinRM Transport Error: Process exited with code 1. Stderr: The command line is too long."
                        execution_result = CommandOutput(
                            Stdout="",
                            Stderr=error_message,
                            ReturnCode=1 # Use the same non-zero return code
                        )
                    else:
                        # Lab Validation (Only runs if the command length is valid)
                        execution_result = lab.run_remote_powershell(obfuscated_cmd)
                    
                    # Process the result (either real or simulated)
                    status = "success" if execution_result.return_code == 0 else "failure_lab"
                    details = "" if status == "success" else execution_result.stderr
                    log_audit_event(primitive.primitive_id, recipe, status, details)

                    if status == "success":
                        try:
                            analysis_obj = Analysis(intent=primitive.intent, mitre_ttps=primitive.mitre_ttps, telemetry_signature=primitive.telemetry_rules)
                            response_obj = LLMResponse(deobfuscated_command=primitive.primitive_command, analysis=analysis_obj)
                            pair_obj = TrainingPair(prompt=obfuscated_cmd, response=response_obj)
                            generated_pairs.append(pair_obj); progress.update(task, successes=len(generated_pairs))
                        except ValidationError as e:
                            log_audit_event(primitive.primitive_id, recipe, "failure_validation", str(e)); status = "failure_validation"
                    
                    completed_jobs.add(job_id)
                    progress.update(task, advance=1, failures=progress.tasks[0].fields['failures'] + (1 if status != "success" else 0))

                    if len(completed_jobs) % 20 == 0: # Checkpoint more frequently
                        progress.console.print(f"\n[bold blue]Checkpoint: Saving progress...[/bold blue]")
                        save_state(generated_pairs, completed_jobs, OUTPUT_FILE, COMPLETION_LOG_FILE)
    finally:
        console.print("\nClosing lab connection..."); lab.close()
        console.print("Generation complete. Performing final save...")
        save_state(generated_pairs, completed_jobs, OUTPUT_FILE, COMPLETION_LOG_FILE)
        console.print(f"[green]Save successful.[/green] Total pairs: {len(generated_pairs)}. Total jobs processed: {len(completed_jobs)}.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate V2 of the obfuscated PowerShell training data.")
    parser.add_argument("--primitives", default=DEFAULT_PRIMITIVES_PATH, help="Path to the primitives library.")
    parser.add_argument("--dry-run", action="store_true", help="Run with a small subset of primitives and recipes for testing.")
    args = parser.parse_args()
    main(args.primitives, args.dry_run)
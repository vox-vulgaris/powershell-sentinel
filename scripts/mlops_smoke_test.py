# /scripts/mlops_pipeline_smoke_test.py
import json
import os
import subprocess
import argparse
from rich.console import Console

# ======================================================================================
# DISSERTATION CONTEXT & ANNOTATIONS
#
# This script serves as a full end-to-end "smoke test" for the entire MLOps
# pipeline, from training to evaluation. Its purpose is to provide a rapid,
# low-cost way to verify that the environment, dependencies, and core scripts
# are all functioning correctly before committing to a long-running, final
# training job.
#
# NARRATIVE PLACEMENT:
# This tool is a key part of the MLOps and Quality Assurance strategy discussed
# in Chapters 4 and 5. It represents a practical risk-mitigation technique
# used to ensure experimental integrity.
# ======================================================================================

def run_command(command: str, console: Console):
    """Executes a shell command and streams its output."""
    console.print(f"[bold yellow]$ {command}[/bold yellow]")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            console.print(output.strip())
            
    return process.poll()

def run_smoke_test(model_name: str, full_data_path: str):
    """Main function to orchestrate the smoke test."""
    console = Console()
    console.print("--- 🚀 Starting Full Pipeline Smoke Test ---", style="bold green")

    # --- Step 1: Create Smoke Test Data ---
    console.print("\n--- Step A: Creating Smoke Test Data ---", style="bold blue")
    smoke_train_path = "data/generated/smoke_test_train.json"
    smoke_val_path = "data/generated/smoke_test_val.json" # Storing in data/generated for consistency
    
    try:
        with open(full_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Ensure we don't try to slice more data than exists
        if len(data) < 6:
             console.print(f"[bold red]FATAL: Full dataset at '{full_data_path}' has fewer than 6 samples required for smoke test.[/bold red]")
             return

        with open(smoke_train_path, 'w') as f:
            json.dump(data[:3], f, indent=2)
        with open(smoke_val_path, 'w') as f:
            json.dump(data[3:6], f, indent=2)
        console.print(f"✅ Created smoke test files:\n- Train: [cyan]{smoke_train_path}[/cyan]\n- Eval:  [cyan]{smoke_val_path}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]FATAL: Failed to create smoke test data: {e}[/bold red]")
        return

    # --- Step 2: Run Smoke Test Training ---
    console.print("\n--- Step B: Running a 10-Step Smoke Test Training ---", style="bold blue")
    train_command = (
        f"python -m powershell_sentinel.train "
        f"--model_name {model_name} "
        f"--train_dataset {smoke_train_path} "
        f"--output_dir models/smoke_test_model "
        f"--test_dataset {smoke_val_path} " # Use smoke val for leakage check
        f"--learning_rate 2e-5 "
        f"--lora_rank 16 "
        f"--max_steps 10"
    )
    
    train_exit_code = run_command(train_command, console)
    if train_exit_code != 0:
        console.print("\n--- ❌ SMOKE TEST FAILED: Training script failed. ---", style="bold red")
        return

    # --- Step 3: Run Smoke Test Evaluation ---
    console.print("\n--- Step C: Running a 3-Sample Smoke Test Evaluation ---", style="bold blue")
    eval_command = (
        f"python -m powershell_sentinel.evaluate "
        f"--base_model_path {model_name} "
        f"--model_path models/smoke_test_model/final_checkpoint "
        f"--test_set_path {smoke_val_path}"
    )
    
    eval_exit_code = run_command(eval_command, console)
    if eval_exit_code != 0:
        console.print("\n--- ❌ SMOKE TEST FAILED: Evaluation script failed. ---", style="bold red")
        return

    # --- Step 4: Cleanup ---
    console.print("\n--- Step D: Cleaning up smoke test artifacts ---", style="bold blue")
    try:
        os.remove(smoke_train_path)
        os.remove(smoke_val_path)
        # Using shell command for recursive deletion for simplicity
        subprocess.run("rm -rf models/smoke_test_model", shell=True, check=True)
        console.print("✅ Cleanup complete.")
    except Exception as e:
        console.print(f"[bold yellow]Warning: Cleanup failed. You may need to manually remove smoke test files. Error: {e}[/bold yellow]")

    console.print("\n\n--- ✅ ✅ ✅ SMOKE TEST PASSED SUCCESSFULLY ---", style="bold green")
    console.print("The full training and evaluation pipeline is functioning correctly.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a full end-to-end smoke test of the MLOps pipeline.")
    parser.add_argument(
        "--model_name", 
        default="meta-llama/Meta-Llama-3-8B-Instruct", 
        help="The base model to use for the test."
    )
    parser.add_argument(
        "--full_data_path", 
        default="data/generated/training_data_v0_clean.json",
        help="Path to the full, clean dataset to sample from for the smoke test."
    )
    args = parser.parse_args()

    run_smoke_test(args.model_name, args.full_data_path)
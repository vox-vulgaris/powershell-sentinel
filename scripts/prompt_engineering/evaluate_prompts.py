# scripts/prompt_engineering/evaluate_prompts.py

import os
import json
import argparse
import torch
from pydantic import ValidationError
from tqdm import tqdm

from rich.console import Console
from rich.table import Table
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Import the core logic from our main evaluation script
from powershell_sentinel.evaluate import calculate_metrics
from powershell_sentinel.models import TrainingPair, LLMResponse
from powershell_sentinel.train import WINNING_PROMPT_TEMPLATE

def evaluate_single_model(model_dir: str, base_model_path: str, val_set: List[TrainingPair], console: Console) -> dict:
    """Runs evaluation for a single experimental model."""
    console.print(f"\n--- Evaluating model from [cyan]{model_dir}[/] ---")
    
    # Load model
    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(base_model_path, quantization_config=quant_config, device_map="auto")
    model = PeftModel.from_pretrained(base_model, model_dir)
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)

    predictions: List[LLMResponse] = []
    parse_failures = 0

    for truth_pair in tqdm(val_set, desc=f"Inference for {os.path.basename(model_dir)}"):
        prompt = WINNING_PROMPT_TEMPLATE.format(prompt=truth_pair.prompt) # This uses the "Detailed" format consistently
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.0)
        
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            json_part = response_text.split("### RESPONSE:")[1].strip()
            predicted_response = LLMResponse.model_validate_json(json_part)
            predictions.append(predicted_response)
        except (IndexError, ValidationError):
            parse_failures += 1
            
    # Clean up memory
    del model
    del base_model
    torch.cuda.empty_cache()

    return calculate_metrics(predictions, val_set, parse_failures)

def run_prompt_evaluation(exp_dir: str, base_model_path: str, val_path: str):
    console = Console()
    
    # Load the validation set once
    try:
        with open(val_path, 'r', encoding='utf-8') as f:
            val_data = json.load(f)
        validation_set = [TrainingPair.model_validate(item) for item in val_data]
        console.print(f"Loaded {len(validation_set)} validation samples from [cyan]{val_path}[/]")
    except (FileNotFoundError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load validation set: {e}[/bold red]")
        return
        
    model_dirs = [os.path.join(exp_dir, d) for d in os.listdir(exp_dir) if os.path.isdir(os.path.join(exp_dir, d))]
    results = []

    for model_dir in model_dirs:
        if "final_checkpoint" not in os.listdir(model_dir):
             console.print(f"[yellow]Skipping {model_dir} as it doesn't contain a 'final_checkpoint'.[/yellow]")
             continue
        
        final_model_path = os.path.join(model_dir, "final_checkpoint")
        report = evaluate_single_model(final_model_path, base_model_path, validation_set, console)
        report['model_name'] = os.path.basename(model_dir)
        results.append(report)
        
    # Print comparison table
    table = Table(title="Prompt Engineering Experiment Results")
    table.add_column("Model Name", style="cyan")
    table.add_column("Parse Success Rate", style="magenta")
    table.add_column("Intent F1 (Macro)", style="green")

    # Sort by parse success rate, then F1 score
    results.sort(key=lambda x: (x['JSON Parse Success Rate'], x['Intent F1-Score (Macro)']), reverse=True)
    
    for res in results:
        table.add_row(
            res['model_name'],
            f"{res['JSON Parse Success Rate']:.2%}",
            f"{res['Intent F1-Score (Macro)']:.2%}"
        )
        
    console.print(table)
    if results:
        console.print(f"\n[bold green]WINNER: {results[0]['model_name']} is the most effective template.[/bold green]")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate prompt engineering models.")
    parser.add_argument("--exp_dir", type=str, default="models/prompt_experiments", help="Directory containing the experimental models.")
    parser.add_argument("--base_model_path", type=str, default="google/gemma-3n-e4b", help="Path to the base model.")
    parser.add_argument("--val_path", type=str, default="scripts/prompt_engineering/mini_val.json", help="Path to the mini validation set.")
    args = parser.parse_args()
    
    run_prompt_evaluation(args.exp_dir, args.base_model_path, args.val_path)
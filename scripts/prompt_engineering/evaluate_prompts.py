# scripts/prompt_engineering/evaluate_prompts.py
import os
import json
import argparse
import torch
from pydantic import ValidationError
from tqdm import tqdm
from typing import List

from rich.console import Console
from rich.table import Table
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from powershell_sentinel.evaluate import calculate_metrics
from powershell_sentinel.models import TrainingPair, LLMResponse
from powershell_sentinel.train import WINNING_PROMPT_TEMPLATE

def evaluate_single_model(model_dir: str, base_model_path: str, val_set: List[TrainingPair], console: Console) -> dict:
    console.print(f"\n--- Evaluating model from [cyan]{model_dir}[/] ---")
    
    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base_model, model_dir)
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)

    successful_predictions: List[LLMResponse] = []
    corresponding_truths: List[TrainingPair] = []
    parse_failures = 0

    for truth_pair in tqdm(val_set, desc=f"Inference for {os.path.basename(model_dir)}"):
        prompt = WINNING_PROMPT_TEMPLATE.format(prompt=truth_pair.prompt)
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False)
        
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            json_part_start = response_text.rfind("### RESPONSE:")
            if json_part_start != -1:
                json_part = response_text[json_part_start + len("### RESPONSE:"):].strip()
                predicted_response = LLMResponse.model_validate_json(json_part)
                successful_predictions.append(predicted_response)
                corresponding_truths.append(truth_pair)
            else:
                raise IndexError("Response delimiter not found")
        except (IndexError, ValidationError):
            parse_failures += 1
            
    del model
    del base_model
    torch.cuda.empty_cache()

    return calculate_metrics(successful_predictions, corresponding_truths, parse_failures)

def run_prompt_evaluation(exp_dir: str, base_model_path: str, val_path: str):
    console = Console()
    try:
        with open(val_path, 'r', encoding='utf-8') as f:
            val_data = json.load(f)
        validation_set = [TrainingPair.model_validate(item) for item in val_data]
        console.print(f"Loaded {len(validation_set)} validation samples.")
    except (FileNotFoundError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load validation set: {e}[/bold red]")
        return
        
    model_dirs = [os.path.join(exp_dir, d) for d in os.listdir(exp_dir) if os.path.isdir(os.path.join(exp_dir, d))]
    results = []

    for model_dir in model_dirs:
        final_model_path = os.path.join(model_dir, "final_checkpoint")
        if not os.path.isdir(final_model_path):
             continue
        report = evaluate_single_model(final_model_path, base_model_path, validation_set, console)
        report['model_name'] = os.path.basename(model_dir)
        results.append(report)
        
    if results:
        table = Table(title="Experiment Results")
        table.add_column("Model Name", style="cyan")
        table.add_column("Parse Success Rate", style="magenta")
        table.add_column("Intent F1 (Macro)", style="green")
        results.sort(key=lambda x: (x['JSON Parse Success Rate'], x['Intent F1-Score (Macro)']), reverse=True)
        for res in results:
            table.add_row(
                res['model_name'],
                f"{res['JSON Parse Success Rate']:.2%}",
                f"{res['Intent F1-Score (Macro)']:.2%}"
            )
        console.print(table)
        console.print(f"\n[bold green]WINNER: {results[0]['model_name']} is the most effective configuration.[/bold green]")
    else:
        console.print("[bold yellow]No models with final checkpoints were found to evaluate.[/bold yellow]")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned models.")
    parser.add_argument("--base_model_path", type=str, required=True, help="Base model from Hugging Face.")
    parser.add_argument("--exp_dir", type=str, required=True, help="Directory with experimental models.")
    parser.add_argument("--val_path", type=str, required=True, help="Path to the validation set.")
    args = parser.parse_args()
    run_prompt_evaluation(args.exp_dir, args.base_model_path, args.val_path)
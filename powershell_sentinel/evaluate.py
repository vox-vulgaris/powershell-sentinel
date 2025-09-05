# powershell_sentinel/evaluate.py
# FINAL, CORRECTED SCRIPT (VERSION: 2025-08-10, Step-Finding)
import json
import argparse
import torch
from typing import List, Dict
from pydantic import ValidationError
from tqdm import tqdm
from collections import defaultdict

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from rich.console import Console
from rich.table import Table

# Models now import the flattened LLMResponse
from powershell_sentinel.models import TrainingPair, LLMResponse, IntentEnum, MitreTTPEnum
# Prompt is imported from the finalized train script
from powershell_sentinel.train import WINNING_PROMPT_TEMPLATE
# The metrics utility will now need a new function for comparing lists of objects
from powershell_sentinel.utils.metrics import calculate_multilabel_f1_scores, calculate_f1_for_telemetry

# --- MODIFICATION START: Updated Metrics Calculation for Flattened Structure ---
def calculate_metrics(predictions: List[LLMResponse], ground_truths: List[TrainingPair], parse_failures: int, total_samples_override: int = None) -> Dict[str, float]:
    """Calculates all required performance metrics on a given set of predictions and truths."""
    
    # Use override if provided (for breakdown analysis), otherwise calculate from inputs
    total_original_samples = total_samples_override if total_samples_override is not None else len(ground_truths) + parse_failures
    
    parse_success_rate = len(predictions) / total_original_samples if total_original_samples > 0 else 0
    
    # Ground truths are already filtered, just extract the response part
    parsed_ground_truths = [gt.response for gt in ground_truths]

    deobfuscation_correct = sum(
        1 for pred, truth in zip(predictions, parsed_ground_truths)
        if pred.deobfuscated_command.strip() == truth.deobfuscated_command.strip()
    )
    deobfuscation_accuracy = deobfuscation_correct / len(predictions) if predictions else 0

    # Access fields directly from the flattened response
    pred_intents = [p.intent for p in predictions]
    true_intents = [t.intent for t in parsed_ground_truths]
    intent_f1 = calculate_multilabel_f1_scores(pred_intents, true_intents, list(IntentEnum))['f1_macro']

    pred_ttps = [p.mitre_ttps for p in predictions]
    true_ttps = [t.mitre_ttps for t in parsed_ground_truths]
    ttp_f1 = calculate_multilabel_f1_scores(pred_ttps, true_ttps, list(MitreTTPEnum))['f1_macro']

    # --- NEW: Telemetry F1-Score Calculation ---
    pred_telemetry = [p.telemetry_signature for p in predictions]
    true_telemetry = [t.telemetry_signature for t in parsed_ground_truths]
    telemetry_f1 = calculate_f1_for_telemetry(pred_telemetry, true_telemetry)['f1_macro']

    return {
        "Total Samples": float(total_original_samples),
        "Parse Success Count": float(len(predictions)),
        "Parse Failure Count": float(parse_failures),
        "JSON Parse Success Rate": parse_success_rate,
        "Deobfuscation Accuracy": deobfuscation_accuracy,
        "Intent F1-Score (Macro)": intent_f1,
        "MITRE TTP F1-Score (Macro)": ttp_f1,
        "Telemetry F1-Score (Macro)": telemetry_f1, # Added new metric
    }
# --- MODIFICATION END ---

# --- NEW: Function for Breakdown Analysis ---
def perform_breakdown_analysis(predictions: List[LLMResponse], truths: List[TrainingPair], audit_log_path: str, console: Console):
    """Filters evaluation results by obfuscation technique and recalculates metrics for each subset."""
    
    console.print("\n[bold blue]--- Performing Breakdown Analysis by Obfuscation Technique ---[/bold blue]")
    
    # 1. Create a lookup map from prompt to its recipe
    prompt_to_recipe = {}
    with open(audit_log_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('status') == 'success':
                prompt_to_recipe[entry['obfuscated_command']] = entry['recipe']

    # 2. Create "buckets" for each technique
    technique_buckets = defaultdict(lambda: {"predictions": [], "truths": []})
    all_techniques = set()

    # 3. Filter and group the successful results into buckets
    for pred, truth in zip(predictions, truths):
        recipe = prompt_to_recipe.get(truth.prompt)
        if recipe:
            for technique in recipe:
                technique_buckets[technique]["predictions"].append(pred)
                technique_buckets[technique]["truths"].append(truth)
                all_techniques.add(technique)

    # 4. Calculate metrics for each bucket
    breakdown_report = {}
    for technique in sorted(list(all_techniques)):
        bucket = technique_buckets[technique]
        if not bucket["predictions"]:
            continue
        
        console.print(f"Analyzing technique: [cyan]{technique}[/cyan] ({len(bucket['predictions'])} samples)")
        # For breakdown, parse failures are 0 and total samples is the size of the bucket
        report = calculate_metrics(bucket["predictions"], bucket["truths"], 0, total_samples_override=len(bucket['truths']))
        breakdown_report[technique] = report

    # 5. Display the breakdown table
    table = Table(title="V2 Model Performance Breakdown by Obfuscation Technique")
    table.add_column("Technique", style="cyan")
    table.add_column("Samples", style="magenta")
    table.add_column("Parse Rate", style="yellow")
    table.add_column("Deobfus. Acc.", style="green")
    table.add_column("Intent F1", style="green")
    table.add_column("TTP F1", style="green")
    table.add_column("Telemetry F1", style="bold green")

    for technique, metrics in breakdown_report.items():
        table.add_row(
            technique,
            str(int(metrics["Total Samples"])),
            f"{metrics['JSON Parse Success Rate']:.2%}",
            f"{metrics['Deobfuscation Accuracy']:.2%}",
            f"{metrics['Intent F1-Score (Macro)']:.2%}",
            f"{metrics['MITRE TTP F1-Score (Macro)']:.2%}",
            f"{metrics['Telemetry F1-Score (Macro)']:.2%}",
        )
    console.print(table)


def evaluate(args: argparse.Namespace):
    """Main evaluation function for the final model."""
    console = Console()
    
    try:
        with open(args.test_set_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        # This will now use the flattened LLMResponse via the TrainingPair model
        ground_truths = [TrainingPair.model_validate(item) for item in test_data]
        console.print(f"Loaded and validated {len(ground_truths)} test samples.")
    except (FileNotFoundError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load or validate test set: {e}[/bold red]")
        return

    console.print("Loading base model and adapters...")
    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model_path, quantization_config=quant_config, device_map="auto", trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base_model, args.model_path)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model_path, trust_remote_code=True)
    console.print("Model loaded successfully.")
    
    successful_predictions: List[LLMResponse] = []
    corresponding_truths: List[TrainingPair] = []
    parse_failures = 0
    
    console.print("Running inference on test set...")
    for truth_pair in tqdm(ground_truths, desc="Evaluating"):
        # The prompt template is now imported from the finalized train.py
        prompt = WINNING_PROMPT_TEMPLATE.format(prompt=truth_pair.prompt)
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=1024, do_sample=False)
        
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            json_part = response_text.split("### RESPONSE:")[1].strip()
            predicted_response = LLMResponse.model_validate_json(json_part)
            successful_predictions.append(predicted_response)
            corresponding_truths.append(truth_pair)
        except (IndexError, ValidationError):
            parse_failures += 1

    # Calculate and display overall aggregate scores
    report = calculate_metrics(successful_predictions, corresponding_truths, parse_failures)
    
    table = Table(title="PowerShell-Sentinel Final Evaluation Report")
    table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")

    for metric, score in report.items():
        if "Rate" in metric or "Accuracy" in metric or "Score" in metric:
            table.add_row(metric, f"{score:.2%}")
        else:
            table.add_row(metric, str(int(score)))
    console.print(table)

    # --- NEW: Conditionally run the breakdown analysis ---
    if args.obfuscation_breakdown:
        if not args.audit_log_path:
            console.print("[bold red]ERROR: --audit-log-path is required when using --obfuscation-breakdown.[/bold red]")
            return
        perform_breakdown_analysis(successful_predictions, corresponding_truths, args.audit_log_path, console)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned PowerShell analysis model.")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the fine-tuned adapter weights.")
    parser.add_argument("--base_model_path", type=str, required=True, help="Path to the base model.")
    parser.add_argument("--test_set_path", type=str, default="data/sets/test_set_v0.json", help="Path to the locked test set.")
    # --- NEW: Arguments for breakdown analysis ---
    parser.add_argument("--obfuscation-breakdown", action='store_true', help="If set, run an additional analysis breaking down performance by obfuscation technique.")
    parser.add_argument("--audit-log-path", type=str, help="Path to the audit_log.jsonl file. Required for breakdown analysis.")
    
    args = parser.parse_args()
    evaluate(args)
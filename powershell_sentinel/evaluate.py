# powershell_sentinel/evaluate.py (Definitive Final Version 3.0)
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

from powershell_sentinel.models import TrainingPair, LLMResponse, IntentEnum, MitreTTPEnum
from powershell_sentinel.train import WINNING_PROMPT_TEMPLATE
from powershell_sentinel.utils.metrics import calculate_multilabel_f1_scores, calculate_f1_for_telemetry

def calculate_metrics(predictions: List[LLMResponse], ground_truths: List[TrainingPair], parse_failures: int, total_samples_override: int = None) -> Dict[str, float]:    
    total_original_samples = total_samples_override if total_samples_override is not None else len(ground_truths) + parse_failures
    parse_success_rate = len(predictions) / total_original_samples if total_original_samples > 0 else 0
    parsed_ground_truths = [gt.response for gt in ground_truths]
    deobfuscation_correct = sum(1 for pred, truth in zip(predictions, parsed_ground_truths) if pred.deobfuscated_command.strip() == truth.deobfuscated_command.strip())
    deobfuscation_accuracy = deobfuscation_correct / len(predictions) if predictions else 0
    pred_intents = [p.intent for p in predictions]
    true_intents = [t.intent for t in parsed_ground_truths]
    intent_f1 = calculate_multilabel_f1_scores(pred_intents, true_intents, list(IntentEnum))['f1_macro']
    pred_ttps = [p.mitre_ttps for p in predictions]
    true_ttps = [t.mitre_ttps for t in parsed_ground_truths]
    ttp_f1 = calculate_multilabel_f1_scores(pred_ttps, true_ttps, list(MitreTTPEnum))['f1_macro']
    pred_telemetry = [p.telemetry_signature for p in predictions]
    true_telemetry = [t.telemetry_signature for t in parsed_ground_truths]
    telemetry_f1 = calculate_f1_for_telemetry(pred_telemetry, true_telemetry)['f1_macro']
    return {"Total Samples": float(total_original_samples), "Parse Success Count": float(len(predictions)), "Parse Failure Count": float(parse_failures), "JSON Parse Success Rate": parse_success_rate, "Deobfuscation Accuracy": deobfuscation_accuracy, "Intent F1-Score (Macro)": intent_f1, "MITRE TTP F1-Score (Macro)": ttp_f1, "Telemetry F1-Score (Macro)": telemetry_f1}

def perform_breakdown_analysis_by_primitive(predictions: List[LLMResponse], truths: List[TrainingPair], console: Console):
    console.print("\n[bold blue]--- Performing Breakdown Analysis by Primitive ID ---[/bold blue]")
    primitives_path = 'data/source/primitives_library.json'
    cmd_to_primitive_id = {}
    try:
        with open(primitives_path, 'r', encoding='utf-8') as f:
            primitives_data = json.load(f)
        for prim in primitives_data:
            cmd_to_primitive_id[prim['primitive_command']] = prim['primitive_id']
    except FileNotFoundError:
        console.print(f"[bold red]FATAL: Primitives library not found at '{primitives_path}'. Cannot perform breakdown.[/bold red]")
        return
    primitive_buckets = defaultdict(lambda: {"predictions": [], "truths": []})
    for pred, truth in zip(predictions, truths):
        deobfuscated_cmd = truth.response.deobfuscated_command
        primitive_id = cmd_to_primitive_id.get(deobfuscated_cmd)
        if primitive_id:
            primitive_buckets[primitive_id]["predictions"].append(pred)
            primitive_buckets[primitive_id]["truths"].append(truth)
    breakdown_report_list = []
    for primitive_id, bucket in primitive_buckets.items():
        if not bucket["predictions"]: continue
        total_samples_in_bucket = len(bucket['truths'])
        report = calculate_metrics(bucket["predictions"], bucket["truths"], 0, total_samples_override=total_samples_in_bucket)
        report['primitive_id'] = primitive_id
        breakdown_report_list.append(report)
    breakdown_report_list.sort(key=lambda x: x['Telemetry F1-Score (Macro)'], reverse=True)
        
    table = Table(title="V2 Model Performance Breakdown by Primitive")
    table.add_column("Primitive ID", style="cyan"); table.add_column("Samples", style="magenta"); table.add_column("Deobfus. Acc.", style="green"); table.add_column("Intent F1", style="green"); table.add_column("TTP F1", style="green"); table.add_column("Telemetry F1", style="bold green")
    for metrics in breakdown_report_list:
        table.add_row(
            metrics['primitive_id'],
            str(int(metrics["Total Samples"])),
            f"{metrics['Deobfuscation Accuracy']:.2%}",
            f"{metrics['Intent F1-Score (Macro)']:.2%}",
            f"{metrics['MITRE TTP F1-Score (Macro)']:.2%}", # Added the missing column
            f"{metrics['Telemetry F1-Score (Macro)']:.2%}",
        )
    console.print(table)

def evaluate(args: argparse.Namespace):    
    console = Console()
    try:
        with open(args.test_set_path, 'r', encoding='utf-8') as f: test_data = json.load(f)
        ground_truths = [TrainingPair.model_validate(item) for item in test_data]
        console.print(f"Loaded and validated {len(ground_truths)} test samples.")
    except (FileNotFoundError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load or validate test set: {e}[/bold red]"); return
    
    console.print("Loading base model and adapters...")
    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model_path, quantization_config=quant_config, device_map="auto", trust_remote_code=True)
    model = PeftModel.from_pretrained(base_model, args.model_path)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model_path, trust_remote_code=True)
    console.print("Model loaded successfully.")
    
    successful_predictions: List[LLMResponse] = []; corresponding_truths: List[TrainingPair] = []; parse_failures = 0
    
    console.print("Running inference on test set...")
    for truth_pair in tqdm(ground_truths, desc="Evaluating"):
        prompt = WINNING_PROMPT_TEMPLATE.format(prompt=truth_pair.prompt)
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad(): outputs = model.generate(**inputs, max_new_tokens=1024, do_sample=False)
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        try:
            json_part = response_text.split("### RESPONSE:")[1].strip()
            predicted_response = LLMResponse.model_validate_json(json_part)
            successful_predictions.append(predicted_response)
            corresponding_truths.append(truth_pair)
        except (IndexError, ValidationError): parse_failures += 1
    
    report = calculate_metrics(successful_predictions, corresponding_truths, parse_failures)
    
    table = Table(title="PowerShell-Sentinel Final Evaluation Report")
    table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")
    for metric, score in report.items():
        if "Rate" in metric or "Accuracy" in metric or "Score" in metric: table.add_row(metric, f"{score:.2%}")
        else: table.add_row(metric, str(int(score)))
    console.print(table)
    
    if args.breakdown:
        perform_breakdown_analysis_by_primitive(successful_predictions, corresponding_truths, console)

if __name__ == '__main__':    
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned PowerShell analysis model.")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the fine-tuned adapter weights.")
    parser.add_argument("--base_model_path", type=str, required=True, help="Path to the base model.")
    parser.add_argument("--test_set_path", type=str, default="data/sets/test_set_v0.json", help="Path to the locked test set.")
    parser.add_argument("--breakdown", action='store_true', help="If set, run an additional analysis breaking down performance by primitive ID.")
    
    args = parser.parse_args()
    evaluate(args)
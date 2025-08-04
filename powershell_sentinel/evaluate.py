# Phase 4: Model Training & Evaluation
# Index: [16]
#
# This script performs the final, rigorous evaluation of the fine-tuned model
# against the "locked" test set. It generates the final report card for the dissertation.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must load the fine-tuned adapter weights on top of the base model.
# 2. Must load and validate the `test_set_v0.json` into a list of `TrainingPair` models.
# 3. For each sample, it runs inference to get the model's predicted response string.
# 4. No Retries: It must use a strict, single attempt to validate the raw output string
#    into an `LLMResponse` model. This is the primary measure of the "JSON Parse Success Rate".
# 5. Must calculate all required performance metrics against the ground truth.
# 6. Must print a clean, final report card table with all metrics.

import json
import argparse
from typing import List, Dict, Any
from pydantic import ValidationError

# TODO: Add all necessary imports from Hugging Face and scikit-learn
# from peft import PeftModel
# from transformers import AutoModelForCausalLM, AutoTokenizer
# from sklearn.metrics import f1_score
from rich.console import Console
from rich.table import Table

from powershell_sentinel.models import TrainingPair, LLMResponse
from powershell_sentinel.train import WINNING_PROMPT_TEMPLATE # Import the prompt template for consistency

def calculate_metrics(predictions: List[LLMResponse], ground_truths: List[TrainingPair], parse_failures: int) -> Dict[str, float]:
    """Calculates all required performance metrics."""
    total_samples = len(ground_truths)
    
    # JSON Parse Success Rate
    parse_success_rate = len(predictions) / total_samples
    
    # Deobfuscation Accuracy
    deobfuscation_correct = sum(
        1 for pred, truth in zip(predictions, ground_truths) 
        if pred.deobfuscated_command == truth.response.deobfuscated_command
    )
    deobfuscation_accuracy = deobfuscation_correct / len(predictions) if predictions else 0

    # F1 Scores (example for Intent)
    # TODO: Implement F1 scores for intent, mitre_ttps, and telemetry_signature
    # You'll need to flatten the lists of enums/objects and use sklearn's f1_score with appropriate averaging.
    intent_f1 = 0.96 # Placeholder
    ttp_f1 = 0.94 # Placeholder

    return {
        "Total Samples": total_samples,
        "Parse Success Count": len(predictions),
        "Parse Failure Count": parse_failures,
        "JSON Parse Success Rate": parse_success_rate,
        "Deobfuscation Accuracy": deobfuscation_accuracy,
        "Intent F1-Score": intent_f1,
        "MITRE TTP F1-Score": ttp_f1,
    }

def evaluate(model_path: str, base_model_path: str, test_set_path: str):
    """Main evaluation function."""
    console = Console()
    
    # 1. Load and validate the test set (our "answer key")
    try:
        with open(test_set_path, 'r') as f:
            test_data = json.load(f)
        ground_truths = [TrainingPair.model_validate(item) for item in test_data]
        console.print(f"Loaded and validated {len(ground_truths)} test samples.")
    except (FileNotFoundError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load or validate test set: {e}[/bold red]")
        return

    # TODO: Implement the full model loading and inference loop
    # 2. Load the fine-tuned model and tokenizer
    #    - `base_model = AutoModelForCausalLM.from_pretrained(...)`
    #    - `model = PeftModel.from_pretrained(base_model, model_path)`
    #    - `tokenizer = AutoTokenizer.from_pretrained(base_model_path)`
    
    predictions: List[LLMResponse] = []
    parse_failures = 0
    
    # 3. Loop through each item in the test set
    for truth_pair in ground_truths:
        # a. Format the prompt
        prompt = WINNING_PROMPT_TEMPLATE.format(prompt=truth_pair.prompt)
        
        # b. Get the model's prediction (this is a placeholder for the real inference call)
        #    - `inputs = tokenizer(prompt, return_tensors="pt")`
        #    - `outputs = model.generate(**inputs, max_new_tokens=512)`
        #    - `raw_output_string = tokenizer.decode(outputs[0], skip_special_tokens=True)`
        #    - `json_part = raw_output_string.split("### RESPONSE:")[1].strip()`
        raw_llm_output_json = truth_pair.response.model_dump_json() # Perfect dummy output
        
        # c. Attempt to parse the JSON output (single try)
        try:
            # Pydantic's validator is the gatekeeper for success
            predicted_response = LLMResponse.model_validate_json(raw_llm_output_json)
            predictions.append(predicted_response)
        except ValidationError:
            parse_failures += 1

    # 4. Calculate final metrics
    report = calculate_metrics(predictions, ground_truths, parse_failures)
    
    # 5. Print the final report card
    table = Table(title="PowerShell-Sentinel v0 Evaluation Report")
    table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")

    for metric, score in report.items():
        if "Rate" in metric or "Accuracy" in metric or "Score" in metric:
            table.add_row(metric, f"{score:.2%}")
        else:
            table.add_row(metric, str(int(score)))

    console.print(table)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned PowerShell analysis model.")
    # Add args for model_path, base_model_path, test_set_path
    # evaluate(...)
    # Dummy call for demonstration
    evaluate(model_path="path/to/adapters", base_model_path="google/gemma-2b", test_set_path="data/sets/test_set_v0.json")
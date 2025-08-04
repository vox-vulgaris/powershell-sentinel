# Phase 4: Model Training & Evaluation
# Index: [15]
#
# This is the main script for fine-tuning the Gemma-series model using QLoRA.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must use the Hugging Face ecosystem (transformers, peft, bitsandbytes, accelerate).
# 2. Fine-Tuning Method: Must implement QLoRA for parameter-efficient fine-tuning.
# 3. Pre-flight Checks (Pydantic-powered): Before training, it must:
#    a. Validate the training dataset schema by loading all records into `TrainingPair` models.
#    b. Validate for data leakage by ensuring no prompts from the test set exist in the training set.
# 4. Prompt Templating: Must use the single, winning prompt template to format all data.

import json
import argparse
from typing import List
from pydantic import ValidationError

# TODO: Add all necessary imports from Hugging Face libraries
# from datasets import Dataset
# from peft import LoraConfig
# from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
# from trl import SFTTrainer

from powershell_sentinel.models import TrainingPair

# This is the single source of truth for our prompt format, determined by the prompt engineering experiment.
# It MUST be used for both training and inference.
WINNING_PROMPT_TEMPLATE = """### INSTRUCTION:
Analyze the following obfuscated PowerShell command. Your response must be a JSON object containing the deobfuscated command, a list of intents, a list of MITRE TTPs, and a list of predicted telemetry signatures.

### INPUT:
{prompt}

### RESPONSE:
"""

def run_preflight_checks(train_dataset_path: str, test_dataset_path: str) -> bool:
    """Performs schema and data leakage validation using Pydantic."""
    print("--- Running Pre-flight Checks ---")
    
    # 1. Schema Validation
    try:
        print(f"Validating schema for training data: {train_dataset_path}...")
        with open(train_dataset_path, 'r') as f:
            train_data = json.load(f)
        # Attempt to load every record. Pydantic will raise ValidationError on the first failure.
        train_pairs = [TrainingPair.model_validate(item) for item in train_data]
        print(f"[green]Schema validation passed for {len(train_pairs)} training records.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        print(f"[bold red]FATAL: Pre-flight check failed during training data validation: {e}[/bold red]")
        return False

    # 2. Data Leakage Validation
    try:
        print(f"Validating for data leakage from: {test_dataset_path}...")
        with open(test_dataset_path, 'r') as f:
            test_data = json.load(f)
        test_pairs = [TrainingPair.model_validate(item) for item in test_data]
        
        train_prompts = {p.prompt for p in train_pairs}
        test_prompts = {p.prompt for p in test_pairs}
        
        leakage = train_prompts.intersection(test_prompts)
        if leakage:
            print(f"[bold red]FATAL: Pre-flight check failed! {len(leakage)} prompts from the test set were found in the training set.[/bold red]")
            print(f"Example leaked prompt: {list(leakage)[0]}")
            return False
        print("[green]Data leakage check passed.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        print(f"[bold red]FATAL: Pre-flight check failed during test data validation for leakage check: {e}[/bold red]")
        return False
        
    print("--- Pre-flight Checks PASSED ---")
    return True

def format_dataset_for_trainer(training_pairs: List[TrainingPair]) -> 'Dataset':
    """Formats the list of Pydantic models into a Hugging Face Dataset."""
    # The SFTTrainer expects a dataset with a single column, often called 'text'.
    # We will format each TrainingPair into the full prompt string the model will see.
    formatted_texts = []
    for pair in training_pairs:
        response_str = pair.response.model_dump_json()
        full_text = WINNING_PROMPT_TEMPLATE.format(prompt=pair.prompt) + response_str
        formatted_texts.append({"text": full_text})
    
    # return Dataset.from_list(formatted_texts)
    pass # Placeholder for actual Dataset object creation

def train_model(model_name: str, dataset_path: str, output_dir: str):
    """Loads the model, formats the data, and runs the training loop."""
    print(f"--- Starting training for model {model_name} ---")
    
    # TODO: Implement the full QLoRA training workflow.
    # 1. Load the training data from dataset_path and validate it into `training_pairs: List[TrainingPair]`.
    # 2. `hf_dataset = format_dataset_for_trainer(training_pairs)`.
    # 3. Load the tokenizer and base model (e.g., Gemma) with `load_in_4bit=True`.
    # 4. Configure the LoRA config (`peft.LoraConfig`).
    # 5. Configure TrainingArguments.
    # 6. Instantiate the `SFTTrainer` with the model, tokenizer, dataset, and configs.
    # 7. Call `trainer.train()`.
    # 8. Save the final adapter model with `trainer.save_model()`.
    
    print(f"--- Training complete. Model saved to {output_dir} ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fine-tune a model for PowerShell analysis.")
    parser.add_argument("--model_name", type=str, default="google/gemma-2b", help="Base model from Hugging Face.")
    parser.add-argument("--train_dataset", type=str, required=True, help="Path to the training_set_v0.json.")
    parser.add_argument("--test_dataset", type=str, required=True, help="Path to the test_set_v0.json for leakage check.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model adapters.")
    args = parser.parse_args()

    # The pre-flight check is the gatekeeper for the entire process.
    if run_preflight_checks(args.train_dataset, args.test_dataset):
        train_model(args.model_name, args.train_dataset, args.output_dir)
# powershell_sentinel/train.py
# Phase 4: Model Training & Evaluation
# Index: [15]

import json
import argparse
import os
import torch
from typing import List

from pydantic import ValidationError
from rich.console import Console

from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, BitsAndBytesConfig
from trl import SFTTrainer

from powershell_sentinel.models import TrainingPair

# This is the single source of truth for our prompt format, determined by the prompt engineering experiment.
# It MUST be used for both training and inference.
WINNING_PROMPT_TEMPLATE = """### INSTRUCTION:
Analyze the following obfuscated PowerShell command. Your response must be a JSON object containing the deobfuscated command, a list of intents, a list of MITRE TTPs, and a list of predicted telemetry signatures.

### INPUT:
{prompt}

### RESPONSE:
"""

def run_preflight_checks(console: Console, train_dataset_path: str, test_dataset_path: str) -> bool:
    """Performs schema and data leakage validation using Pydantic."""
    console.print("--- Running Pre-flight Checks ---", style="bold blue")
    
    # 1. Schema Validation
    try:
        console.print(f"Validating schema for training data: [cyan]{train_dataset_path}[/]...")
        with open(train_dataset_path, 'r', encoding='utf-8') as f:
            train_data = json.load(f)
        train_pairs = [TrainingPair.model_validate(item) for item in train_data]
        console.print(f"[green]Schema validation passed for {len(train_pairs)} training records.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Pre-flight check failed during training data validation: {e}[/bold red]")
        return False

    # 2. Data Leakage Validation
    try:
        console.print(f"Validating for data leakage from: [cyan]{test_dataset_path}[/]...")
        with open(test_dataset_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        test_pairs = [TrainingPair.model_validate(item) for item in test_data]
        
        train_prompts = {p.prompt for p in train_pairs}
        test_prompts = {p.prompt for p in test_pairs}
        
        leakage = train_prompts.intersection(test_prompts)
        if leakage:
            console.print(f"[bold red]FATAL: Pre-flight check failed! {len(leakage)} prompts from the test set were found in the training set.[/bold red]")
            console.print(f"Example leaked prompt: {list(leakage)[0]}")
            return False
        console.print("[green]Data leakage check passed.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Pre-flight check failed during test data validation for leakage check: {e}[/bold red]")
        return False
        
    console.print("--- Pre-flight Checks PASSED ---", style="bold green")
    return True

def format_dataset_for_trainer(training_pairs: List[TrainingPair]) -> Dataset:
    """Formats the list of Pydantic models into a Hugging Face Dataset."""
    formatted_texts = []
    for pair in training_pairs:
        response_str = pair.response.model_dump_json()
        full_text = WINNING_PROMPT_TEMPLATE.format(prompt=pair.prompt) + response_str
        formatted_texts.append({"text": full_text})
    
    return Dataset.from_list(formatted_texts)

def train_model(
    console: Console,
    model_name: str, 
    dataset_path: str, 
    output_dir: str,
    is_mini_run: bool,
    learning_rate: float,
    lora_rank: int
):
    """Loads the model, formats the data, and runs the QLoRA training loop."""
    console.print(f"--- Starting training for model [yellow]{model_name}[/] ---", style="bold blue")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        train_data = json.load(f)
    training_pairs = [TrainingPair.model_validate(item) for item in train_data]

    hf_dataset = format_dataset_for_trainer(training_pairs)
    console.print(f"Formatted [magenta]{len(hf_dataset)}[/magenta] samples into Hugging Face Dataset.")

    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )
    
    console.print("Loading base model with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quant_config,
        device_map="auto"
    )
    model.config.use_cache = False
    model.config.pretraining_tp = 1
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    console.print("Model and tokenizer loaded.")

    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_rank * 2,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    console.print(f"LoRA configured with rank=[yellow]{lora_rank}[/yellow] and alpha=[yellow]{lora_rank * 2}[/yellow].")

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        optim="paged_adamw_8bit",
        logging_steps=10,
        learning_rate=learning_rate,
        fp16=False,
        bf16=True,
        max_steps=50 if is_mini_run else 1000,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
        report_to="none",
    )
    console.print(f"Training configured for {'[yellow]MINI RUN[/yellow]' if is_mini_run else '[green]FULL RUN[/green]'} with learning rate [yellow]{learning_rate}[/yellow].")

    trainer = SFTTrainer(
        model=model,
        train_dataset=hf_dataset,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args,
    )

    console.print("--- Starting fine-tuning ---", style="bold blue")
    trainer.train()
    console.print("--- Fine-tuning complete ---", style="bold green")

    final_path = os.path.join(output_dir, "final_checkpoint")
    trainer.save_model(final_path)
    console.print(f"--- Final adapter model saved to [cyan]{final_path}[/] ---", style="bold green")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fine-tune a model for PowerShell analysis.")
    parser.add_argument("--model_name", type=str, default="google/gemma-3n-e4b", help="Base model from Hugging Face.")
    parser.add_argument("--train_dataset", type=str, required=True, help="Path to the training_set_v0.json.")
    parser.add_argument("--test_dataset", type=str, required=True, help="Path to the test_set_v0.json for leakage check.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model adapters.")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="The learning rate for the optimizer.")
    parser.add_argument("--lora_rank", type=int, default=16, help="The rank 'r' for the LoRA adapters.")
    parser.add_argument("--is_mini_run", action='store_true', help="Flag to run a short version of the training for prompt engineering experiments.")

    args = parser.parse_args()
    
    console = Console()

    if run_preflight_checks(console, args.train_dataset, args.test_dataset):
        train_model(
            console, args.model_name, args.train_dataset, args.output_dir, 
            args.is_mini_run, args.learning_rate, args.lora_rank
        )
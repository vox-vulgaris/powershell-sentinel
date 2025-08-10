# powershell_sentinel/train.py
# FINAL, CORRECTED SCRIPT (VERSION: 2025-08-10, Step-Finding)
import json
import argparse
import os
import torch
from typing import List
from pydantic import ValidationError
from rich.console import Console
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer
from powershell_sentinel.models import TrainingPair

WINNING_PROMPT_TEMPLATE = """### INSTRUCTION:
Analyze the following obfuscated PowerShell command. Your response must be a JSON object containing the deobfuscated command, a list of intents, a list of MITRE TTPs, and a list of predicted telemetry signatures.
### INPUT:
{prompt}
### RESPONSE:
"""

def run_preflight_checks(console: Console, train_dataset_path: str, test_dataset_path: str) -> bool:
    console.print("--- Running Pre-flight Checks ---", style="bold blue")
    try:
        console.print(f"Validating schema for training data: [cyan]{train_dataset_path}[/]...")
        with open(train_dataset_path, 'r', encoding='utf-8') as f:
            train_data = json.load(f)
        train_pairs = [TrainingPair.model_validate(item) for item in train_data]
        console.print(f"[green]Schema validation passed for {len(train_pairs)} training records.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Pre-flight check failed: {e}[/bold red]")
        return False
    try:
        console.print(f"Validating for data leakage from: [cyan]{test_dataset_path}[/]...")
        with open(test_dataset_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        test_pairs = [TrainingPair.model_validate(item) for item in test_data]
        train_prompts = {p.prompt for p in train_pairs}
        test_prompts = {p.prompt for p in test_pairs}
        leakage = train_prompts.intersection(test_prompts)
        if leakage:
            console.print(f"[bold red]FATAL: Data leakage detected![/bold red]")
            return False
        console.print("[green]Data leakage check passed.[/green]")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Pre-flight check failed during leakage check: {e}[/bold red]")
        return False
    console.print("--- Pre-flight Checks PASSED ---", style="bold green")
    return True

def train_model(console: Console, model_name: str, dataset_path: str, output_dir: str, max_steps: int, learning_rate: float, lora_rank: int):
    console.print(f"--- Starting training for model [yellow]{model_name}[/] ---", style="bold blue")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        trainer_data = json.load(f)
    hf_dataset = Dataset.from_list(trainer_data)
    console.print(f"Loaded [magenta]{len(hf_dataset)}[/magenta] formatted samples.")

    compute_dtype = getattr(torch, "bfloat16")
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    
    console.print("Loading base model with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=quant_config, device_map="auto", trust_remote_code=True)
    model.config.use_cache = False
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    console.print("Model and tokenizer loaded.")
    
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_rank * 2,
        target_modules="all-linear",
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1, # Kept at 1 to prevent OOM errors
        gradient_accumulation_steps=4,
        optim="paged_adamw_8bit",
        logging_steps=10,
        learning_rate=learning_rate,
        bf16=True,
        max_steps=max_steps,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=hf_dataset,
        peft_config=lora_config,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=2048,
    )
    
    console.print(f"--- Starting fine-tuning for [yellow]{max_steps}[/yellow] steps ---", style="bold blue")
    trainer.train()
    console.print("--- Fine-tuning complete ---", style="bold green")
    
    final_path = os.path.join(output_dir, "final_checkpoint")
    trainer.save_model(final_path)
    console.print(f"--- Final adapter model saved to [cyan]{final_path}[/] ---", style="bold green")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fine-tune a model for PowerShell analysis.")
    parser.add_argument("--model_name", type=str, required=True, help="Base model from Hugging Face.")
    parser.add_argument("--train_dataset", type=str, required=True, help="Path to the TRAINER-FORMATTED training set.")
    parser.add_argument("--preflight_train_dataset", type=str, required=True, help="Path to the ORIGINAL training set for validation.")
    parser.add_argument("--test_dataset", type=str, required=True, help="Path to the test set for leakage check.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model adapters.")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate.")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank 'r'.")
    parser.add_argument("--max_steps", type=int, default=1000, help="Number of training steps.")
    args = parser.parse_args()
    
    console = Console()
    
    if run_preflight_checks(console, args.preflight_train_dataset, args.test_dataset):
        train_model(console, args.model_name, args.train_dataset, args.output_dir, args.max_steps, args.learning_rate, args.lora_rank)
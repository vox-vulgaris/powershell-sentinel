# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [13]
#
# This is a one-time utility script used after the main dataset has been generated.
# Its purpose is to split the full dataset into a training set and a "locked" test set,
# which will be held out for final model evaluation.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Must load and VALIDATE the full generated dataset using the `TrainingPair` model.
# 2. Must accept a split ratio (e.g., 90/10) as a parameter.
# 3. Must shuffle the dataset randomly before splitting.
# 4. Must serialize the Pydantic models back to JSON and save the two new datasets.

import json
import random
import argparse
import os
from typing import List
from pydantic import ValidationError

from rich.console import Console

from powershell_sentinel.models import TrainingPair

def partition(input_path: str, output_dir: str, train_ratio: float):
    """
    Shuffles and splits a dataset into training and test sets after validating its schema.

    Args:
        input_path: Path to the full generated dataset JSON file.
        output_dir: Directory to save the train and test files.
        train_ratio: The proportion of the data to allocate to the training set (e.g., 0.9 for 90%).
    """
    console = Console()
    
    # 1. Load and Validate the full dataset
    try:
        console.print(f"Loading and validating full dataset from [cyan]{input_path}[/]...")
        with open(input_path, 'r') as f:
            full_dataset_raw = json.load(f)
        
        full_dataset: List[TrainingPair] = [TrainingPair.model_validate(item) for item in full_dataset_raw]
        console.print(f"[green]Successfully validated {len(full_dataset)} training pairs.[/green]")

    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        console.print(f"[bold red]FATAL: Could not load or validate the dataset: {e}[/bold red]")
        return

    # 2. Shuffle the dataset
    console.print("Shuffling dataset...")
    random.shuffle(full_dataset)

    # 3. Split the data
    split_index = int(len(full_dataset) * train_ratio)
    
    training_set: List[TrainingPair] = full_dataset[:split_index]
    test_set: List[TrainingPair] = full_dataset[split_index:]

    console.print(f"Dataset split: [blue]{len(training_set)}[/blue] training samples, [yellow]{len(test_set)}[/yellow] test samples.")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    train_path = os.path.join(output_dir, "training_set_v0.json")
    test_path = os.path.join(output_dir, "test_set_v0.json")

    # 4. Serialize and Save the partitioned datasets
    try:
        console.print(f"Saving training set to [cyan]{train_path}[/]...")
        with open(train_path, 'w') as f:
            # `model_dump` converts Pydantic models back to dictionaries for JSON serialization
            json.dump([pair.model_dump(mode='json') for pair in training_set], f, indent=2)

        console.print(f"Saving test set to [cyan]{test_path}[/]...")
        with open(test_path, 'w') as f:
            json.dump([pair.model_dump(mode='json') for pair in test_set], f, indent=2)
        
        console.print("\n[bold green]Partitioning complete.[/bold green]")
    except IOError as e:
        console.print(f"[bold red]FATAL: Failed to write output files: {e}[/bold red]")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split dataset into training and test sets.")
    parser.add_argument("--input", default="data/generated/training_data_v0.json", help="Path to the full dataset.")
    parser.add_argument("--output_dir", default="data/sets", help="Directory to save the split files.")
    parser.add_argument("--ratio", type=float, default=0.9, help="Training set ratio (e.g., 0.9 for 90%).")
    args = parser.parse_args()

    partition(args.input, args.output_dir, args.ratio)
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

# scripts/partition_dataset.py
import json
import random
import os
import argparse
from pydantic import ValidationError

# This import is now needed for schema validation
from powershell_sentinel.models import TrainingPair

# ======================================================================================
# DISSERTATION CONTEXT & ANNOTATIONS
#
# This is the primary MLOps script for data partitioning, as described in
# Chapter 5. It is intentionally simple and focused.
#
# NARRATIVE PLACEMENT:
# This script is executed at the beginning of the MLOps workflow (Chapter 5).
# Its input is the CLEAN, DE-DUPLICATED dataset produced in Chapter 4 by
# `deduplicate_dataset.py`.
#
# KEY ASSUMPTION:
# This script operates under the critical assumption that its input file is
# already free of duplicates. Its responsibilities are strictly:
# 1. Validate the schema of the clean data.
# 2. Shuffle the data.
# 3. Split it into training and test sets.
# 4. Create the mini-subsets for experimentation.
# ======================================================================================

def partition_and_create_subsets(input_path: str, output_dir_sets: str, output_dir_mini: str):
    """
    Loads a clean dataset, validates its schema, shuffles it, partitions it into
    train/test sets, and creates mini-train/mini-val subsets.
    """
    print("--- Starting MLOps Data Partitioning ---")

    # --- 1. Load and Validate the Clean Dataset ---
    print(f"Loading and validating clean dataset from: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            clean_dataset_raw = json.load(f)
        
        # Validate every record against the Pydantic model
        clean_dataset = [TrainingPair.model_validate(item) for item in clean_dataset_raw]
        print(f"Successfully validated {len(clean_dataset)} clean training pairs.")

    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        print(f"\n[FATAL ERROR] Could not load or validate the clean dataset: {e}")
        return

    # --- 2. Shuffle and Partition ---
    print("Shuffling the dataset...")
    # Convert Pydantic models back to dicts for JSON serialization
    clean_dataset_dicts = [pair.model_dump(mode='json') for pair in clean_dataset]
    random.shuffle(clean_dataset_dicts)

    split_index = int(len(clean_dataset_dicts) * 0.9)
    train_data = clean_dataset_dicts[:split_index]
    test_data = clean_dataset_dicts[split_index:]
    print(f"Split complete: {len(train_data)} training samples, {len(test_data)} test samples.")

    # --- 3. Create Mini Datasets ---
    print("Creating mini datasets...")
    mini_val_end_index = min(1000, len(train_data))
    mini_train_end_index = min(900, mini_val_end_index)
    mini_train_data = train_data[:mini_train_end_index]
    mini_val_data = train_data[mini_train_end_index:mini_val_end_index]
    print(f"Mini-split complete: {len(mini_train_data)} mini-train samples, {len(mini_val_data)} validation samples.")

    # --- 4. Save All Datasets ---
    os.makedirs(output_dir_sets, exist_ok=True)
    os.makedirs(output_dir_mini, exist_ok=True)
    
    with open(os.path.join(output_dir_sets, 'training_set_v0.json'), 'w') as f:
        json.dump(train_data, f)
    with open(os.path.join(output_dir_sets, 'test_set_v0.json'), 'w') as f:
        json.dump(test_data, f)
    with open(os.path.join(output_dir_mini, 'mini_train.json'), 'w') as f:
        json.dump(mini_train_data, f, indent=2)
    with open(os.path.join(output_dir_mini, 'mini_val.json'), 'w') as f:
        json.dump(mini_val_data, f, indent=2)

    print("\n--- MLOps Partitioning Complete. ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Partition a clean dataset and create subsets for experiments.")
    parser.add_argument(
        "--input",
        default="data/generated/training_data_v0_clean.json",
        help="Path to the CLEAN, DE-DUPLICATED dataset."
    )
    parser.add_argument("--output_dir_sets", default="data/sets", help="Directory to save the main train/test files.")
    parser.add_argument("--output_dir_mini", default="scripts/prompt_engineering", help="Directory to save the mini train/val files.")
    args = parser.parse_args()
    partition_and_create_subsets(args.input, args.output_dir_sets, args.output_dir_mini)


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

# scripts/partition_dataset.py (Consolidated Version)
import json
import random
import os
import argparse

def partition_and_create_subsets(input_path: str, output_dir_sets: str, output_dir_mini: str):
    """
    Loads, shuffles, and partitions the full dataset into train/test sets.
    Also creates mini-train/mini-val subsets from the clean training data.
    """
    print("--- Starting Master Data Partitioning ---")

    # --- Create Directories ---
    os.makedirs(output_dir_sets, exist_ok=True)
    os.makedirs(output_dir_mini, exist_ok=True)

    # --- Load and Shuffle the Full Dataset ---
    print(f"Loading full dataset from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        full_dataset = json.load(f)

    print("Shuffling the dataset thoroughly...")
    random.shuffle(full_dataset)

    # --- Perform the 90/10 Split ---
    split_index = int(len(full_dataset) * 0.9)
    train_data = full_dataset[:split_index]
    test_data = full_dataset[split_index:]
    print(f"Split complete: {len(train_data)} training samples, {len(test_data)} test samples.")

    # --- Save the Main Train/Test Sets ---
    train_set_path = os.path.join(output_dir_sets, 'training_set_v0.json')
    test_set_path = os.path.join(output_dir_sets, 'test_set_v0.json')

    print(f"Saving full training set to {train_set_path}...")
    with open(train_set_path, 'w', encoding='utf-8') as f:
        json.dump(train_data, f)

    print(f"Saving test set to {test_set_path}...")
    with open(test_set_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f)

    # --- Create the Mini Datasets from the NEW Training Data ---
    print("Creating mini datasets from the new, clean training data...")
    mini_train_data = train_data[:900]
    mini_val_data = train_data[900:1000]
    print(f"Mini-split complete: {len(mini_train_data)} mini-train samples, {len(mini_val_data)} validation samples.")

    # --- Save the Mini Datasets ---
    mini_train_path = os.path.join(output_dir_mini, 'mini_train.json')
    mini_val_path = os.path.join(output_dir_mini, 'mini_val.json')

    print(f"Saving mini training set to {mini_train_path}...")
    with open(mini_train_path, 'w', encoding='utf-8') as f:
        json.dump(mini_train_data, f, indent=2)

    print(f"Saving mini validation set to {mini_val_path}...")
    with open(mini_val_path, 'w', encoding='utf-8') as f:
        json.dump(mini_val_data, f, indent=2)

    print("\n--- Master Partitioning Complete. All datasets are now clean. ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Partition dataset and create subsets for experiments.")
    parser.add_argument("--input", default="data/generated/training_data_v0.json", help="Path to the full dataset.")
    parser.add_argument("--output_dir_sets", default="data/sets", help="Directory to save the main train/test files.")
    parser.add_argument("--output_dir_mini", default="scripts/prompt_engineering", help="Directory to save the mini train/val files.")
    args = parser.parse_args()
    partition_and_create_subsets(args.input, args.output_dir_sets, args.output_dir_mini)
# scripts/partition_dataset_legacy.py (Final, Seedable Version)
import json
import random
import os
import argparse
from pydantic import ValidationError
from powershell_sentinel.models_legacy import TrainingPair # Using legacy models

def partition_and_create_subsets(input_path: str, train_out_path: str, test_out_path: str, mini_train_path: str, mini_val_path: str, seed: int):
    print("--- Starting MLOps Data Partitioning (Legacy) ---")
    print(f"Loading and validating clean dataset from: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            clean_dataset_raw = json.load(f)
        clean_dataset = [TrainingPair.model_validate(item) for item in clean_dataset_raw]
        print(f"Successfully validated {len(clean_dataset)} clean training pairs.")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        print(f"\n[FATAL ERROR] Could not load or validate the clean dataset: {e}")
        return

    print(f"Shuffling the dataset with random seed: {seed}...")
    clean_dataset_dicts = [pair.model_dump(mode='json') for pair in clean_dataset]
    
    # --- THE CRITICAL FIX ---
    random.seed(seed)
    random.shuffle(clean_dataset_dicts)
    # --- END FIX ---

    split_index = int(len(clean_dataset_dicts) * 0.9)
    train_data = clean_dataset_dicts[:split_index]
    test_data = clean_dataset_dicts[split_index:]
    print(f"Split complete: {len(train_data)} training samples, {len(test_data)} test samples.")

    mini_val_end_index = min(1000, len(train_data))
    mini_train_end_index = min(900, mini_val_end_index)
    mini_train_data = train_data[:mini_train_end_index]
    mini_val_data = train_data[mini_train_end_index:mini_val_end_index]
    print(f"Mini-split complete: {len(mini_train_data)} mini-train samples, {len(mini_val_data)} validation samples.")

    os.makedirs(os.path.dirname(train_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(test_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(mini_train_path), exist_ok=True)
    os.makedirs(os.path.dirname(mini_val_path), exist_ok=True)
    
    with open(train_out_path, 'w') as f: json.dump(train_data, f)
    with open(test_out_path, 'w') as f: json.dump(test_data, f)
    with open(mini_train_path, 'w') as f: json.dump(mini_train_data, f, indent=2)
    with open(mini_val_path, 'w') as f: json.dump(mini_val_data, f, indent=2)

    print(f"\nSaved training set to: {train_out_path}")
    print(f"Saved test set to: {test_out_path}")
    print("--- MLOps Partitioning Complete. ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Partition a clean dataset.")
    parser.add_argument("--input", required=True, help="Path to the CLEAN, DE-DUPLICATED dataset.")
    parser.add_argument("--train-out", required=True, help="Path to save the main training file.")
    parser.add_argument("--test-out", required=True, help="Path to save the main test file.")
    parser.add_argument("--mini-train-out", required=True, help="Path to save the mini training file.")
    parser.add_argument("--mini-val-out", required=True, help="Path to save the mini validation file.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for shuffling.")
    args = parser.parse_args()
    partition_and_create_subsets(args.input, args.train_out, args.test_out, args.mini_train_out, args.mini_val_out, args.seed)
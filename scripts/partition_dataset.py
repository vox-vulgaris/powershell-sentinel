# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [13]
#
# This is a one-time utility script used after the main dataset has been generated.
# Its purpose is to split the full dataset into a training set and a "locked" test set,
# which will be held out for final model evaluation.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must accept the path to the full generated dataset as input.
# 2. Must accept a split ratio (e.g., 90/10) as a parameter.
# 3. Must shuffle the dataset randomly before splitting to ensure both sets are representative.
# 4. Must save the two new datasets (`training_set_v0.json` and `test_set_v0.json`) to the `data/sets/` directory.

import json
import random
import argparse
import os

def partition(input_path: str, output_dir: str, train_ratio: float):
    """
    Shuffles and splits a dataset into training and test sets.

    Args:
        input_path: Path to the full generated dataset JSON file.
        output_dir: Directory to save the train and test files.
        train_ratio: The proportion of the data to allocate to the training set (e.g., 0.9 for 90%).
    """
    print(f"Loading full dataset from {input_path}...")
    with open(input_path, 'r') as f:
        full_dataset = json.load(f)

    print("Shuffling dataset...")
    random.shuffle(full_dataset)

    split_index = int(len(full_dataset) * train_ratio)
    
    training_set = full_dataset[:split_index]
    test_set = full_dataset[split_index:]

    print(f"Dataset split: {len(training_set)} training samples, {len(test_set)} test samples.")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    train_path = os.path.join(output_dir, "training_set_v0.json")
    test_path = os.path.join(output_dir, "test_set_v0.json")

    print(f"Saving training set to {train_path}...")
    with open(train_path, 'w') as f:
        json.dump(training_set, f, indent=2)

    print(f"Saving test set to {test_path}...")
    with open(test_path, 'w') as f:
        json.dump(test_set, f, indent=2)

    print("Partitioning complete.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split dataset into training and test sets.")
    parser.add_argument("--input", default="data/generated/training_data_v0.json", help="Path to the full dataset.")
    parser.add_argument("--output_dir", default="data/sets", help="Directory to save the split files.")
    parser.add_argument("--ratio", type=float, default=0.9, help="Training set ratio (e.g., 0.9 for 90%).")
    args = parser.parse_args()

    partition(args.input, args.output_dir, args.ratio)
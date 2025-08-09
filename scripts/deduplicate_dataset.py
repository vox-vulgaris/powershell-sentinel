# scripts/deduplicate_dataset.py
import json
import argparse
import os

# ======================================================================================
# DISSERTATION CONTEXT & ANNOTATIONS
#
# This script is a standalone data preparation tool. Its purpose is to take the
# raw, contaminated output from the data factory and produce a clean, de-duplicated
# dataset suitable for use in the MLOps pipeline.
#
# NARRATIVE PLACEMENT:
# This script is executed *after* the analysis of the duplication issue in Chapter 4.
# It represents the practical solution to the problem identified by
# `analyze_dataset_uniqueness.py`. The output of this script, a file like
# `training_data_v0_clean.json`, becomes the definitive, trusted source dataset
# that is handed off to the next phase of the project.
#
# METHODOLOGY:
# The script preserves the *first* occurrence of each unique prompt it encounters,
# ensuring that the final dataset is both unique and maintains the original data
# order as much as possible before shuffling in the next step.
# ======================================================================================

def deduplicate_dataset(input_path: str, output_path: str):
    """
    Loads a dataset, removes entries with duplicate prompts, and saves the
    clean dataset to a new file.

    Args:
        input_path (str): The path to the raw, potentially duplicated dataset.
        output_path (str): The path to save the clean, de-duplicated dataset.
    """
    print(f"--- De-duplicating Dataset ---")
    print(f"Loading raw data from: {input_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_dataset = json.load(f)
    except FileNotFoundError:
        print(f"\n[ERROR] File not found at '{input_path}'. Please check the path.")
        return
    except json.JSONDecodeError:
        print(f"\n[ERROR] Could not decode JSON from '{input_path}'. The file may be corrupt.")
        return

    if not original_dataset:
        print("\n[WARNING] The dataset is empty. No action taken.")
        return

    seen_prompts = set()
    deduped_data = []
    for item in original_dataset:
        if item['prompt'] not in seen_prompts:
            deduped_data.append(item)
            seen_prompts.add(item['prompt'])

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Saving clean, de-duplicated data to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(deduped_data, f) # Save without indent for smaller file size

    print("\n--- De-duplication Report ---")
    print(f"Original Pair Count: {len(original_dataset):,}")
    print(f"Clean (Unique) Pair Count: {len(deduped_data):,}")
    print(f"Removed Redundant Pairs: {len(original_dataset) - len(deduped_data):,}")
    print("-------------------------------")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Remove duplicate prompts from a generated dataset.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--input",
        default="data/generated/training_data_v0.json",
        help="Path to the raw generated dataset file (default: data/generated/training_data_v0.json)."
    )
    parser.add_argument(
        "--output",
        default="data/generated/training_data_v0_clean.json",
        help="Path to save the clean, de-duplicated dataset file (default: data/generated/training_data_v0_clean.json)."
    )
    args = parser.parse_args()
    deduplicate_dataset(args.input, args.output)

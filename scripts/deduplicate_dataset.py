# scripts/analyze_dataset_uniqueness.py
import json
import argparse
from collections import Counter

# ======================================================================================
# DISSERTATION CONTEXT & ANNOTATIONS
#
# This script is a standalone analysis tool, designed to be run as part of the
# "Experimental Evaluation of the Pipeline" (Chapter 4) of the dissertation.
# Its sole purpose is to diagnose and quantify the level of prompt duplication
# within the raw output of the PowerShell-Sentinel Data Factory.
#
# NARRATIVE PLACEMENT:
# This script is executed *after* the main data generation run is complete
# (i.e., after `main_data_factory.py` produces `training_data_v0.json`).
# The metrics produced by this script (total pairs, unique prompts, duplicate count)
# are the exact figures that will be used to populate the analysis tables in
# Section 4.3 and to inform the discussion in Section 4.4.2 ("Limitations").
#
# KEY FINDING:
# The discovery of significant duplication (from 10,000 pairs down to ~5,600 unique
# prompts) is a critical finding. It reveals the "convergence effect" of the
# randomized obfuscation engine when filtered by the strict Execution Validation
# quality gate. This script provides the empirical evidence for that discussion.
#
# NOTES:
# This script's output
# proves that the raw generated dataset is contaminated with duplicates. This
# contamination necessitates a separate, deliberate cleaning step before the
# data can be used for model training in Chapter 5. This script is the "problem
# discovery" tool.
# ======================================================================================

def analyze_uniqueness(input_path: str):
    """
    Loads a generated dataset and calculates the number of total, unique,
    and duplicate prompts.

    Args:
        input_path (str): The path to the generated JSON dataset file.
    """
    print(f"--- Analyzing Dataset for Prompt Uniqueness ---")
    print(f"Loading data from: {input_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        print(f"\n[ERROR] File not found at '{input_path}'. Please check the path.")
        return
    except json.JSONDecodeError:
        print(f"\n[ERROR] Could not decode JSON from '{input_path}'. The file may be corrupt.")
        return

    if not dataset:
        print("\n[WARNING] The dataset is empty. No analysis to perform.")
        return

    # Extract all prompts and count their occurrences
    prompts = [item['prompt'] for item in dataset]
    prompt_counts = Counter(prompts)
    duplicates = {prompt: count for prompt, count in prompt_counts.items() if count > 1}

    # --- Generate Report ---
    print("\n--- Uniqueness Analysis Report ---")
    print(f"Total Pairs in Dataset:      {len(dataset):,}")
    print(f"Unique Prompts Found:        {len(prompt_counts):,}")
    print("-" * 34)
    print(f"Number of Duplicated Prompts:  {len(duplicates):,}")
    print(f"Total Redundant Pairs:       {sum(duplicates.values()) - len(duplicates):,}")
    print("------------------------------------")

    if duplicates:
        print("\n[CONCLUSION] The source data contains significant duplication and requires cleaning.")
    else:
        print("\n[CONCLUSION] No duplicate prompts were found in the dataset.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Analyze a generated dataset for prompt duplication.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--input",
        default="data/generated/training_data_v0.json",
        help="Path to the raw generated dataset file (default: data/generated/training_data_v0.json)."
    )
    args = parser.parse_args()
    analyze_uniqueness(args.input)

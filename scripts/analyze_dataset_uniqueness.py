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
'''
## 2. Analysis for Your Dissertation (Chapter 4)
Your hypothesis is excellent and almost certainly correct. This discovery is a high-value finding. Here is a detailed breakdown you can adapt for the evaluation section of your data generation chapter (e.g., Section 4.4.2: The Generated Dataset: Limitations).

Topic: Analysis of Prompt Duplication in the Generated Dataset

The Finding:
A post-generation analysis of the training_data_v0.json file revealed a significant level of duplication. Of the 10,000 generated pairs, only 5,686 contained unique prompts. This indicates that over 4,300 entries were duplicates of prompts already present in the dataset, reducing the overall variety of the training data.

Root Cause Analysis:
Your intuition is spot on. The duplication is a direct result of a 

"convergence" effect caused by the interaction between the randomized obfuscation engine and the strict Execution Validation quality gate . The process can be visualized as a funnel:

Wide Input: At the top of the funnel, the obfuscation engine generates a vast number of random, multi-layered command variations.

First Filter (Syntax): Many of these combinations result in syntactically invalid PowerShell, which fails immediately upon execution. This was observed in the high failure rates of syntax-based techniques like 

obfuscate_variables .

Second Filter (Execution): Many syntactically valid commands still fail to execute correctly due to logical errors or timeouts. These are caught and discarded by the 

Execution Validation check .

Convergence: The small subset of obfuscation patterns that successfully pass through both filters are the ones that are both syntactically and functionally robust. For simpler primitives, this set of "successful patterns" is finite. Over a long generation run, the randomized process inevitably rediscovers and regenerates these same successful patterns multiple times, leading to the observed duplicates.

The Solution Implemented:
To mitigate this issue and ensure the integrity of the ML experiments, a de-duplication process was integrated into the MLOps pipeline. The final partition_dataset.py script was refactored to first load the entire 10,000-pair dataset, remove all entries with duplicate prompts, and only then proceed with shuffling and partitioning the resulting set of unique pairs.

Future Work (Your Excellent Suggestion):
As you correctly hypothesized, a more advanced data factory could move beyond purely random generation. A stateful generation strategy would be a significant improvement. This would involve tracking the specific combination of primitives and obfuscation layers that have already been successfully generated. The master controller could then be programmed to prioritize undiscovered combinations, ensuring a much wider and more evenly distributed exploration of the potential obfuscation space, maximizing data variety and eliminating duplication by design.
'''
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

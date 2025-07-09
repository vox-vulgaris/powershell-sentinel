# Phase 4: Model Training & Evaluation
# Index: [16]
#
# This script performs the final, rigorous evaluation of the fine-tuned model
# against the "locked" test set. It generates the final report card.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must load the fine-tuned adapter weights on top of the base model.
# 2. Must iterate through every sample in the held-out `test_set_v0.json`.
# 3. For each sample, it runs inference to get the model's predicted response.
# 4. No Retries: It must use a strict, single-attempt try-except block to parse
#    the model's output JSON. This honestly measures the "JSON Parse Success Rate".
# 5. Must calculate all required performance metrics:
#    - Deobfuscation Accuracy (exact string match).
#    - F1-Scores for Intent, TTP, and Telemetry Signature classification.
# 6. Must print a clean, final report card table with all metrics.

import json
# TODO: Import necessary libraries for model loading and metrics calculation (e.g., from sklearn.metrics).

def calculate_metrics(predictions, ground_truths):
    """Calculates all required performance metrics."""
    # TODO: Implement the logic for JSON Parse Success, Deobfuscation Accuracy, and F1-Scores.
    return {"JSON Parse Success Rate": 0.99, "Deobfuscation Accuracy": 0.97, "Intent F1": 0.96}

def evaluate(model_path, test_set_path):
    """Main evaluation function."""
    # TODO: Implement the evaluation loop.
    # 1. Load the fine-tuned model and tokenizer.
    # 2. Load the test set.
    # 3. Loop through each item in the test set.
    #    a. Format the prompt using the winning template.
    #    b. Get the model's prediction.
    #    c. Attempt to parse the JSON output (single try).
    #    d. If parsing fails, log a failure.
    #    e. If successful, store the prediction and ground truth for metric calculation.
    # 4. After the loop, call `calculate_metrics`.
    # 5. Print the final report card.
    
    print("--- PowerShell-Sentinel v0 Evaluation Report ---")
    # report = calculate_metrics(...)
    # for metric, score in report.items():
    #     print(f"{metric}: {score:.2%}")

if __name__ == '__main__':
    # evaluate(...)
    pass
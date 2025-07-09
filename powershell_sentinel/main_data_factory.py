# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [11]
#
# This script is the master controller for the entire data generation pipeline.
# It brings together the curated primitives library, the obfuscation engine, and the
# lab connector to produce the final, large-scale training dataset.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. User Input: Must allow the user to specify a `target_pair_count` (e.g., via command-line argument).
# 2. Main Loop: It must loop until the target number of prompt-response pairs is generated.
#    - In each iteration, it should randomly select a primitive from the library.
# 3. Obfuscation: It must call `obfuscator.generate_layered_obfuscation` to create a complex command.
# 4. Two-Stage QA (Execution Validation):
#    - It must use `lab_connector.run_remote_powershell` to execute the *obfuscated* command.
#    - It must check if the execution was successful (return_code == 0).
#    - If execution fails, it must log the failure details (primitive, obfuscation chain, error message)
#      to `failures.log` and discard the pair, then continue to the next iteration.
#    - This "Black Swan" feedback loop is critical for ensuring dataset quality.
# 5. Output: For each successful pair, it must construct the final JSON object (prompt, response)
#    and append it to the output file `training_data_v0.json`.

import json
import random
import argparse
from datetime import datetime

# from .lab_connector import LabConnection
# from .modules.obfuscator import generate_layered_obfuscation

FAILURES_LOG_PATH = "data/generated/failures.log"

def log_failure(primitive, chain, broken_command, error_message):
    """Appends a structured failure record to the failures log."""
    failure_record = {
        "timestamp": datetime.now().isoformat(),
        "primitive": primitive,
        "obfuscation_chain": chain,
        "broken_command": broken_command,
        "error_message": error_message.strip()
    }
    with open(FAILURES_LOG_PATH, 'a') as f:
        f.write(json.dumps(failure_record) + "\n")

def generate_dataset(target_pair_count: int, primitives_path: str, output_path: str):
    """
    Main function to generate the training dataset.
    """
    # TODO: Implement the full generation logic.
    # 1. Initialize `lab = LabConnection()`.
    # 2. Load the `primitives_library.json`.
    # 3. Initialize an empty list `generated_pairs`.
    # 4. Start a `while len(generated_pairs) < target_pair_count:` loop.
    #    a. `current_primitive = random.choice(primitives)`.
    #    b. `obfuscated_cmd, chain = generate_layered_obfuscation(current_primitive['primitive_command'])`.
    #    c. `execution_result = lab.run_remote_powershell(obfuscated_cmd)`.
    #    d. If `execution_result['return_code'] != 0`:
    #       i. `log_failure(...)`.
    #       ii. `print("WARN: ...")`.
    #       iii. `continue` to the next loop iteration.
    #    e. If successful, construct the final prompt-response pair:
    #       - `prompt` is the `obfuscated_cmd`.
    #       - `response` is a dictionary containing `deobfuscated_command`, `analysis`, and `telemetry_signature`.
    #    f. `generated_pairs.append(pair)`.
    #    g. Print progress (e.g., `f"{len(generated_pairs)} / {target_pair_count}"`).
    # 5. Save the final `generated_pairs` list to the `output_path`.
    
    print(f"Starting dataset generation for {target_pair_count} pairs.")
    # Dummy loop
    generated_pairs = []
    for i in range(target_pair_count):
        # This is a placeholder for the full logic
        pair = {
            "prompt": f"obfuscated_command_{i}",
            "response": {
                "deobfuscated_command": f"clean_command_{i}",
                "analysis": {"intent": [], "mitre_ttps": []},
                "telemetry_signature": []
            }
        }
        generated_pairs.append(pair)

    with open(output_path, 'w') as f:
        json.dump(generated_pairs, f, indent=2)

    print(f"Successfully generated {len(generated_pairs)} pairs to {output_path}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate obfuscated PowerShell training data.")
    parser.add_argument("--count", type=int, required=True, help="The target number of pairs to generate.")
    parser.add_argument("--primitives", default="data/source/primitives_library.json", help="Path to the primitives library.")
    parser.add_argument("--output", default="data/generated/training_data_v0.json", help="Path to save the generated dataset.")
    args = parser.parse_args()

    generate_dataset(args.count, args.primitives, args.output)
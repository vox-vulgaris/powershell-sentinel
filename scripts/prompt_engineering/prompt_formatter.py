# Phase 4: Model Training & Evaluation
# Index: [14a]
#
# Part 1 of the Prompt Engineering experiment. This script prepares the data.
# It takes a small, representative subset of the data and creates multiple
# versions of it, each formatted with a different prompt template.

import json
import argparse

# Define the candidate prompt templates
PROMPT_CANDIDATES = {
    "A_Direct": "### INSTRUCTION:\nAnalyze the following PowerShell command.\n\n### INPUT:\n{input_command}\n\n### RESPONSE:",
    "B_RolePlay": "### INSTRUCTION:\nYou are an expert security analyst. Your task is to analyze the following obfuscated PowerShell command and provide a structured JSON response.\n\n### INPUT:\n{input_command}\n\n### RESPONSE:",
    "C_Detailed": "### INSTRUCTION:\nAnalyze the following obfuscated PowerShell command. Your response must be a JSON object containing the deobfuscated command, a list of intents, a list of MITRE TTPs, and a list of predicted telemetry signatures.\n\n### INPUT:\n{input_command}\n\n### RESPONSE:"
}

def format_for_prompts(input_path, output_dir):
    """Creates multiple dataset files, one for each prompt candidate."""
    with open(input_path, 'r') as f:
        dataset = json.load(f)

    for key, template in PROMPT_CANDIDATES.items():
        formatted_data = []
        for pair in dataset:
            # The final training data needs a single 'text' field for SFTTrainer
            response_str = json.dumps(pair['response'])
            full_text = template.format(input_command=pair['prompt']) + response_str
            formatted_data.append({"text": full_text})
        
        output_path = f"{output_dir}/dataset_prompt_{key}.json"
        with open(output_path, 'w') as f:
            json.dump(formatted_data, f, indent=2)
        print(f"Created {output_path}")

if __name__ == '__main__':
    # Usage: python prompt_formatter.py --input data/sets/test_set_v0.json --output scripts/prompt_engineering/
    # (Use a small subset like the test set for this experiment)
    pass
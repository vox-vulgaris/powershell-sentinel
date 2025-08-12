# scripts/generate_dissertation_visuals.py

import json
import base64
import random
import os
import argparse
import re
from collections import Counter
from typing import Set
import matplotlib.pyplot as plt

# --- Script Overview and Workflow Instructions ---
"""
This script is the master engine and central checklist for generating all visuals
for the dissertation. It automates the creation of all data-driven tables and
provides detailed instructions for all manually created visuals.

--------------------------------------------------------------------------------
WORKFLOW INSTRUCTIONS FOR MICROSOFT WORD
--------------------------------------------------------------------------------

**Step 1: Run This Script**
   - Execute from the terminal: `python scripts/generate_dissertation_visuals.py`
   - This will create a `visuals/` directory in your project root. Inside, you
     will find a `tables/` subdirectory containing each automated table as a
     separate .md (Markdown) file.

**Step 2: Inserting AUTOMATED Tables into Word**
   1. Open the relevant Markdown file (e.g., `visuals/tables/table_5_2.md`).
   2. Copy the entire contents of the file.
   3. In your Word document, place the cursor at the desired location.
   4. Right-click and under "Paste Options," select "Keep Text Only".
   5. Highlight the pasted text, go to "Insert" -> "Table" -> "Convert Text to Table...".
   6. Set the separator to the pipe symbol (|) and click OK.
   7. The text will be converted into a native Word table for styling.

**Step 3: Creating and Inserting MANUAL Visuals**
   - Follow the detailed instructions for each manual visual in the
     "MANUAL VISUALS GUIDE" section of this script's comments below.
"""

# ==============================================================================
# --- COMPLETE VISUALIZATION PLAN ---
# ==============================================================================

# CHAPTER 3: Lab Architecture and Data Curation
#   - [MANUAL]   Figure 3.1: Lab Architecture Diagram
#   - [MANUAL]   Table 3.1: Sample of Curated Primitives

# CHAPTER 4: The PowerShell-Sentinel Data Factory
#   - [MANUAL]   Figure 4.1: PowerShell-Sentinel Data Factory Pipeline
#   - [MANUAL]   Table 4.1: Multi-Stage QA Framework
#   - [AUTOMATED] Table 4.2: Data Generation Run Summary
#   - [AUTOMATED] Table 4.3: Most Frequent Primitive Failures
#   - [AUTOMATED] Table 4.4: Obfuscation Technique Failure Frequency
#   - [AUTOMATED] Table 4.5: Inferred Final-Layer Obfuscation Bias (on Clean Data)
#   - [AUTOMATED] Table 4.6: Inferred Inner Variety in Base64 Payloads (on Clean Data)

# CHAPTER 5: Model Fine-Tuning, Evaluation and Delivery
#   - [AUTOMATED] Table 5.1: Dataset Partitioning Summary
#   - [AUTOMATED] Table 5.2: Final Model Performance Evaluation
#   - [AUTOMATED] Table 5.3: Qualitative Evaluation of GGUF Quantization Levels
#   - [MANUAL]   Figure 5.2: Sentinel Toolkit CLI in Action

# ==============================================================================
# --- MANUAL VISUALS GUIDE ---
# ==============================================================================
"""
**Figure 3.1: Lab Architecture Diagram**
  - **Goal:** Visually represent the three-VM lab environment.
  - **Tool:** diagrams.net (formerly draw.io).
  - **Content:** Draw a large box for the Azure VNet, containing three smaller boxes for the VMs (DEV/Splunk, DC, VICTIM). Use arrows to show WinRM and Splunk Forwarder connections.

**Table 3.1: Sample of Curated Primitives**
  - **Goal:** Show the structure of a fully curated primitive.
  - **Tool:** Microsoft Word's table editor or Markdown.
  - **Content:** Columns: "Primitive ID", "Primitive Command", "Sample Telemetry Rule". Select 4-5 diverse primitives from `primitives_library.json`.

**Figure 4.1: PowerShell-Sentinel Data Factory Pipeline**
  - **Goal:** Create a flowchart of the `main_data_factory.py` logic.
  - **Tool:** diagrams.net.
  - **Content:** Use standard flowchart shapes to represent the process of selecting, obfuscating, executing, and validating primitives in a loop.

**Table 4.1: Multi-Stage QA Framework**
  - **Goal:** Summarize the QA strategy.
  - **Tool:** Microsoft Word's table editor or Markdown.
  - **Content:** Columns: "QA Stage" and "Purpose". Rows for Obfuscator Unit Testing, Live Execution Validation, and Pipeline Integration Testing.

**Figure 5.2: Sentinel Toolkit CLI in Action**
  - **Goal:** Show the final user-facing application.
  - **Tool:** Screenshot tool.
  - **Content:** Capture a clean screenshot of the terminal showing the "Analyze" feature with an obfuscated command and the final, well-formatted JSON output.
"""

# --- Core Logic Functions ---

def infer_techniques_from_prompt(prompt: str) -> Set[str]:
    """Infers obfuscation techniques from a prompt string for statistical analysis."""
    inferred_techniques = set()
    if 'powershell.exe -EncodedCommand' in prompt:
        inferred_techniques.add('obfuscate_base64')
        inferred_techniques.add('layered_technique_inside_base64')
        return inferred_techniques
    if '+' in prompt and ('Invoke-Expression' in prompt or 'iex' in prompt):
        inferred_techniques.add('obfuscate_concat')
    if '$' in prompt and '=' in prompt and ';' in prompt:
        inferred_techniques.add('obfuscate_variables')
    if '-f' in prompt and "'{0}'" in prompt:
        inferred_techniques.add('obfuscate_format_operator')
    if '&([string]::new' in prompt or '&([char[]]' in prompt:
        inferred_techniques.add('obfuscate_types')
    return inferred_techniques

def save_markdown_table(filename: str, title: str, headers: list, rows: list):
    """Formats and saves a table to a Markdown file."""
    filepath = os.path.join("visuals", "tables", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"**{title}**\n\n")
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(['---'] * len(headers)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(str(item) for item in row) + " |\n")
    print(f"SUCCESS: Saved table to '{filepath}'")

def parse_evaluation_report(report_path: str) -> dict:
    """
    [DEFINITIVE FIX] Parses key metrics from the final evaluation report file
    which uses rich.Table box-drawing characters.
    """
    metrics = {}
    # This regex is designed to capture the key and value from lines like:
    # │    JSON Parse Success Rate │ 93.32% │
    pattern = re.compile(r"│\s*(.*?)\s*│\s*(.*?)\s*│")
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.match(line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    # We only care about the final, most important metrics
                    if "Rate" in key or "Accuracy" in key or "Score" in key:
                         metrics[key] = value
    except FileNotFoundError:
        print(f"WARNING: Evaluation report not found at '{report_path}'. Table 5.2 will be a placeholder.")
    return metrics

# --- Table Generation Functions ---

def generate_chapter_4_visuals(dataset: list, clean_dataset: list, log_lines: list):
    """Analyzes the data factory's output to quantify its performance and patterns."""
    print("\n>>> Generating visuals for Chapter 4...")
    
    total_failures = len(log_lines)
    total_successes_raw = len(dataset)
    total_successes_clean = len(clean_dataset)
    total_attempts = total_successes_raw + total_failures
    success_rate_clean = (total_successes_clean / total_attempts) * 100 if total_attempts > 0 else 0

    save_markdown_table(
        "table_4_2_run_summary.md", "Table 4.2: Data Generation Run Summary",
        headers=["Metric", "Value"],
        rows=[
            ["Target Pair Count", f"{10000:,}"],
            ["Total Raw Pairs Generated", f"{total_successes_raw:,}"],
            ["Unique (De-duplicated) Pairs Generated", f"{total_successes_clean:,}"],
            ["Failed Pairs (Execution Errors)", f"{total_failures:,}"],
            ["Total Generation Attempts", f"{total_attempts:,}"],
            ["Unique Generation Success Rate (%)", f"{success_rate_clean:.2f}%"]
        ]
    )

    primitive_failures, technique_failures = Counter(), Counter()
    for line in log_lines:
        try:
            record = json.loads(line)
            primitive_failures.update([record.get('primitive_id', 'Unknown')])
            technique_failures.update(record.get('obfuscation_chain', [])),
        except json.JSONDecodeError: continue

    save_markdown_table(
        "table_4_3_primitive_failures.md", "Table 4.3: Most Frequent Primitive Failures",
        headers=["Primitive ID", "Failure Count", "% of Total Failures"],
        rows=[[prim_id, count, f"{(count / total_failures) * 100:.2f}%"] for prim_id, count in primitive_failures.most_common(5)]
    )
    
    save_markdown_table(
        "table_4_4_technique_failures.md", "Table 4.4: Obfuscation Technique Failure Frequency",
        headers=["Technique", "Failure Count"],
        rows=[[tech, f"{count:,}"] for tech, count in technique_failures.most_common()]
    )

    technique_counts = Counter()
    for pair in clean_dataset:
        technique_counts.update(infer_techniques_from_prompt(pair.get('prompt', '')))
        
    display_counts = {k: v for k, v in technique_counts.items() if k != 'layered_technique_inside_base64'}
    save_markdown_table(
        "table_4_5_obfuscation_bias.md", "Table 4.5: Inferred Final-Layer Obfuscation Bias (on Clean Data)",
        headers=["Inferred Technique", "Occurrence Count", "Presence in Dataset (%)"],
        rows=[[tech, f"{count:,}", f"{(count / total_successes_clean) * 100:.2f}%"] for tech, count in sorted(display_counts.items(), key=lambda item: item[1], reverse=True)]
    )
    
    sample_size = 500
    base64_prompts = [p['prompt'] for p in clean_dataset if 'EncodedCommand' in p['prompt']]
    if len(base64_prompts) < sample_size: sample_size = len(base64_prompts)
    if sample_size > 0:
        sample = random.sample(base64_prompts, sample_size)
        inner_technique_counts = Counter()
        for prompt in sample:
            try:
                decoded_command = base64.b64decode(prompt.split(' ')[-1]).decode('utf-16le')
                inner_technique_counts.update(infer_techniques_from_prompt(decoded_command))
            except Exception: continue

        save_markdown_table(
            f"table_4_6_inner_variety.md", f"Table 4.6: Inferred Technique Distribution Inside a {sample_size}-Pair Sample of Clean Base64 Payloads",
            headers=["Technique", "Presence in Sample (%)"],
            rows=[[tech, f"{(count / sample_size) * 100:.2f}%"] for tech, count in inner_technique_counts.most_common()]
        )

def generate_chapter_5_visuals(eval_results_path: str, clean_dataset_path: str):
    """Generates visuals for Chapter 5."""
    print("\n>>> Generating visuals for Chapter 5...")
    
    # --- TABLE 5.1: DATASET PARTITIONING SUMMARY ---
    try:
        with open(clean_dataset_path, 'r', encoding='utf-8') as f:
            clean_dataset_len = len(json.load(f))
        train_len = int(clean_dataset_len * 0.9)
        test_len = clean_dataset_len - train_len
        rows_5_1 = [
            ["Total Unique Samples", f"{clean_dataset_len:,}"],
            ["Training Set (90%)", f"{train_len:,}"],
            ["Test Set (10%)", f"{test_len:,}"]
        ]
    except FileNotFoundError:
        rows_5_1 = [["Status", "Clean dataset file not found."]]

    save_markdown_table(
        "table_5_1_partition_summary.md", "Table 5.1: Dataset Partitioning Summary",
        headers=["Split", "Count"],
        rows=rows_5_1
    )
    
    # --- TABLE 5.2: FINAL MODEL PERFORMANCE EVALUATION ---
    final_metrics = parse_evaluation_report(eval_results_path)
    if final_metrics:
        display_metrics = [
            "JSON Parse Success Rate", "Deobfuscation Accuracy",
            "Intent F1-Score (Macro)", "MITRE TTP F1-Score (Macro)"
        ]
        rows_5_2 = [[metric, final_metrics.get(metric, "N/A")] for metric in display_metrics]
    else:
        rows_5_2 = [["Status", "Could not parse evaluation report."]]
        
    save_markdown_table(
        "table_5_2_model_performance.md", "Table 5.2: Final Model Performance Evaluation",
        headers=["Metric", "Score"],
        rows=rows_5_2
    )

    # --- TABLE 5.3: QUALITATIVE EVALUATION OF GGUF QUANTIZATION ---
    # This table is hard-coded based on the manual, qualitative analysis.
    # It is designed to be directly inserted into the dissertation narrative.
    headers_5_3 = ["Model", "Task Assessment", "Key Observation"]
    rows_5_3 = [
        ["High-Precision (f16)", "Excellent", "Gold standard. Provides correct, nuanced, and well-explained outputs."],
        ["Quantized (Q8_0)", "Excellent", "No discernible degradation in performance or reasoning ability."],
        ["Quantized (Q6_K)", "Excellent", "No discernible degradation in performance or reasoning ability."],
        ["Quantized (Q5_K_M)", "Excellent", "No discernible degradation in performance or reasoning ability."],
        ["Quantized (Q4_K_M)", "Excellent", "No discernible degradation. The optimal balance of size and performance."],
        ["Quantized (Q3_K_M)", "Good", "Functionally correct but with minor losses in explanatory detail."],
        ["Quantized (Q2_K)", "FAIL", "Catastrophic failure. Produces hallucinated, non-functional code."]
    ]
    save_markdown_table(
        "table_5_3_quantization_evaluation.md", "Table 5.3: Qualitative Evaluation of GGUF Quantization Levels",
        headers=headers_5_3,
        rows=rows_5_3
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate all data-driven visuals for the dissertation.")
    parser.add_argument("--raw-dataset-file", default="data/generated/training_data_v0.json")
    parser.add_argument("--clean-dataset-file", default="data/generated/training_data_v0_clean.json")
    parser.add_argument("--log-file", default="data/generated/failures.log")
    # Corrected default path to reflect final workflow
    parser.add_argument("--eval-results-path", default="dist/final_evaluation_report.md") 
    args = parser.parse_args()

    # Create parent directories
    os.makedirs(os.path.join("visuals", "tables"), exist_ok=True)
    os.makedirs(os.path.join("visuals", "figures"), exist_ok=True)
    
    try:
        with open(args.raw_dataset_file, 'r', encoding='utf-8') as f:
            raw_dataset = json.load(f)
        with open(args.clean_dataset_file, 'r', encoding='utf-8') as f:
            clean_dataset = json.load(f)
        with open(args.log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"FATAL: Could not load required data/log files. Error: {e}")
        print("HINT: Have you run the main data factory and the data prep scripts first?")
        exit()

    generate_chapter_4_visuals(raw_dataset, clean_dataset, log_lines)
    generate_chapter_5_visuals(args.eval_results_path, args.clean_dataset_file)

    print("\n[bold green]Visuals generation complete.[/bold green]")
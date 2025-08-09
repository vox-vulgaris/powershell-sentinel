# scripts/generate_dissertation_visuals.py

import json
import base64
import random
import os
import argparse
from collections import Counter
from typing import Set
import matplotlib.pyplot as plt

# --- Script Overview and Workflow Instructions ---
"""
This script is the master engine and central checklist for generating all visuals
for the dissertation. It automates the creation of all data-driven tables and
figures and provides detailed instructions for all manually created visuals.

--------------------------------------------------------------------------------
WORKFLOW INSTRUCTIONS FOR MICROSOFT WORD
--------------------------------------------------------------------------------

**Step 1: Run This Script**
   - Execute from the terminal: `python scripts/generate_dissertation_visuals.py`
   - This will create a `visuals/` directory in your project root. Inside, you
     will find two subdirectories:
       - `visuals/tables/`: Contains each automated table as a separate .md (Markdown) file.
       - `visuals/figures/`: Contains each automated figure as a separate .png image file.

**Step 2: Inserting AUTOMATED Tables into Word**
   1. Open the relevant Markdown file (e.g., `visuals/tables/table_4_2.md`) in any
      plain text editor (like VS Code or Notepad).
   2. Highlight and copy the entire contents of the file.
   3. In your Word document, place the cursor at the desired location.
   4. Right-click and under "Paste Options," select "Keep Text Only".
   5. Highlight the text you just pasted in Word.
   6. Go to the "Insert" tab -> "Table" -> "Convert Text to Table...".
   7. In the dialog box, ensure "Separate text at" is set to "Other" and
      type the pipe symbol (|) in the box. Click OK.
   8. The text will be converted into a native Word table, ready for styling.

**Step 3: Inserting AUTOMATED Figures into Word**
   1. In your Word document, place the cursor at the desired location.
   2. Go to the "Insert" tab -> "Pictures" -> "This Device...".
   3. Navigate to the `visuals/figures/` directory and select the image
      file (e.g., `figure_5_1.png`).
   4. Use Word's tools to add a caption.

**Step 4: Creating and Inserting MANUAL Visuals**
   - Follow the detailed instructions for each manual visual in the
     "MANUAL VISUALS GUIDE" section of this script's comments below.

--------------------------------------------------------------------------------
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
#   - [AUTOMATED] Table 4.5: Inferred Final-Layer Obfuscation Bias
#   - [AUTOMATED] Table 4.6: Inferred Inner Variety in Base64 Payloads

# CHAPTER 5: Model Fine-Tuning, Evaluation and Delivery
#   - [AUTOMATED] Table 5.1: Dataset Partitioning Summary
#   - [AUTOMATED] Figure 5.1: Prompt Engineering Experiment Results
#   - [AUTOMATED] Table 5.2: Final Model Performance Evaluation
#   - [MANUAL]   Figure 5.2: Sentinel Toolkit CLI in Action

# ==============================================================================
# --- MANUAL VISUALS GUIDE ---
# ==============================================================================
"""
**Figure 3.1: Lab Architecture Diagram**
  - **Goal:** Visually represent the three-VM lab environment.
  - **Tool:** diagrams.net (formerly draw.io) is highly recommended.
  - **Content:**
    - Draw a large box representing the "Azure Virtual Network".
    - Inside, draw three smaller boxes for the VMs: "PS-DEV-01 (Splunk, Code)",
      "PS-DC-01 (Domain Controller)", and "PS-VICTIM-01 (Execution Host)".
    - Use arrows to show key interactions:
      - Python on DEV -> WinRM on VICTIM
      - Log Forwarder on VICTIM/DC -> Splunk (TCP 9997) on DEV
  - **Format:** Export as a high-resolution PNG or SVG.

**Table 3.1: Sample of Curated Primitives**
  - **Goal:** Show the structure of a fully curated primitive after the initial
           human-in-the-loop process.
  - **Tool:** Microsoft Word's table editor or Markdown.
  - **Content:**
    - Create a table with columns: "Primitive ID", "Primitive Command", "Sample Telemetry Rule".
    - Select 4-5 diverse and interesting primitives from your final
      `primitives_library.json`. Pick ones with clear, representative telemetry.
    - For the "Sample Telemetry Rule" column, pick just one clear rule for brevity.

**Figure 4.1: PowerShell-Sentinel Data Factory Pipeline**
  - **Goal:** Create a flowchart of the `main_data_factory.py` logic.
  - **Tool:** diagrams.net.
  - **Content (use standard flowchart shapes):**
    - Parallelogram (Data I/O): "Input: primitives_library.json"
    - Rectangle (Process): "Select Next Primitive (Round-Robin)"
    - Rectangle (Process): "Apply Layered Obfuscation"
    - Rectangle (Process): "Execute Command via Lab Connector"
    - Diamond (Decision): "Execution Successful? (Return Code == 0)"
    - If Yes -> Rectangle (Process): "Create TrainingPair Object"
    - If No -> Rectangle (Process): "Log Failure to failures.log"
    - Arrow back to "Select Next Primitive".

**Table 4.1: Multi-Stage QA Framework**
  - **Goal:** Summarize your comprehensive QA strategy.
  - **Tool:** Microsoft Word's table editor or Markdown.
  - **Content:**
    - Create a table with two columns: "QA Stage" and "Purpose".
    - Rows should be:
      1. "Obfuscator Unit Testing (`test_obfuscator.py`)" -> "Validates functional equivalency of obfuscated commands against a known 'Canary Cage' of primitives."
      2. "Live Execution Validation (`main_data_factory.py`)" -> "Ensures every generated pair is executable in the live lab by checking for a zero return code."
      3. "Pipeline Integration Testing (`test_integration_*.py`)" -> "Validates the stability, timeout handling, and resilience of the entire pipeline under high-volume and worst-case scenarios."

**Figure 5.2: Sentinel Toolkit CLI in Action**
  - **Goal:** Show the final user-facing application in action.
  - **Tool:** Screenshot tool (e.g., Windows Snip & Sketch).
  - **Content:**
    - Run `sentinel_toolkit.py`.
    - Use the "Analyze" feature on a moderately complex obfuscated command.
    - Capture a clean screenshot of the terminal showing the input command and the
      well-formatted, structured JSON output from the model.
    - (Optional) Use a tool to add a border or shadow to the screenshot for a
      more professional look.
"""

# --- Core Logic Functions ---

def infer_techniques_from_prompt(prompt: str) -> Set[str]:
    """Infers obfuscation techniques from a prompt string."""
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
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"**{title}**\n\n")
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(['---'] * len(headers)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(str(item) for item in row) + " |\n")
    print(f"SUCCESS: Saved table to '{filepath}'")

# --- Table Generation Functions ---

def generate_chapter_4_visuals(dataset: list, log_lines: list):
    """
    BRIEF: Analyzes the data factory's output to quantify its performance,
    failure patterns, and the composition of the final dataset.
    """
    print("\n>>> Generating visuals for Chapter 4...")
    
    total_failures = len(log_lines)
    total_successes = len(dataset)
    total_attempts = total_successes + total_failures
    success_rate = (total_successes / total_attempts) * 100 if total_attempts > 0 else 0

    save_markdown_table(
        "table_4_2_run_summary.md", "Table 4.2: Data Generation Run Summary",
        headers=["Metric", "Value"],
        rows=[
            ["Target Pair Count", "10,000"],
            ["Successful Pairs Generated", f"{total_successes}"],
            ["Failed Pairs (Execution Errors)", f"{total_failures}"],
            ["Total Generation Attempts", f"{total_attempts}"],
            ["Generation Success Rate (%)", f"{success_rate:.2f}%"]
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
        rows=[[tech, count] for tech, count in technique_failures.most_common()]
    )

    technique_counts = Counter()
    for pair in dataset:
        technique_counts.update(infer_techniques_from_prompt(pair.get('prompt', '')))
        
    display_counts = {k: v for k, v in technique_counts.items() if k != 'layered_technique_inside_base64'}
    save_markdown_table(
        "table_4_5_obfuscation_bias.md", "Table 4.5: Inferred Final-Layer Obfuscation Bias",
        headers=["Inferred Technique", "Occurrence Count", "Presence in Dataset (%)"],
        rows=[[tech, count, f"{(count / total_successes) * 100:.2f}%"] for tech, count in sorted(display_counts.items(), key=lambda item: item[1], reverse=True)]
    )
    
    sample_size = 500
    base64_prompts = [p['prompt'] for p in dataset if 'EncodedCommand' in p['prompt']]
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
            f"table_4_6_inner_variety.md", f"Table 4.6: Inferred Technique Distribution Inside a {sample_size}-Pair Sample of Base64 Payloads",
            headers=["Technique", "Presence in Sample (%)"],
            rows=[[tech, f"{(count / sample_size) * 100:.2f}%"] for tech, count in inner_technique_counts.most_common()]
        )

def generate_chapter_5_visuals(partitioned_data_dir: str, eval_results_path: str, prompt_results_path: str):
    """
    BRIEF: Generates visuals for Chapter 5, summarizing dataset partitioning,
    prompt engineering results, and final model performance metrics.
    """
    print("\n>>> Generating visuals for Chapter 5...")

    # Table 5.1: Dataset Partitioning Summary
    # TODO: This logic will be implemented after Conversation 5.
    save_markdown_table(
        "table_5_1_partition_summary.md", "Table 5.1: Dataset Partitioning Summary",
        headers=["Split", "Count"],
        rows=[
            ["Total Samples", "10000 (Placeholder)"],
            ["Training Set (90%)", "9000 (Placeholder)"],
            ["Test Set (10%)", "1000 (Placeholder)"]
        ]
    )
    
    # Figure 5.1: Prompt Engineering Experiment Results
    # [DEFINITIVE FIX] This section now only prints a status message and does NOT generate a file.
    # It serves as a clear "to-do" for when the prompt engineering results are available.
    print("\n--- [PLACEHOLDER] Figure 5.1: Prompt Engineering Experiment Results ---")
    print("INFO: This figure will be a bar chart generated from the output of the prompt engineering experiments.")
    print("ACTION: After running the prompt experiments (Conversation 6), uncomment and adapt the plotting")
    print("        logic in this script to read your results file and save the figure.")
    # try:
    #     with open(prompt_results_path, 'r') as f: results = json.load(f)
    #     templates = list(results.keys())
    #     parse_rates = [res['json_parse_success_rate'] for res in results.values()]
    #     plt.figure(figsize=(8, 5)); plt.bar(templates, parse_rates, color='#1E4970'); plt.ylabel('JSON Parse Success Rate (%)'); plt.title('Figure 5.1'); plt.ylim(0, 100)
    #     figure_path = os.path.join("visuals", "figures", "figure_5_1_prompt_results.png"); plt.savefig(figure_path)
    #     print(f"SUCCESS: Figure saved to '{figure_path}'")
    # except FileNotFoundError:
    #     print(f"SKIPPING: Prompt results file not found at '{prompt_results_path}'.")
    
    # Table 5.2: Final Model Performance Evaluation
    # TODO: This logic will be implemented after Conversation 6.
    save_markdown_table(
        "table_5_2_model_performance.md", "Table 5.2: Final Model Performance Evaluation",
        headers=["Metric", "Score"],
        rows=[
            ["JSON Parse Success Rate", "XX.XX% (Placeholder)"],
            ["F1-Score (Intent)", "0.XX (Placeholder)"],
            ["F1-Score (MITRE TTPs)", "0.XX (Placeholder)"]
        ]
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate all data-driven visuals for the dissertation.")
    parser.add_argument("--dataset-file", default="data/generated/training_data_v0.json")
    parser.add_argument("--log-file", default="data/generated/failures.log")
    parser.add_argument("--partitioned-data-dir", default="data/sets/")
    parser.add_argument("--eval-results-path", default="results/final_evaluation.json")
    parser.add_argument("--prompt-results-path", default="results/prompt_experiments.json")
    args = parser.parse_args()

    os.makedirs(os.path.join("visuals", "tables"), exist_ok=True)
    os.makedirs(os.path.join("visuals", "figures"), exist_ok=True)
    
    try:
        with open(args.dataset_file, 'r', encoding='utf-8') as f:
            full_dataset = json.load(f)
        with open(args.log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"FATAL: Could not load required data/log files. Error: {e}")
        exit()

    generate_chapter_4_visuals(full_dataset, log_lines)
    generate_chapter_5_visuals(args.partitioned_data_dir, args.eval_results_path, args.prompt_results_path)

    print("\n[bold green]Visuals generation complete.[/bold green]")
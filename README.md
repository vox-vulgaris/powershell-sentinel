# PowerShell-Sentinel: A Data-Centric Approach to Obfuscated Command Analysis

## Overview

This project engineers and validates a data-centric methodology for fine-tuning a Large Language Model (LLM) to perform structured analysis of obfuscated PowerShell commands. The core research contribution is the **"PowerShell-Sentinel Data Factory,"** a software pipeline for generating specialized, high-quality training data. This data is then used to fine-tune a `Gemma-2B` model, which powers a practical command-line analysis tool.

The entire workflow—from lab setup and data curation to model training and evaluation—is designed to be a transparent, repeatable, and rigorous process, forming the basis of a dissertation on applied AI for cybersecurity.

---

## Features (sentinel_toolkit v0)

The final deliverable is a standalone, interactive command-line tool with three primary functions:

*   **[1] Analyze Obfuscated Command:** The core feature. It leverages the fine-tuned LLM to take any obfuscated PowerShell command, deobfuscate it, and predict its intent, associated MITRE ATT&CK TTPs, and the likely telemetry signals it would generate. Includes an intelligent retry mechanism for robust performance.

*   **[2] Threat Intel Lookup:** A high-speed, deterministic lookup tool. It allows a user to input a *clean*, known PowerShell command (e.g., `Invoke-Kerberoast`) and instantly retrieve the expert-curated `intent`, `TTPs`, and `telemetry_rules` from the project's internal knowledge base.

*   **[3] About & Performance:** Displays static information about the tool, the base model used, and the final performance metrics (e.g., JSON Parse Success Rate, F1-Scores) as determined by the rigorous evaluation against a held-out test set.

---

## Setup & Installation

### For Development

This is for running the data factory, training scripts, or modifying the tool.

1.  **Clone the repository:**
    `git clone https://github.com/YourUsername/powershell-sentinel.git`
2.  **Navigate to the project directory:**
    `cd powershell-sentinel`
3.  **Create and activate a Python virtual environment:**
    *   `python -m venv venv`
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`
4.  **Install dependencies:**
    `pip install -r requirements.txt`

### Running the Packaged Tool (End-User)

This is for users who only want to use the final application.

1.  Download `sentinel_toolkit.exe` (for Windows) or `sentinel_toolkit` (for macOS/Linux) from the project's releases page.
2.  Open a terminal (PowerShell, Command Prompt, bash, etc.).
3.  Navigate to the directory where you downloaded the file.
4.  Run the tool:
    *   **Windows:** `.\sentinel_toolkit.exe`
    *   **macOS/Linux:** First, make it executable with `chmod +x ./sentinel_toolkit`, then run it with `./sentinel_toolkit`.

---

## Project & Data Directory Structure

The project follows a structured layout to separate source code, data, scripts, and tests.

### `/powershell_sentinel/`
The main Python source code for the application and its modules.

### `/data/`
This directory is organized to separate raw source data, intermediate artifacts, and final generated datasets.

*   #### `/data/source/`
    This directory contains the hand-curated, ground-truth data for the project.

    *   **`primitives_library.json`**: This is the master knowledge base. It is a list of "primitive" PowerShell commands representing various adversarial techniques. Each entry is a JSON object with a specific, required schema. This file is the primary input for the data factory.
        *   **Schema:** `primitive_id`, `primitive_command`, `intent` (list), `mitre_ttps` (list), `telemetry_rules` (list of objects). The `telemetry_rules` field starts empty and is populated by the `primitives_manager.py` tool.

    *   **`mitre_ttp_library.json`**: A project-specific lookup file that provides canonical data (name and tactic) for every MITRE ATT&CK technique referenced in `primitives_library.json`. This file is not an exhaustive database of the entire ATT&CK framework; instead, it is curated iteratively. As new primitives are developed, any new TTPs they reference are added here. This ensures the `primitives_manager.py` tool has a consistent and validated source for populating its selection menus.

*   #### `/data/interim/`
    Holds temporary data generated during the curation process, such as the `delta_logs` for each primitive.

*   #### `/data/generated/`
    Contains the final output of the `main_data_factory.py` script.
    *   **`training_data_v0.json`**: The complete, large-scale dataset of obfuscated/deobfuscated pairs before partitioning.
    *   **`failures.log`**: A critical log file that records any obfuscated command that failed execution in the lab, providing a feedback loop for improving the obfuscation engine.

*   #### `/data/sets/`
    The final, ML-ready datasets after partitioning.
    *   **`training_set_v0.json`**: The portion of the data used to fine-tune the model (e.g., 90%).
    *   **`test_set_v0.json`**: The "locked," held-out portion of the data used for final, unbiased model evaluation (e.g., 10%).

### `/scripts/`
Contains utility and one-time experiment scripts, like the `prompt_engineering` suite and the `partition_dataset.py` script.

### `/tests/`
Contains all unit and integration tests for the project.

*   #### `/tests/test_data/`
    This subdirectory holds small, specific data files required for running tests.

    *   **`expert_ground_truth.json`**: This file acts as the definitive "answer key" for the data curation integration tests. It contains a small, representative subset of primitives where the `telemetry_rules`, `intent`, and `mitre_ttps` have been meticulously hand-curated by a human domain expert. The automated curation pipeline's output is compared against this file to calculate an F1-score for accuracy.

    *   **`test_cli_lookup.json`**: A small, mock version of `primitives_library.json` used to unit test the non-LLM "Threat Intel Lookup" feature of the final `sentinel_toolkit` CLI, ensuring it can correctly parse the file and retrieve data without needing the full dataset.
# PowerShell-Sentinel: Practitioner Review Package

Thank you for your time and expertise in helping to validate this research project.

**Project Goal:** The goal is to create a high-quality dataset for fine-tuning a Large Language Model to analyze obfuscated PowerShell commands. Your feedback is crucial for validating the quality of our data curation process.

This package contains several folders, each named with a unique `primitive_id` (e.g., `PS-007`). Inside each folder, you will find:
-   `command.txt`: The clean, deobfuscated PowerShell command that was executed.
-   `context.txt`: The `intent` and `MITRE ATT&CK TTPs` we have assigned to this command.
-   `delta_logs.json`: A file containing ALL the raw log events that were generated *only* when this command was run in a clean lab. This is noisy data.

---

### Your Tasks

You have two main tasks.

#### Task 1: Identify "Golden Signals" (for each folder)

Your primary task is to act as an expert analyst and identify the most important log events from the noisy `delta_logs.json`.

**For each folder (e.g., `PS-007`, `PS-011`, etc.):**

1.  Review the `command.txt` and `context.txt` to understand what the command does.
2.  Open the noisy `delta_logs.json` file.
3.  From the list of log objects, identify the **2 to 5 "golden signals"**—the log events that you believe are the most critical and definitive evidence that this specific command was executed.
4.  Create a **new file** in that same folder named **`expert_golden_signals.json`**.
5.  **Copy and paste** the full JSON objects of the golden signals you selected into this new file. The result should be a valid JSON list `[ {log1}, {log2}, ... ]`.

#### Task 2: Review Metadata (one-time task)

This is a quick sanity check of our manual curation.

1.  As you go through the folders, if you disagree with any of the `intent` or `mitre_ttps` listed in a `context.txt` file, please make a note of it.
2.  Create a **single, top-level text file** named **`metadata_review.txt`**.
3.  In this file, list the `primitive_id` and any suggested changes. For example:
    ```text
    PS-008: Suggest adding TTP T1592.002 (Gather Victim Host Information). Intent seems correct.
    PS-015: Intent "Local Groups" is too vague, suggest "Permission Groups Discovery: Local Groups". TTP is correct.
    ```
    If you agree with everything, you can simply write "All metadata looks correct."

---

### Final Step

Once you have completed both tasks, please re-zip the entire `practitioner_package` directory (which will now contain your new files) and send it back.

Thank you again for your invaluable contribution.

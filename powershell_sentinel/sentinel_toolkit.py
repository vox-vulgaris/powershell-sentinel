# Phase 5: Final Deliverable & Documentation
# Index: [18]
#
# This is the final, user-facing v0 MVP CLI application. It is the main entry
# point for the end-user and packages the project's capabilities into a simple,
# interactive tool.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Menu: Must be a menu-driven application using a modern CLI library like `rich`.
#    v0 MVP requires [1] Analyze Obfuscated Command, [2] Threat Intel Lookup, and [3] About/Performance.
# 2. Analyze Feature (LLM-Powered):
#    - Prompts the user for an obfuscated command string.
#    - Must use the IDENTICAL winning prompt template for model inference.
#    - Robustness: Must implement an intelligent retry loop (max 3 attempts) that
#      retries on `pydantic.ValidationError`, ensuring only schema-compliant output is accepted.
#    - Must provide clean, formatted table-based output for readability upon success.
#    - Must provide a graceful error message, including the raw model output, upon failure.
# 3. Threat Intel Lookup Feature (Non-LLM):
#    - Must load and validate the `primitives_library.json` into Pydantic models on startup.
#    - Must perform a simple, high-speed, case-insensitive lookup on these validated objects.
# 4. About/Performance Feature:
#    - Must display the static performance metrics from the final evaluation report.

# powershell_sentinel/sentinel_toolkit.py

import json
import time
import argparse
from typing import List, Dict, Union

# Use llama_cpp for GGUF model inference
from llama_cpp import Llama
from pydantic import ValidationError

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

# Import the Pydantic models that define the data structures
from powershell_sentinel.models import Primitive, LLMResponse, Analysis, TelemetryRule

# The prompt template is the exact format the model was fine-tuned on.
# Consistency is critical for reliable performance.
WINNING_PROMPT_TEMPLATE = """### INSTRUCTION:
You are a specialized cybersecurity assistant focused on PowerShell deobfuscation and analysis.
Your task is to analyze the provided obfuscated PowerShell command and return a structured JSON object.
The JSON object must conform to the following schema:
- `deobfuscated_command`: A string containing the cleaned, deobfuscated version of the original command.
- `analysis`: An object containing:
  - `intent`: A list of strings describing the command's purpose (e.g., "Process Discovery").
  - `mitre_ttps`: A list of strings with the corresponding MITRE ATT&CK Technique IDs (e.g., "T1057").
  - `telemetry_signature`: A list of objects, where each object represents a predicted log event with `source`, `event_id`, and `details`.

Analyze the following PowerShell command:
{prompt}

### RESPONSE:
"""

# --- Constants ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.5
PRIMITIVES_DB_PATH = "data/source/primitives_library.json"


class SentinelToolkit:
    """The main user-facing CLI application."""

    def __init__(self, model_path: str):
        self.console = Console()
        self.model = None

        with self.console.status("Initializing toolkit... Loading model...", spinner="dots"):
            try:
                # Load the GGUF model using llama-cpp-python for efficient CPU inference
                self.model = Llama(model_path=model_path, verbose=False, n_ctx=2048)
            except Exception as e:
                self.console.print(f"[bold red]Fatal Error: Could not load the model from path: {model_path}[/bold red]")
                self.console.print(f"[red]Details: {e}[/red]")
                exit(1)

            self.primitives_db: List[Primitive] = self._load_primitives_db()

        self.console.print(f"[green]Sentinel Toolkit Initialized. Model '{model_path}' loaded.[/green]")

    def _load_primitives_db(self) -> List[Primitive]:
        """Loads and validates the primitives library for the Threat Intel Lookup feature."""
        try:
            with open(PRIMITIVES_DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Use Pydantic to validate every entry, ensuring data integrity
            return [Primitive.model_validate(p) for p in data]
        except FileNotFoundError:
            self.console.print(f"[bold red]Error: Primitives DB not found at '{PRIMITIVES_DB_PATH}'. Lookup will not work.[/bold red]")
            return []
        except Exception as e:
            self.console.print(f"[bold red]Could not load or validate primitives DB: {e}[/bold red]")
            return []

    def _run_inference(self, prompt: str) -> str:
        """Helper function to run model inference using llama-cpp-python."""
        if not self.model:
            raise RuntimeError("Model is not loaded.")

        # Generate text using the loaded GGUF model
        output = self.model(prompt, max_tokens=1024, temperature=0.1, stop=["###"])
        raw_output_string = output['choices'][0]['text']

        return raw_output_string.strip()

    def _get_structured_analysis(self, user_prompt: str) -> Dict[str, Union[LLMResponse, str]]:
        """Calls the LLM with a retry loop, validating the output against the LLMResponse model."""
        full_prompt = WINNING_PROMPT_TEMPLATE.format(prompt=user_prompt)
        raw_llm_output_json = ""

        for attempt in range(MAX_RETRIES):
            self.console.print(f"Attempting analysis... (Attempt {attempt + 1}/{MAX_RETRIES})")
            raw_llm_output_json = self._run_inference(full_prompt)

            try:
                # The core of the retry loop: attempt to parse and validate the model's output.
                # If this fails, it raises a ValidationError, triggering the retry.
                response_model = LLMResponse.model_validate_json(raw_llm_output_json)
                self.console.print("[green]Successfully parsed and validated model output.[/green]")
                return {"success": True, "data": response_model}
            except ValidationError as e:
                self.console.print(f"[yellow]WARN: Failed to validate LLM output on attempt {attempt + 1}.[/yellow]")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

        self.console.print("[bold red]ERROR: Failed to get a valid structured response after all retries.[/bold red]")
        return {"success": False, "raw_output": raw_llm_output_json}

    def _display_analysis_report(self, response: LLMResponse):
        """Formats and prints the analysis result in clean rich tables."""
        main_table = Table(title="PowerShell Command Analysis", show_header=False)
        main_table.add_column("Field", style="cyan", no_wrap=True)
        main_table.add_column("Value", style="white")

        main_table.add_row("Deobfuscated Command", f"[bold green]{response.deobfuscated_command}[/bold green]")
        main_table.add_row("Intent", "\n".join(f"- {i.value}" for i in response.analysis.intent))
        main_table.add_row("MITRE ATT&CK TTPs", "\n".join(f"- {t.value}" for t in response.analysis.mitre_ttps))

        self.console.print(main_table)

        if response.analysis.telemetry_signature:
            telemetry_table = Table(title="Predicted Telemetry Signature", show_header=True, header_style="bold blue")
            telemetry_table.add_column("Source")
            telemetry_table.add_column("Event ID")
            telemetry_table.add_column("Details")

            for rule in response.analysis.telemetry_signature:
                telemetry_table.add_row(rule.source, str(rule.event_id), rule.details)
            self.console.print(telemetry_table)

    def _display_primitive_report(self, primitive: Primitive):
        """Formats and prints the details for a known primitive from the database."""
        # This reuses the same display logic by constructing the same Pydantic objects,
        # ensuring a consistent user experience for both LLM analysis and DB lookups.
        analysis = Analysis(
            intent=primitive.intent,
            mitre_ttps=primitive.mitre_ttps,
            telemetry_signature=primitive.telemetry_rules
        )
        response = LLMResponse(deobfuscated_command=primitive.primitive_command, analysis=analysis)
        self._display_analysis_report(response)

    def feature_analyze_command(self):
        """Handler for the 'Analyze Obfuscated Command' feature."""
        command = Prompt.ask("\n[bold cyan]Enter obfuscated PowerShell command[/bold cyan]")
        if not command.strip():
            self.console.print("[yellow]No command entered.[/yellow]")
            return

        with self.console.status("Analyzing command...", spinner="dots"):
            result = self._get_structured_analysis(command)

        if result.get('success'):
            self._display_analysis_report(result['data'])
        else:
            self.console.print("\n[bold red]--- Analysis Error ---[/bold red]")
            self.console.print("The model produced an output that could not be parsed into the required format.")
            self.console.print("\n[bold yellow]--- Raw Model Output ---[/bold yellow]")
            self.console.print(result.get('raw_output', 'No output received.'))

    def feature_threat_intel_lookup(self):
        """Handler for the 'Threat Intel Lookup' feature (non-LLM)."""
        if not self.primitives_db:
            self.console.print("[bold red]Threat Intel DB is not loaded. Cannot perform lookup.[/bold red]")
            return

        command = Prompt.ask("\n[bold cyan]Enter clean primitive command for lookup[/bold cyan]").strip()
        found_primitive = None
        for primitive in self.primitives_db:
            if primitive.primitive_command.lower() == command.lower():
                found_primitive = primitive
                break

        if found_primitive:
            self.console.print(f"\n[green]Found entry for '{command}':[/green]")
            self._display_primitive_report(found_primitive)
        else:
            self.console.print(f"\n[yellow]No entry found for '{command}' in the primitives database.[/yellow]")

    def feature_about(self):
        """Displays the About/Performance screen."""
        self.console.print("\n[bold]--- About PowerShell-Sentinel v0.1 ---[/bold]")
        self.console.print("This tool uses a fine-tuned LLM to analyze obfuscated PowerShell commands.")
        self.console.print("It is the final deliverable of a data-centric AI engineering project.")

        table = Table(title="v0 Final Model Performance Evaluation")
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Score", style="magenta")

        # These are the final performance metrics from the dissertation.
        table.add_row("JSON Parse Success Rate", "93.32%")
        table.add_row("Deobfuscation Accuracy", "72.50%")
        table.add_row("Intent F1-Score (Macro)", "70.08%")
        table.add_row("MITRE TTP F1-Score (Macro)", "70.08%")

        self.console.print(table)
        self.console.print("\n[italic]Always verify results with manual analysis.[/italic]")

    def start(self):
        """The main application menu loop."""
        while True:
            self.console.print("\n" + "─" * 50, style="bold magenta")
            self.console.print("  PowerShell Sentinel Toolkit Menu", style="bold magenta")
            self.console.print("─" * 50, style="bold magenta")
                        
            self.console.print("\n[1] Analyze Obfuscated Command")
            self.console.print("[2] Threat Intel Lookup")
            self.console.print("[3] About/Performance")
            self.console.print("[q] Quit")
            
            choice = Prompt.ask(
                "\nChoose an option",
                choices=["1", "2", "3", "q"],
                show_default=False 
            )            

            if choice == '1':
                self.feature_analyze_command()
            elif choice == '2':
                self.feature_threat_intel_lookup()
            elif choice == '3':
                self.feature_about()
            elif choice.lower() == 'q':
                self.console.print("Exiting.")
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="PowerShell Sentinel Analysis Toolkit. An LLM-driven tool for deobfuscating PowerShell commands.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Path to the GGUF-formatted fine-tuned model file."
    )
    args = parser.parse_args()

    toolkit = SentinelToolkit(model_path=args.model)
    toolkit.start()
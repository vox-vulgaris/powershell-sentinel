# Phase 2: Data Factory - Curation Tooling
# Index: [8]
#
# This file is the main user-facing tool for managing the primitives dataset.
# It's an interactive command-line interface (CLI) that orchestrates the
# modules developed in this phase (snapshot_differ, recommendation_engine, etc.)
# into a coherent, step-by-step workflow for the user.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Main Menu: Must offer options to [1] Manage a Dataset, [2] Re-calculate Global Statistics, and [q] Quit.
# 2. Dataset Workflow Menu: Must provide [1] Add/Edit a Primitive, [2] Run BATCH Telemetry Discovery, [3] Run BATCH Telemetry Curation.
# 3. Validated TTP Entry: The Add/Edit workflow must use `mitre_ttp_library.json` for validated user input.
# 4. BATCH Telemetry Discovery:
#    - Must iterate through all primitives in the library.
#    - For each, it will use `lab_connector.py` to run a "before" log query, execute the command, and run an "after" log query.
#    - It will then call `snapshot_differ.py` to get the `delta_logs`.
#    - It must save these `delta_logs` to a corresponding file in `data/interim/delta_logs/`.
#    - Must prompt the user for confirmation if `delta_logs` for a primitive already exist.
# 5. BATCH Telemetry Curation:
#    - Must offer "Interactive" and "Automated" modes.
#    - It will load the `delta_logs` for each primitive.
#    - It will call `recommendation_engine.py` to get recommendations.
#    - In Interactive mode, it presents the recommendations and prompts the user for a y/n/manual selection.
#    - In Automated mode, it accepts any recommendations that meet a predefined confidence threshold.
#    - After selection, it calls `rule_formatter.py` to format the selections.
#    - Finally, it updates the `telemetry_rules` field for that primitive in `primitives_library.json` and saves the file.

import json
# TODO: Import all the necessary modules
# from .lab_connector import LabConnection
# from .modules import snapshot_differ, recommendation_engine, rule_formatter, statistics_calculator

class PrimitivesManager:
    """An interactive CLI for managing and curating the primitives knowledge base."""

    def __init__(self, primitives_path, mitre_path, deltas_path):
        self.primitives_path = primitives_path
        self.mitre_path = mitre_path
        self.deltas_path = deltas_path
        # self.lab = LabConnection()
        # self.primitives = self._load_json(self.primitives_path)
        # self.mitre_ttps = self._load_json(self.mitre_path)
        print("PowerShell-Sentinel Primitives Manager Initialized.")

    def _load_json(self, path):
        # TODO: Implement with error handling
        pass

    def _save_json(self, path, data):
        # TODO: Implement
        pass

    def run_telemetry_discovery(self):
        """Orchestrates the BATCH Telemetry Discovery workflow."""
        # TODO: Implement the full workflow described in the requirements.
        print("Starting BATCH Telemetry Discovery...")
        # For each primitive in self.primitives:
        #   - Check if delta_log exists, ask for overwrite.
        #   - before_logs = self.lab.query_splunk(...)
        #   - self.lab.run_remote_powershell(primitive['primitive_command'])
        #   - after_logs = self.lab.query_splunk(...)
        #   - delta = snapshot_differ.get_delta_logs(before_logs, after_logs)
        #   - self._save_json(f"{self.deltas_path}/{primitive['primitive_id']}.json", delta)
        print("BATCH Telemetry Discovery Complete.")


    def run_telemetry_curation(self):
        """Orchestrates the BATCH Telemetry Curation workflow."""
        # TODO: Implement the full workflow with Interactive/Automated modes.
        print("Starting BATCH Telemetry Curation...")
        # For each primitive in self.primitives:
        #   - delta_logs = self._load_json(...)
        #   - recommendations = recommendation_engine.get_recommendations(...)
        #   - selected_logs = self._prompt_user_for_selection(recommendations)
        #   - formatted = rule_formatter.format_rules(selected_logs)
        #   - primitive['telemetry_rules'] = formatted
        # self._save_json(self.primitives_path, self.primitives)
        print("BATCH Telemetry Curation Complete.")

    def start(self):
        """The main entry point and loop for the CLI."""
        # TODO: Implement the main menu loop.
        print("Welcome to the Primitives Manager.")
        # while True: display menu, get input, call methods.


if __name__ == '__main__':
    # This allows running the manager directly.
    # manager = PrimitivesManager(...)
    # manager.start()
    pass
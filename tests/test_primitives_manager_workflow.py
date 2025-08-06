# tests/test_primitives_manager_workflow.py
# Phase 3: The Curation Controller, Dataset Expansion & Validation
# Index: [8]
#
# This is an integration test for the PrimitivesManager CLI. It validates all
# major end-to-end workflows, including adding new primitives, discovering
# telemetry from a mocked lab, and curating telemetry with the interactive parser.
#
# REQUIREMENTS:
# 1. Test the `_add_primitive`, `run_telemetry_discovery`, and `run_telemetry_curation` methods.
# 2. Use a temporary file system to ensure tests are isolated and clean.
# 3. Use `unittest.mock.patch` to simulate user input and external dependencies (the lab).
# 4. Assert that all file system artifacts and in-memory objects are correctly modified.

import unittest
import json
import tempfile
import os
import shutil
import zipfile
from unittest.mock import patch, MagicMock

from powershell_sentinel.primitives_manager import PrimitivesManager
from powershell_sentinel.models import SplunkLogEvent, TelemetryRule, IntentEnum, MitreTTPEnum, ParsingRule

class TestPrimitivesManagerWorkflows(unittest.TestCase):

    def setUp(self):
        """Create a temporary file system and mock data for a clean test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.primitives_path = os.path.join(self.temp_dir.name, "primitives.json")
        self.parsing_rules_path = os.path.join(self.temp_dir.name, "parsing_rules.json")
        self.deltas_path = os.path.join(self.temp_dir.name, "deltas")
        self.mitre_path = os.path.join(self.temp_dir.name, "mitre.json")
        self.parsing_logs_path = os.path.join(self.temp_dir.name, "parsing_logs")
        self.curating_logs_path = os.path.join(self.temp_dir.name, "curating_logs")
        
        os.makedirs(self.deltas_path)
        os.makedirs(self.parsing_logs_path)
        os.makedirs(self.curating_logs_path)

        with open(self.primitives_path, 'w') as f:
            json.dump([
                {"primitive_id": "PS-001", "primitive_command": "test", "intent": ["Process Discovery"], "mitre_ttps": ["T1057"], "telemetry_rules": []},
                {"primitive_id": "PS-002", "primitive_command": "test2", "intent": ["Process Discovery"], "mitre_ttps": ["T1057"], "telemetry_rules": [{"source": "s", "event_id": 1, "details": "d"}]}
            ], f)
        
        with open(self.parsing_rules_path, 'w') as f:
            json.dump([], f)
        
        with open(self.mitre_path, 'w') as f:
            json.dump({
                "T1049": {"name": "System Network Connections Discovery"},
                "T1057": {"name": "Process Discovery"}
            }, f)

    def tearDown(self):
        """Clean up the temporary directory and files after the test."""
        self.temp_dir.cleanup()
        
    def _get_manager_instance(self):
        """Helper to create a manager instance with the correct temp paths."""
        return PrimitivesManager(
            primitives_path=self.primitives_path,
            parsing_rules_path=self.parsing_rules_path,
            deltas_path=self.deltas_path,
            mitre_lib_path=self.mitre_path,
            parsing_logs_path=self.parsing_logs_path,
            curating_logs_path=self.curating_logs_path
        )

    @patch('rich.prompt.Prompt.ask')
    @patch('powershell_sentinel.primitives_manager.LabConnection')
    def test_add_primitive_workflow(self, mock_lab_connection, mock_prompt_ask):
        """Tests the interactive workflow for adding a new primitive."""
        mock_prompt_ask.side_effect = [
            "Get-NetTCPConnection",
            "11",
            "1",
        ]
        manager = self._get_manager_instance()
        self.assertEqual(len(manager.primitives), 2)
        manager._add_primitive()
        with open(self.primitives_path, 'r') as f:
            saved_primitives = json.load(f)
        self.assertEqual(len(saved_primitives), 3)
        self.assertEqual(saved_primitives[2]['primitive_id'], "PS-003")
        self.assertEqual(saved_primitives[2]['primitive_command'], "Get-NetTCPConnection")
        self.assertEqual(saved_primitives[2]['mitre_ttps'], ["T1049"])

    @patch('rich.prompt.Confirm.ask', return_value=True)
    @patch('powershell_sentinel.primitives_manager.LabConnection')
    def test_telemetry_discovery_individual_mode(self, mock_lab_connection, mock_confirm):
        """[NEW] Tests that discovery can run on a single selected primitive."""
        mock_log = SplunkLogEvent.model_validate({"_raw": "log", "_time": "t", "source": "s", "sourcetype": "st"})
        mock_lab_instance = mock_lab_connection.return_value
        mock_lab_instance.query_splunk.side_effect = [[], [mock_log]]
        manager = self._get_manager_instance()
        manager.run_telemetry_discovery(primitive_id="PS-002")
        self.assertTrue(os.path.exists(os.path.join(self.deltas_path, "PS-002.json")))

    @patch('powershell_sentinel.primitives_manager.recommendation_engine.get_recommendations')
    @patch('rich.prompt.Confirm.ask', return_value=True)
    @patch('rich.prompt.Prompt.ask')
    def test_curation_creates_new_parsing_rule(self, mock_prompt_ask, mock_confirm_ask, mock_get_recommendations):
        """Tests the curation workflow prompts for a new parsing rule when a log is unknown."""
        mock_log = SplunkLogEvent.model_validate({"_raw": 'EventCode=11 TargetFilename=secret.txt', "_time": "t", "source": "MyTestSource.evtx", "sourcetype": "Sysmon"})
        with open(os.path.join(self.deltas_path, "PS-001.json"), 'w') as f:
            json.dump([mock_log.model_dump(by_alias=True)], f)

        mock_prompt_ask.side_effect = ["Sysmon-FileCreate-Test", "11", "", "key_value", "TargetFilename", "all"]
        expected_rule = TelemetryRule(source="MyTestSource.evtx", event_id=11, details="secret.txt")
        mock_get_recommendations.return_value = [expected_rule]
        manager = self._get_manager_instance()
        manager.run_telemetry_curation()

        with open(self.parsing_rules_path, 'r') as f:
            saved_rules = json.load(f)
        self.assertEqual(len(saved_rules), 1)
        self.assertEqual(saved_rules[0]['detail_key_or_pattern'], "TargetFilename")
        self.assertEqual(saved_rules[0]['source_match'], None)
        
        updated_primitive = [p for p in manager.primitives if p.primitive_id == "PS-001"][0]
        self.assertEqual(len(updated_primitive.telemetry_rules), 1)
        self.assertEqual(updated_primitive.telemetry_rules[0].details, "secret.txt")
        
    def test_dump_unparsed_logs_and_validate_source_match_fix(self):
        """[NEW & REFACTORED] Tests the dump feature and validates the source_match bug fix."""
        rule1 = ParsingRule(rule_name="Parse-Good", event_id=1, source_match=None, extraction_method="key_value", detail_key_or_pattern="data")
        rule2 = ParsingRule(rule_name="Parse-Special", event_id=4104, source_match="SPECIAL_FLAG", extraction_method="regex", detail_key_or_pattern=r"data=(.*)")
        with open(self.parsing_rules_path, 'w') as f:
            json.dump([rule1.model_dump(mode='json'), rule2.model_dump(mode='json')], f)
            
        log_a = SplunkLogEvent.model_validate({"_raw": "EventCode=1 data=success", "source": "s1", "_time": "t1", "sourcetype": "st1"})
        log_b = SplunkLogEvent.model_validate({"_raw": "EventCode=4104 SPECIAL_FLAG data=another_success", "source": "s2", "_time": "t2", "sourcetype": "st2"})
        log_c = SplunkLogEvent.model_validate({"_raw": "EventCode=99 data=failure", "source": "s3", "_time": "t3", "sourcetype": "st3"})
        
        with open(os.path.join(self.deltas_path, "PS-001.json"), 'w') as f:
            json.dump([log_a.model_dump(by_alias=True), log_b.model_dump(by_alias=True), log_c.model_dump(by_alias=True)], f)
            
        manager = self._get_manager_instance()
        manager.dump_unparsed_logs()
        
        output_file = os.path.join(self.parsing_logs_path, "unparsed_for_review.json")
        self.assertTrue(os.path.exists(output_file))
        
        with open(output_file, 'r') as f:
            dumped_logs = json.load(f)
            
        self.assertEqual(len(dumped_logs), 1)
        self.assertEqual(dumped_logs[0]['_raw'], log_c.raw)

    def test_dump_uncurated_logs_workflow(self):
        """[NEW] Tests the feature to dump parsed logs for uncurated primitives."""
        rule = ParsingRule(rule_name="TestRule", event_id=1, extraction_method="key_value", detail_key_or_pattern="data")
        with open(self.parsing_rules_path, 'w') as f:
            json.dump([rule.model_dump(mode='json')], f)
            
        log1 = SplunkLogEvent.model_validate({"_raw": "EventCode=1 data=signal1", "source": "s1", "_time": "t1", "sourcetype": "st1"})
        log2 = SplunkLogEvent.model_validate({"_raw": "EventCode=1 data=signal2", "source": "s2", "_time": "t2", "sourcetype": "st2"})
        
        with open(os.path.join(self.deltas_path, "PS-001.json"), 'w') as f:
            json.dump([log1.model_dump(by_alias=True)], f)
            
        with open(os.path.join(self.deltas_path, "PS-002.json"), 'w') as f:
            json.dump([log2.model_dump(by_alias=True)], f)
            
        manager = self._get_manager_instance()
        manager.dump_uncurated_logs()
        
        output_file = os.path.join(self.curating_logs_path, "uncurated_for_review.json")
        self.assertTrue(os.path.exists(output_file))
        
        with open(output_file, 'r') as f:
            dumped_data = json.load(f)
            
        self.assertIn("PS-001", dumped_data)
        self.assertNotIn("PS-002", dumped_data)
        self.assertEqual(len(dumped_data["PS-001"]), 1)
        self.assertEqual(dumped_data["PS-001"][0]["details"], "signal1")

    def test_assemble_review_package_workflow(self):
        """[NEW] Tests the feature to assemble and zip the practitioner review package."""
        manager = self._get_manager_instance()
        
        mock_log = SplunkLogEvent.model_validate({"_raw": "EventCode=1 data=signal1", "source": "s1", "_time": "t1", "sourcetype": "st1"})
        with open(os.path.join(self.deltas_path, "PS-001.json"), 'w') as f:
            json.dump([mock_log.model_dump(by_alias=True)], f)
        
        output_zip_path = "practitioner_package.zip"
        if os.path.exists(output_zip_path):
            os.remove(output_zip_path)

        manager._assemble_review_package()

        self.assertTrue(os.path.exists(output_zip_path))

        with zipfile.ZipFile(output_zip_path, 'r') as zf:
            filenames = zf.namelist()
            self.assertIn("INSTRUCTIONS.md", filenames)
            self.assertIn("PS-001/", filenames)
            self.assertIn("PS-001/command.txt", filenames)
            self.assertIn("PS-001/context.txt", filenames)
            self.assertIn("PS-001/delta_logs.json", filenames)

        os.remove(output_zip_path)

if __name__ == '__main__':
    unittest.main()
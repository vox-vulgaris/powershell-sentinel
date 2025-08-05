# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# Unit tests for the recommendation_engine.py module.
# This test is updated to reflect the refactored engine, which now includes
# a parsing step to translate raw logs into structured rules before scoring.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Test the core `get_recommendations` function.
# 2. Create mock inputs that the internal `_parse_log_to_rule` function can process.
# 3. Build mock statistics dictionaries using the correct keys (JSON dumps of TelemetryRule objects).
# 4. Assert that the returned list contains only the expected logs and is correctly ranked.

import unittest
from powershell_sentinel.modules.recommendation_engine import get_recommendations
from powershell_sentinel.models import SplunkLogEvent, MitreTTPEnum, TelemetryRule

# Helper to create dummy SplunkLogEvent objects for testing.
# The raw content is now designed to be parseable by the engine.
def create_log(raw_content: str, sourcetype: str = "PowerShell") -> SplunkLogEvent:
    return SplunkLogEvent.model_validate({
        "_raw": raw_content, "_time": "time", "source": "TestSource", "sourcetype": sourcetype
    })

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        """Set up mock data for testing the refactored recommendation engine."""
        # --- 1. Define the clean, structured rules we expect to be parsed ---
        self.rule_high_relevance = TelemetryRule(source="TestSource", event_id=4104, details="Get-Process")
        self.rule_high_rarity = TelemetryRule(source="TestSource", event_id=1, details="rare-command.exe")
        self.rule_noise = TelemetryRule(source="TestSource", event_id=4104, details="common-command")
        
        # --- 2. Create the raw Splunk logs that will produce those rules when parsed ---
        self.log_high_relevance = create_log("EventCode=4104 ScriptBlockText=Get-Process Message=")
        self.log_high_rarity = create_log("<Data Name='CommandLine'>rare-command.exe</Data> EventCode=1", sourcetype="xmlwineventlog")
        self.log_noise = create_log("EventCode=4104 ScriptBlockText=common-command Message=")
        self.log_unparseable = create_log("Some log format we don't recognize")

        self.delta_logs = [
            self.log_high_relevance, self.log_high_rarity, self.log_noise, self.log_unparseable
        ]
        
        # --- 3. Build the mock statistics using the CORRECT keys (JSON dumps of the rules) ---
        self.rarity_stats = {
            self.rule_high_relevance.model_dump_json(): 0.5,  # Not rare enough
            self.rule_high_rarity.model_dump_json(): 0.9,     # Very rare (above 0.8 threshold)
            self.rule_noise.model_dump_json(): 0.1,           # Very common
        }
        
        # Use a valid TTP from mitre_ttp_library.json, e.g., T1057 for Process Discovery
        self.relevance_stats = {
            MitreTTPEnum.T1057.value: {
                self.rule_high_relevance.model_dump_json(): 0.95, # Highly relevant (above 0.75 threshold)
                self.rule_high_rarity.model_dump_json(): 0.1,     # Not relevant enough
                self.rule_noise.model_dump_json(): 0.05,          # Not relevant
            }
        }
        
        self.primitive_ttps = [MitreTTPEnum.T1057]

    def test_get_recommendations(self):
        """
        Test that the engine correctly parses, filters, and ranks logs.
        """
        # Act
        recommendations = get_recommendations(
            self.delta_logs, self.rarity_stats, self.relevance_stats, self.primitive_ttps
        )
        
        # Assert
        # 1. Check that noise and unparseable logs were filtered out
        self.assertEqual(len(recommendations), 2)
        self.assertNotIn(self.log_noise, recommendations)
        self.assertNotIn(self.log_unparseable, recommendations)
        
        # 2. Check that the other two logs were recommended for the correct reasons
        self.assertIn(self.log_high_relevance, recommendations) # Recommended for high relevance
        self.assertIn(self.log_high_rarity, recommendations)    # Recommended for high rarity
        
        # 3. Check for correct ranking (sorted by relevance descending)
        # The first item should be the one with the highest relevance score (0.95).
        self.assertEqual(recommendations[0], self.log_high_relevance)
        # The second item should be the one with the lower relevance score (0.1).
        self.assertEqual(recommendations[1], self.log_high_rarity)


if __name__ == '__main__':
    unittest.main()
# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# Unit tests for the recommendation_engine.py module.
# This test validates the final, simplified version of the engine, which now
# operates exclusively on pre-parsed TelemetryRule objects.
#
# REQUIREMENTS:
# 1. Test the core `get_recommendations` function.
# 2. Provide a list of Pydantic `TelemetryRule` models as direct input.
# 3. Build mock statistics dictionaries to test the scoring logic.
# 4. Assert that the returned list is correctly filtered and ranked.

import unittest
# Note: 'patch' is no longer needed as there is no parsing to mock.
from powershell_sentinel.modules.recommendation_engine import get_recommendations
from powershell_sentinel.models import MitreTTPEnum, TelemetryRule

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        """Set up mock, pre-parsed TelemetryRule data for testing."""
        # --- 1. Define the clean, structured rules that are now the direct input ---
        self.rule_high_relevance = TelemetryRule(source="TestSource", event_id=4104, details="Get-Process")
        self.rule_high_rarity = TelemetryRule(source="TestSource", event_id=1, details="rare-command.exe")
        self.rule_noise = TelemetryRule(source="TestSource", event_id=4104, details="common-command")
        
        # This is the direct input to the function we are testing.
        self.parsed_rules = [
            self.rule_high_relevance,
            self.rule_high_rarity,
            self.rule_noise
        ]
        
        # --- 2. Build the mock statistics using the keys from the rules ---
        self.rarity_stats = {
            self.rule_high_relevance.model_dump_json(): 0.5,  # Not rare enough
            self.rule_high_rarity.model_dump_json(): 0.9,     # Very rare (above 0.8 threshold)
            self.rule_noise.model_dump_json(): 0.1,           # Very common
        }
        
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
        Test that the engine correctly filters and ranks a list of pre-parsed rules.
        """
        # --- Act ---
        # Call the function with the direct, pre-parsed input. No mocking is needed.
        recommendations = get_recommendations(
            self.parsed_rules, self.rarity_stats, self.relevance_stats, self.primitive_ttps
        )
        
        # --- Assert ---
        # The assertions now check the filtering and ranking of TelemetryRule objects.
        # 1. Check that the noise rule was filtered out.
        self.assertEqual(len(recommendations), 2)
        self.assertNotIn(self.rule_noise, recommendations)
        
        # 2. Check that the other two rules were recommended.
        self.assertIn(self.rule_high_relevance, recommendations)
        self.assertIn(self.rule_high_rarity, recommendations)
        
        # 3. Check for correct ranking (sorted by relevance descending).
        self.assertEqual(recommendations[0], self.rule_high_relevance)
        self.assertEqual(recommendations[1], self.rule_high_rarity)


if __name__ == '__main__':
    unittest.main()
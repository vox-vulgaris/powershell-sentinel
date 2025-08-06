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
from powershell_sentinel.modules.recommendation_engine import get_recommendations
from powershell_sentinel.models import MitreTTPEnum, TelemetryRule

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        """Set up mock, pre-parsed TelemetryRule data for testing."""
        # --- 1. Define the clean, structured rules that are now the direct input ---
        self.rule_high_relevance = TelemetryRule(source="TestSource", event_id=4104, details="Get-Process")
        self.rule_high_rarity = TelemetryRule(source="TestSource", event_id=1, details="rare-command.exe")
        self.rule_noise = TelemetryRule(source="TestSource", event_id=4104, details="common-command")
        
        self.parsed_rules = [
            self.rule_high_relevance,
            self.rule_high_rarity,
            self.rule_noise
        ]
        
        # --- 2. Build the mock statistics using the keys from the rules ---
        self.rarity_stats = {
            self.rule_high_relevance.model_dump_json(): 0.5,
            self.rule_high_rarity.model_dump_json(): 0.9,
            self.rule_noise.model_dump_json(): 0.1,
        }
        
        self.relevance_stats = {
            MitreTTPEnum.T1057.value: {
                self.rule_high_relevance.model_dump_json(): 0.95,
                self.rule_high_rarity.model_dump_json(): 0.1,
                self.rule_noise.model_dump_json(): 0.05,
            }
        }
        
        self.primitive_ttps = [MitreTTPEnum.T1057]

    def test_get_recommendations_filters_and_ranks_correctly(self):
        """
        Test that the engine correctly filters and ranks a list of pre-parsed rules
        when some rules meet the statistical thresholds.
        """
        # --- Act ---
        recommendations = get_recommendations(
            self.parsed_rules, self.rarity_stats, self.relevance_stats, self.primitive_ttps
        )
        
        # --- Assert ---
        self.assertEqual(len(recommendations), 2)
        self.assertNotIn(self.rule_noise, recommendations)
        self.assertIn(self.rule_high_relevance, recommendations)
        self.assertIn(self.rule_high_rarity, recommendations)
        self.assertEqual(recommendations[0], self.rule_high_relevance) # Correctly ranked by relevance
        self.assertEqual(recommendations[1], self.rule_high_rarity)

    def test_bootstrap_mode_with_no_stats_returns_all_rules(self):
        """
        [NEW] Test that the engine returns all parsed rules when the statistics are empty
        (the initial "bootstrap" run).
        """
        # --- Act ---
        recommendations = get_recommendations(
            self.parsed_rules, {}, {}, self.primitive_ttps
        )

        # --- Assert ---
        # Should return all 3 rules since there are no stats to filter by.
        self.assertEqual(len(recommendations), 3)
        self.assertIn(self.rule_noise, recommendations)

    def test_fallback_mode_when_no_rules_meet_threshold(self):
        """
        [NEW] Test that the engine returns all parsed rules when stats exist but none
        are high enough to meet the filtering thresholds.
        """
        # --- Arrange ---
        # Create stats where no rule meets the 0.8 rarity or 0.75 relevance threshold.
        low_stats = {
            self.rule_high_relevance.model_dump_json(): 0.5,
            self.rule_high_rarity.model_dump_json(): 0.6,
            self.rule_noise.model_dump_json(): 0.1,
        }
        low_relevance = {
            MitreTTPEnum.T1057.value: {
                self.rule_high_relevance.model_dump_json(): 0.7, # Highest relevance, but below threshold
                self.rule_high_rarity.model_dump_json(): 0.1,
                self.rule_noise.model_dump_json(): 0.05,
            }
        }

        # --- Act ---
        recommendations = get_recommendations(
            self.parsed_rules, low_stats, low_relevance, self.primitive_ttps
        )

        # --- Assert ---
        # Even though nothing met the threshold, the fallback should return all 3 rules.
        self.assertEqual(len(recommendations), 3)
        # It should still sort them by relevance, so the highest one is first.
        self.assertEqual(recommendations[0], self.rule_high_relevance)

    def test_empty_input_returns_empty_list(self):
        """
        [NEW] Test the edge case where an empty list of parsed rules is provided.
        """
        # --- Act ---
        recommendations = get_recommendations(
            [], self.rarity_stats, self.relevance_stats, self.primitive_ttps
        )

        # --- Assert ---
        self.assertEqual(len(recommendations), 0)

if __name__ == '__main__':
    unittest.main()
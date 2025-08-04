# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# Unit tests for the recommendation_engine.py module.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Test the core `get_recommendations` function.
# 2. Create mock inputs using Pydantic models: `SplunkLogEvent`, `MitreTTPEnum`.
# 3. Ensure the test covers logs that should be recommended and logs that should be filtered out.
# 4. Assert that the returned list contains only the expected `SplunkLogEvent` objects.
# 5. Assert that the returned list is correctly ranked based on the defined scoring logic.

import unittest
from powershell_sentinel.modules.recommendation_engine import get_recommendations
from powershell_sentinel.models import SplunkLogEvent, MitreTTPEnum

# Helper to create dummy SplunkLogEvent objects for testing
def create_log(raw_content: str) -> SplunkLogEvent:
    return SplunkLogEvent.model_validate({
        "_raw": raw_content, "_time": "time", "source": "s", "sourcetype": "st"
    })

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        """Set up mock data for testing the recommendation engine."""
        self.log_high_relevance = create_log("High relevance log")
        self.log_high_rarity = create_log("High rarity log")
        self.log_noise = create_log("Noise log")

        self.delta_logs = [self.log_high_relevance, self.log_high_rarity, self.log_noise]
        
        self.rarity_stats = {
            self.log_high_relevance.raw: 0.5, # Not rare enough
            self.log_high_rarity.raw: 0.9,    # Very rare (above 0.8 threshold)
            self.log_noise.raw: 0.1           # Very common
        }
        
        self.relevance_stats = {
            MitreTTPEnum.T1003_001.value: {
                self.log_high_relevance.raw: 0.95, # Highly relevant (above 0.75 threshold)
                self.log_high_rarity.raw: 0.1,     # Not relevant enough
                self.log_noise.raw: 0.05            # Not relevant
            }
        }
        
        self.primitive_ttps = [MitreTTPEnum.T1003_001]

    def test_get_recommendations(self):
        """
        Test that the engine correctly filters and ranks logs based on heuristics.
        """
        # Act
        recommendations = get_recommendations(
            self.delta_logs, self.rarity_stats, self.relevance_stats, self.primitive_ttps
        )
        
        # Assert
        # 1. Check that the noise log was filtered out
        self.assertEqual(len(recommendations), 2)
        self.assertNotIn(self.log_noise, recommendations)
        
        # 2. Check that the other two logs were recommended for different reasons
        self.assertIn(self.log_high_relevance, recommendations) # Recommended for relevance
        self.assertIn(self.log_high_rarity, recommendations)    # Recommended for rarity
        
        # 3. Check for correct ranking (sorted by relevance descending)
        # The first item should be the one with the highest relevance score (0.95).
        self.assertEqual(recommendations[0], self.log_high_relevance)
        # The second item should be the one with the lower relevance score (0.1).
        self.assertEqual(recommendations[1], self.log_high_rarity)


if __name__ == '__main__':
    unittest.main()
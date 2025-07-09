# Phase 2: Data Factory - Curation Tooling
# Index: [6]
#
# Unit tests for the recommendation_engine.py module.
#
# REQUIREMENTS:
# 1. Test the core `get_recommendations` function.
# 2. Create mock inputs: `delta_logs`, `global_rarity` stats, `local_relevance` stats, and `primitive_tags`.
# 3. Ensure the test covers logs that should be recommended and logs that should be filtered out.
# 4. Assert that the returned list contains only the expected logs.
# 5. Assert that the returned list is correctly ranked (sorted) based on the defined scoring logic.

import unittest
from powershell_sentinel.modules.recommendation_engine import get_recommendations

# A mock hashable representation for logs for testing purposes
def make_log_repr(log):
    return tuple(sorted(log.items()))

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        """Set up mock data for testing the recommendation engine."""
        self.log_high_relevance = {"EventID": 4104, "Message": "Malicious Script Block"}
        self.log_high_rarity = {"EventID": 10, "Provider": "Sysmon", "Target": "lsass.exe"}
        self.log_noise = {"EventID": 4624, "AccountType": "User"}

        self.delta_logs = [self.log_high_relevance, self.log_high_rarity, self.log_noise]
        
        self.rarity_stats = {
            make_log_repr(self.log_high_relevance): 0.5, # Not rare
            make_log_repr(self.log_high_rarity): 0.9,    # Very rare
            make_log_repr(self.log_noise): 0.1           # Very common
        }
        
        self.relevance_stats = {
            "T1003": {
                make_log_repr(self.log_high_relevance): 0.95, # Highly relevant
                make_log_repr(self.log_high_rarity): 0.85,    # Also highly relevant
                make_log_repr(self.log_noise): 0.05           # Not relevant
            }
        }
        
        self.primitive_tags = ["T1003"]

    def test_get_recommendations(self):
        """
        Test that the engine correctly filters and ranks logs based on heuristics.
        Assuming static thresholds: rarity >= 0.8 OR relevance >= 0.8
        """
        # TODO: Properly implement this test once the main function is built.
        #
        # # Act
        # recommendations = get_recommendations(self.delta_logs, self.rarity_stats, self.relevance_stats, self.primitive_tags)
        #
        # # Assert
        # # 1. Check that the noise log was filtered out
        # self.assertEqual(len(recommendations), 2)
        # recommended_messages = [log['Message'] for log in recommendations if 'Message' in log]
        # self.assertNotIn("Noise", " ".join(recommended_messages))
        #
        # # 2. Check that the remaining logs are the correct ones
        # self.assertIn(self.log_high_relevance, recommendations)
        # self.assertIn(self.log_high_rarity, recommendations)
        #
        # # 3. Check for correct ranking (sorted by relevance descending)
        # # The first item in the list should be the one with the highest relevance score.
        # self.assertEqual(recommendations[0], self.log_high_relevance)
        pass

if __name__ == '__main__':
    unittest.main()
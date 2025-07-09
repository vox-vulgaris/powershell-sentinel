# Phase 2: Data Factory - Curation Tooling
# Index: [5]
#
# Unit tests for the statistics_calculator.py module.
#
# REQUIREMENTS:
# 1. Test `calculate_global_rarity` and `calculate_local_relevance` functions.
# 2. Create a small, mock `primitives_library` to serve as test input.
# 3. Manually calculate the expected rarity and relevance scores for the mock data.
# 4. Assert that the functions' outputs match the pre-calculated expected values.
# 5. Ensure floating point comparisons are handled carefully (e.g., using `assertAlmostEqual`).

import unittest
import math
from powershell_sentinel.modules.statistics_calculator import calculate_global_rarity, calculate_local_relevance

# A mock hashable representation for logs for testing purposes
def make_log_repr(log):
    return tuple(sorted(log.items()))

class TestStatisticsCalculator(unittest.TestCase):

    def setUp(self):
        """Set up a mock primitives library for testing."""
        self.log1 = {"EventID": 4688, "ProcessName": "powershell.exe"} # Appears in 2 primitives
        self.log2 = {"EventID": 4104}                                 # Appears in 1 primitive
        self.log3 = {"EventID": 1, "Provider": "Sysmon"}              # Appears in 1 primitive

        self.mock_library = [
            {
                "primitive_id": "PS-001",
                "mitre_ttps": ["T1059", "T1057"],
                "telemetry_rules": [self.log1, self.log2]
            },
            {
                "primitive_id": "PS-002",
                "mitre_ttps": ["T1059"],
                "telemetry_rules": [self.log1, self.log3]
            }
        ]

    def test_calculate_global_rarity(self):
        """Test the calculation of Inverse Primitive Frequency."""
        # TODO: This test needs to be properly implemented.
        # total_primitives = 2
        # log1_count = 2 -> rarity = log(2/2) = 0
        # log2_count = 1 -> rarity = log(2/1) = 0.693
        # log3_count = 1 -> rarity = log(2/1) = 0.693
        #
        # rarity_scores = calculate_global_rarity(self.mock_library)
        #
        # self.assertAlmostEqual(rarity_scores[make_log_repr(self.log1)], 0.0)
        # self.assertAlmostEqual(rarity_scores[make_log_repr(self.log2)], math.log(2))
        # self.assertAlmostEqual(rarity_scores[make_log_repr(self.log3)], math.log(2))
        pass

    def test_calculate_local_relevance(self):
        """Test the calculation of P(Log|Tag)."""
        # TODO: This test needs to be properly implemented.
        #
        # For T1059 (appears in 2 primitives):
        # - log1 appears 2 times with T1059. P(log1|T1059) = 2/2 = 1.0
        # - log2 appears 1 time with T1059. P(log2|T1059) = 1/2 = 0.5
        # - log3 appears 1 time with T1059. P(log3|T1059) = 1/2 = 0.5
        #
        # For T1057 (appears in 1 primitive):
        # - log1 appears 1 time with T1057. P(log1|T1057) = 1/1 = 1.0
        # - log2 appears 1 time with T1057. P(log2|T1057) = 1/1 = 1.0
        #
        # relevance_scores = calculate_local_relevance(self.mock_library)
        #
        # self.assertAlmostEqual(relevance_scores["T1059"][make_log_repr(self.log1)], 1.0)
        # self.assertAlmostEqual(relevance_scores["T1059"][make_log_repr(self.log2)], 0.5)
        # self.assertAlmostEqual(relevance_scores["T1057"][make_log_repr(self.log2)], 1.0)
        pass

if __name__ == '__main__':
    unittest.main()
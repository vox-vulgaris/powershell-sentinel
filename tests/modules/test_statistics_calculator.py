# Phase 2: Data Factory - Curation Tooling
# Index: [5]
#
# Unit tests for the statistics_calculator.py module.
#
# REQUIREMENTS (Pydantic-aware):
# 1. Test `calculate_global_rarity` and `calculate_local_relevance` functions.
# 2. Create a small, mock list of `Primitive` models to serve as test input.
# 3. Manually calculate the expected rarity and relevance scores for the mock data.
# 4. Assert that the functions' outputs match the pre-calculated expected values.
# 5. Ensure floating point comparisons are handled carefully (using `assertAlmostEqual`).

import unittest
import math
from powershell_sentinel.modules.statistics_calculator import calculate_global_rarity, calculate_local_relevance
from powershell_sentinel.models import Primitive, TelemetryRule, IntentEnum, MitreTTPEnum

class TestStatisticsCalculator(unittest.TestCase):

    def setUp(self):
        """Set up a mock primitives library for testing using Pydantic models."""
        self.rule1 = TelemetryRule(source="Security", event_id=4688, details="powershell.exe created") # Appears in 2 primitives
        self.rule2 = TelemetryRule(source="PowerShell", event_id=4104, details="Get-Process executed") # Appears in 1 primitive
        self.rule3 = TelemetryRule(source="Sysmon", event_id=1, details="whoami.exe created")       # Appears in 1 primitive

        # Corrected TTPs based on the error message
        self.mock_library = [
            Primitive(
                primitive_id="PS-001",
                primitive_command="Get-Process",
                intent=[IntentEnum.PROCESS_DISCOVERY],
                mitre_ttps=[MitreTTPEnum.T1069_001, MitreTTPEnum.T1057], # CORRECTED
                telemetry_rules=[self.rule1, self.rule2]
            ),
            Primitive(
                primitive_id="PS-002",
                primitive_command="whoami",
                intent=[IntentEnum.USER_DISCOVERY],
                mitre_ttps=[MitreTTPEnum.T1069_001], # CORRECTED
                telemetry_rules=[self.rule1, self.rule3]
            )
        ]

    def test_calculate_global_rarity(self):
        """Test the calculation of Inverse Primitive Frequency."""
        # total_primitives = 2
        # rule1_count = 2 -> rarity = log(2/2) = 0
        # rule2_count = 1 -> rarity = log(2/1) = 0.693...
        # rule3_count = 1 -> rarity = log(2/1) = 0.693...
        
        rarity_scores = calculate_global_rarity(self.mock_library)
        
        self.assertAlmostEqual(rarity_scores[self.rule1.model_dump_json()], 0.0)
        self.assertAlmostEqual(rarity_scores[self.rule2.model_dump_json()], math.log(2))
        self.assertAlmostEqual(rarity_scores[self.rule3.model_dump_json()], math.log(2))

    def test_calculate_local_relevance(self):
        """Test the calculation of P(Log|Tag)."""
        # For T1069.001 (appears in 2 primitives): -- CORRECTED COMMENT
        # - rule1 appears 2 times with T1069.001. P(rule1|T1069.001) = 2/2 = 1.0
        # - rule2 appears 1 time with T1069.001. P(rule2|T1069.001) = 1/2 = 0.5
        # - rule3 appears 1 time with T1069.001. P(rule3|T1069.001) = 1/2 = 0.5
        #
        # For T1057 (appears in 1 primitive):
        # - rule1 appears 1 time with T1057. P(rule1|T1057) = 1/1 = 1.0
        # - rule2 appears 1 time with T1057. P(rule2|T1057) = 1/1 = 1.0
        
        relevance_scores = calculate_local_relevance(self.mock_library)
        
        # Test a few key values
        self.assertAlmostEqual(relevance_scores[MitreTTPEnum.T1069_001.value][self.rule1.model_dump_json()], 1.0) # CORRECTED
        self.assertAlmostEqual(relevance_scores[MitreTTPEnum.T1069_001.value][self.rule2.model_dump_json()], 0.5) # CORRECTED
        self.assertAlmostEqual(relevance_scores[MitreTTPEnum.T1057.value][self.rule2.model_dump_json()], 1.0)
        # Check that a rule not associated with a tag isn't present
        self.assertNotIn(self.rule3.model_dump_json(), relevance_scores.get(MitreTTPEnum.T1057.value, {}))


if __name__ == '__main__':
    unittest.main()
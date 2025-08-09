# tests/test_mlops_metrics.py

import unittest
from powershell_sentinel.utils.metrics import calculate_multilabel_f1_scores
from powershell_sentinel.models import IntentEnum, MitreTTPEnum

class TestMLOpsMetrics(unittest.TestCase):

    def test_f1_perfect_match(self):
        """Tests F1 calculation with a perfect match."""
        ground_truths = [[IntentEnum.PROCESS_DISCOVERY, IntentEnum.USER_DISCOVERY]]
        predictions = [[IntentEnum.PROCESS_DISCOVERY, IntentEnum.USER_DISCOVERY]]
        all_labels = list(IntentEnum)
        
        scores = calculate_multilabel_f1_scores(predictions, ground_truths, all_labels)
        
        # The F1 is 1.0 for the 2 classes present, and 0 for the other 24.
        # The macro average is the sum of F1s divided by the total number of classes.
        expected_f1 = (1.0 + 1.0) / len(all_labels)
        self.assertAlmostEqual(scores['f1_macro'], expected_f1)

    def test_f1_partial_match(self):
        """Tests F1 calculation with a known partial match example."""
        ground_truths = [[IntentEnum.PROCESS_DISCOVERY, IntentEnum.USER_DISCOVERY]]
        predictions = [[IntentEnum.PROCESS_DISCOVERY, IntentEnum.SOFTWARE_DISCOVERY]]
        all_labels = list(IntentEnum)
        
        scores = calculate_multilabel_f1_scores(predictions, ground_truths, all_labels)

        # F1 for PROCESS_DISCOVERY is 1.0 (TP).
        # F1 for USER_DISCOVERY is 0.0 (FN).
        # F1 for SOFTWARE_DISCOVERY is 0.0 (FP).
        # All others are 0.0.
        # The macro average is the sum of F1s divided by the total number of classes.
        expected_f1 = 1.0 / len(all_labels)
        self.assertAlmostEqual(scores['f1_macro'], expected_f1)

    def test_f1_no_match(self):
        """Test F1 score when there is no overlap."""
        ground_truths = [[IntentEnum.PROCESS_DISCOVERY]]
        predictions = [[IntentEnum.SOFTWARE_DISCOVERY]]
        all_labels = list(IntentEnum)
        
        scores = calculate_multilabel_f1_scores(predictions, ground_truths, all_labels)
        self.assertAlmostEqual(scores['f1_macro'], 0.0)

    def test_f1_empty_prediction(self):
        """Test F1 score when the prediction is empty."""
        ground_truths = [[IntentEnum.PROCESS_DISCOVERY]]
        predictions = [[]]
        all_labels = list(IntentEnum)

        scores = calculate_multilabel_f1_scores(predictions, ground_truths, all_labels)
        self.assertAlmostEqual(scores['f1_macro'], 0.0)

    def test_f1_with_mitre_ttps(self):
        """Ensures the function works with the MITRE TTP enum as well."""
        ground_truths = [[MitreTTPEnum.T1057, MitreTTPEnum.T1087_001]]
        predictions = [[MitreTTPEnum.T1057]]
        all_labels = list(MitreTTPEnum)
        
        scores = calculate_multilabel_f1_scores(predictions, ground_truths, all_labels)
        expected_f1 = 1.0 / len(all_labels)
        self.assertAlmostEqual(scores['f1_macro'], expected_f1)

if __name__ == '__main__':
    unittest.main()
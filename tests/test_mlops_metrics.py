# Phase 4: Model Training & Evaluation
# Index: [16]
#
# Unit tests for the metric calculation functions within evaluate.py.
#
# REQUIREMENTS:
# 1. Test the F1-score calculation logic with mock data.
# 2. Create small, handcrafted examples of predicted vs. ground truth lists.
# 3. Assert that the calculated precision, recall, and F1-score are mathematically correct.
# 4. This ensures the evaluation script's core logic is sound.

import unittest

# This function would ideally be defined in a utility file or within evaluate.py
def calculate_f1_score(prediction: list, ground_truth: list) -> dict:
    """Calculates precision, recall, and F1 for two lists of items."""
    pred_set = set(prediction)
    true_set = set(ground_truth)

    true_positives = len(pred_set.intersection(true_set))
    false_positives = len(pred_set.difference(true_set))
    false_negatives = len(true_set.difference(pred_set))

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {"precision": precision, "recall": recall, "f1": f1}


class TestMLOpsMetrics(unittest.TestCase): # CORRECTED CLASS NAME
    def test_f1_score_calculation_perfect_match(self):
        """Test F1 score when prediction and ground truth are identical."""
        ground_truth = ["A", "B", "C"]
        prediction = ["A", "B", "C"]
        scores = calculate_f1_score(prediction, ground_truth)
        self.assertAlmostEqual(scores['f1'], 1.0)
        self.assertAlmostEqual(scores['precision'], 1.0)
        self.assertAlmostEqual(scores['recall'], 1.0)

    def test_f1_score_calculation_partial_match(self):
        """Test F1 score with a known partial match example."""
        ground_truth = ["A", "B", "C"]
        prediction = ["A", "B", "D"]
        # TP=2, FP=1, FN=1 -> Precision=0.667, Recall=0.667, F1=0.667
        scores = calculate_f1_score(prediction, ground_truth)
        self.assertAlmostEqual(scores['f1'], 0.666, places=3)
        self.assertAlmostEqual(scores['precision'], 0.666, places=3)
        self.assertAlmostEqual(scores['recall'], 0.666, places=3)

    def test_f1_score_no_match(self):
        """Test F1 score when there is no overlap."""
        ground_truth = ["A", "B", "C"]
        prediction = ["D", "E", "F"]
        scores = calculate_f1_score(prediction, ground_truth)
        self.assertAlmostEqual(scores['f1'], 0.0)

    def test_f1_score_empty_prediction(self):
        """Test F1 score when the prediction is empty."""
        ground_truth = ["A", "B", "C"]
        prediction = []
        # TP=0, FP=0, FN=3 -> Precision=0, Recall=0, F1=0
        scores = calculate_f1_score(prediction, ground_truth)
        self.assertAlmostEqual(scores['f1'], 0.0)
        self.assertAlmostEqual(scores['precision'], 0.0)
        self.assertAlmostEqual(scores['recall'], 0.0)

if __name__ == '__main__':
    unittest.main()
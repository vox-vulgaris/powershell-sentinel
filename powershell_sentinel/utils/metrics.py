# powershell_sentinel/utils/metrics.py

from typing import List, Any, Dict
from pydantic import BaseModel
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import f1_score

def calculate_multilabel_f1_scores(
    predictions: List[List[Any]], 
    ground_truths: List[List[Any]], 
    all_labels: List[Any]
) -> dict:
    """
    Calculates macro-averaged F1 score for multi-label classification.
    Used for fields like 'intent' and 'mitre_ttps'.
    """
    if not predictions or not ground_truths:
        return {"f1_macro": 0.0}

    if len(predictions) != len(ground_truths):
         raise ValueError("Predictions and ground truths must have the same length.")

    mlb = MultiLabelBinarizer(classes=all_labels)
    
    y_true = mlb.fit_transform(ground_truths)
    y_pred = mlb.transform(predictions)

    f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    
    return {"f1_macro": f1}


# --- NEW FUNCTION ADDED FOR TELEMETRY EVALUATION ---

def calculate_f1_for_telemetry(y_pred: List[List[BaseModel]], y_true: List[List[BaseModel]]) -> Dict[str, float]:
    """
    Calculates the F1 score for lists of Pydantic TelemetryRule objects.

    This function treats each TelemetryRule object as an atomic unit and compares
    the set of predicted rules to the set of true rules for each sample.
    """
    
    def to_canonical_set(rules: List[BaseModel]) -> set:
        """Converts a list of Pydantic models into a set of hashable, sorted tuples."""
        return {tuple(sorted(rule.model_dump().items())) for rule in rules}

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for pred_list, true_list in zip(y_pred, y_true):
        pred_set = to_canonical_set(pred_list)
        true_set = to_canonical_set(true_list)

        intersection = pred_set.intersection(true_set)
        
        true_positives += len(intersection)
        false_positives += len(pred_set - true_set)
        false_negatives += len(true_set - pred_set)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    f1_macro = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {"f1_macro": f1_macro}
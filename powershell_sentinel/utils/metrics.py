# powershell_sentinel/utils/metrics.py

from typing import List, Any
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import f1_score

def calculate_multilabel_f1_scores(
    predictions: List[List[Any]], 
    ground_truths: List[List[Any]], 
    all_labels: List[Any]
) -> dict:
    """
    Calculates macro-averaged F1 score for multi-label classification.
    
    Args:
        predictions: A list of lists, where each inner list contains the predicted labels for a sample.
        ground_truths: A list of lists, containing the ground truth labels.
        all_labels: A complete list of all possible labels (the label universe).

    Returns:
        A dictionary containing the macro-averaged F1 score.
    """
    if not predictions or not ground_truths:
        return {"f1_macro": 0.0}

    # Ensure ground_truths and predictions are the same length for comparison
    if len(predictions) != len(ground_truths):
         raise ValueError("Predictions and ground truths must have the same length.")

    mlb = MultiLabelBinarizer(classes=all_labels)
    
    # Transform the lists of labels into binary matrix format
    y_true = mlb.fit_transform(ground_truths)
    y_pred = mlb.transform(predictions)

    # Calculate F1 score
    f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    
    return {"f1_macro": f1}
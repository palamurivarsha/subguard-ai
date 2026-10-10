
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = PROJECT_ROOT / "data/synthetic/bank_transactions.csv"
ANOMALIES_PATH = (
    PROJECT_ROOT / "data/processed/subscription_anomalies.csv"
)

ANOMALY_EVENTS = {"duplicate", "price_increase"}


def evaluate():
    raw = pd.read_csv(RAW_PATH)
    anomalies = pd.read_csv(ANOMALIES_PATH)

    required = {
        "transaction_id",
        "event_type_ground_truth",
    }

    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Ground truth is used for evaluation only.
    raw["actual_anomaly"] = (
        raw["event_type_ground_truth"]
        .isin(ANOMALY_EVENTS)
        .astype(int)
    )

    predicted_ids = set(
        anomalies["transaction_id"].astype(str)
    )

    raw["predicted_anomaly"] = (
        raw["transaction_id"]
        .astype(str)
        .isin(predicted_ids)
        .astype(int)
    )

    y_true = raw["actual_anomaly"]
    y_pred = raw["predicted_anomaly"]

    print("\n========== ANOMALY EVALUATION ==========")
    print(f"Transactions evaluated: {len(raw)}")

    print(
        f"Actual anomalies: {int(y_true.sum())}"
    )
    print(
        f"Predicted anomalies: {int(y_pred.sum())}"
    )

    print(
        f"Precision: {precision_score(y_true, y_pred, zero_division=0):.4f}"
    )
    print(
        f"Recall: {recall_score(y_true, y_pred, zero_division=0):.4f}"
    )
    print(
        f"F1-score: {f1_score(y_true, y_pred, zero_division=0):.4f}"
    )

    print("\nGround-truth event types:")
    print(
        raw["event_type_ground_truth"]
        .value_counts()
        .to_string()
    )

    print("\n========== EVALUATION COMPLETE ==========")


if __name__ == "__main__":
    evaluate()
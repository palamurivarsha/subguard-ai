
from pathlib import Path
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = ROOT / "data/synthetic/bank_transactions.csv"
SUBSCRIPTIONS_PATH = (
    ROOT / "data/processed/detected_subscriptions.csv"
)
ANOMALIES_PATH = (
    ROOT / "data/processed/subscription_anomalies.csv"
)


def evaluate():
    raw = pd.read_csv(RAW_PATH)
    subscriptions = pd.read_csv(SUBSCRIPTIONS_PATH)
    anomalies = pd.read_csv(ANOMALIES_PATH)

    merchants = set(
        subscriptions["merchant_name"].dropna().astype(str)
    )

    # Map raw merchant names to normalized merchant names
    # for evaluation only. Never use ground truth in detection.
    normalized = pd.read_parquet(
        ROOT / "data/processed/normalized_transactions.parquet"
    )

    scope_ids = set(
        normalized.loc[
            normalized["normalized_merchant"].isin(merchants),
            "transaction_id",
        ].astype(str)
    )

    evaluation = raw[
        raw["transaction_id"].astype(str).isin(scope_ids)
    ].copy()

    # Evaluate duplicate-charge detection separately.
    evaluation["actual_duplicate"] = (
        evaluation["event_type_ground_truth"] == "duplicate"
    ).astype(int)

    predicted_ids = set(
        anomalies.loc[
            anomalies["anomaly_type"] == "duplicate_charge",
            "transaction_id",
        ].astype(str)
    )

    evaluation["predicted_duplicate"] = (
        evaluation["transaction_id"]
        .astype(str)
        .isin(predicted_ids)
        .astype(int)
    )

    y_true = evaluation["actual_duplicate"]
    y_pred = evaluation["predicted_duplicate"]

    tn, fp, fn, tp = confusion_matrix(
        y_true, y_pred, labels=[0, 1]
    ).ravel()

    print("\n========== SUBSCRIPTION ANOMALY EVALUATION ==========")
    print(f"Transactions evaluated: {len(evaluation)}")
    print(f"True positives: {tp}")
    print(f"False positives: {fp}")
    print(f"False negatives: {fn}")
    print(f"True negatives: {tn}")

    print(
        f"Precision: {precision_score(y_true, y_pred, zero_division=0):.4f}"
    )
    print(
        f"Recall: {recall_score(y_true, y_pred, zero_division=0):.4f}"
    )
    print(
        f"F1-score: {f1_score(y_true, y_pred, zero_division=0):.4f}"
    )

    print(
        "\nNote: Metrics cover subscription duplicate detection "
        "only, on synthetic development data."
    )
    print("Price-change detection is evaluated separately.")
    print("========== EVALUATION COMPLETE ==========")


if __name__ == "__main__":
    evaluate()

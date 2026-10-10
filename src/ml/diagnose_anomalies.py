
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = ROOT / "data/synthetic/bank_transactions.csv"
ANOMALIES_PATH = ROOT / "data/processed/subscription_anomalies.csv"


def diagnose():
    raw = pd.read_csv(RAW_PATH)
    predictions = pd.read_csv(ANOMALIES_PATH)

    actual_duplicates = raw[
        raw["event_type_ground_truth"] == "duplicate"
    ].copy()

    predicted_duplicates = predictions[
        predictions["anomaly_type"] == "duplicate_charge"
    ].copy()

    actual_ids = set(
        actual_duplicates["transaction_id"].astype(str)
    )

    predicted_ids = set(
        predicted_duplicates["transaction_id"].astype(str)
    )

    true_positives = actual_ids & predicted_ids
    false_positives = predicted_ids - actual_ids
    false_negatives = actual_ids - predicted_ids

    print("\n========== ANOMALY DIAGNOSIS ==========")

    print("\nACTUAL DUPLICATE EVENTS:")
    print(
        actual_duplicates[
            [
                "transaction_id",
                "transaction_date",
                "description",
                "amount",
                "merchant_ground_truth",
            ]
        ].to_string(index=False)
    )

    print("\nPREDICTED DUPLICATE EVENTS:")
    print(
        predicted_duplicates[
            [
                "transaction_id",
                "transaction_date",
                "merchant_name",
                "amount",
            ]
        ].to_string(index=False)
    )

    print("\nTRUE POSITIVES:", len(true_positives))
    print("FALSE POSITIVES:", len(false_positives))
    print("FALSE NEGATIVES:", len(false_negatives))

    print("\nFALSE POSITIVE IDS:")
    print(sorted(false_positives))

    print("\nMISSED DUPLICATE IDS:")
    print(sorted(false_negatives))

    print("\n========== DIAGNOSIS COMPLETE ==========")


if __name__ == "__main__":
    diagnose()

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

NORMALIZED_PATH = (
    ROOT / "data/processed/normalized_transactions.parquet"
)

RAW_PATH = (
    ROOT / "data/synthetic/bank_transactions.csv"
)


def inspect():
    normalized = pd.read_parquet(NORMALIZED_PATH)
    raw = pd.read_csv(RAW_PATH)

    # Ground truth is used here only for offline diagnosis.
    planet = normalized[
        normalized["normalized_merchant"] == "PLANET FITNESS"
    ].copy()

    planet = planet.merge(
        raw[["transaction_id", "event_type_ground_truth"]],
        on="transaction_id",
        how="left",
        validate="one_to_one",
    )

    planet["transaction_date"] = pd.to_datetime(
        planet["transaction_date"]
    )

    planet = planet.sort_values(
        ["transaction_date", "transaction_id"]
    )

    print("\n========== PLANET FITNESS TRANSACTIONS ==========")

    print(
        planet[
            [
                "transaction_date",
                "amount",
                "transaction_type",
                "event_type_ground_truth",
            ]
        ].to_string(index=False)
    )

    print("\n========== INSPECTION COMPLETE ==========")


if __name__ == "__main__":
    inspect()
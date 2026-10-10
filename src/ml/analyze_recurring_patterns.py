
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "normalized_transactions.parquet"
)

df = pd.read_parquet(INPUT_PATH)

df["transaction_date"] = pd.to_datetime(
    df["transaction_date"]
)

df["amount"] = pd.to_numeric(
    df["amount"], errors="coerce"
)

# Analyze transactions without using ground-truth labels.
df = df.drop(
    columns=[
        "merchant_ground_truth",
        "is_subscription_ground_truth",
        "event_type_ground_truth",
    ],
    errors="ignore",
)

merchants = [
    "DOORDASH",
    "NETFLIX",
    "SPOTIFY",
    "MICROSOFT 365",
]

for merchant in merchants:
    group = df[
        df["normalized_merchant"] == merchant
    ].sort_values("transaction_date")

    print(f"\n========== {merchant} ==========")
    print(f"Total transactions: {len(group)}")

    print(
        group[
            [
                "transaction_date",
                "description",
                "amount",
                "transaction_type",
            ]
        ].head(25).to_string(index=False)
    )

    print("\nAmount distribution:")
    print(group["amount"].describe().round(2))

    print("\nTransactions per month:")
    print(
        group.groupby(
            group["transaction_date"].dt.to_period("M")
        ).size().head(12).to_string()
    )

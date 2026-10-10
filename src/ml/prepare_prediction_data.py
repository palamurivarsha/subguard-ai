
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "normalized_transactions.parquet"
)

SUBSCRIPTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_subscriptions.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "ml_prediction_training_data.csv"
)

transactions = pd.read_parquet(TRANSACTIONS_PATH)
subscriptions = pd.read_csv(SUBSCRIPTIONS_PATH)

# Never use ground-truth columns as ML features.
transactions = transactions.drop(
    columns=[
        "merchant_ground_truth",
        "is_subscription_ground_truth",
        "event_type_ground_truth",
    ],
    errors="ignore",
)

transactions["transaction_date"] = pd.to_datetime(
    transactions["transaction_date"]
)

transactions["amount"] = pd.to_numeric(
    transactions["amount"], errors="coerce"
)

# Use detected subscription merchants only.
transactions = transactions[
    transactions["normalized_merchant"].isin(
        subscriptions["merchant_name"]
    )
].copy()

# Keep outgoing charges, excluding zero-value trial starts.
transactions = transactions[
    (transactions["transaction_type"].str.lower() == "debit")
    & (transactions["amount"] < 0)
].copy()

transactions["charge_amount"] = transactions["amount"].abs()

# Remove duplicate payment observations.
transactions = transactions.drop_duplicates(
    subset=[
        "normalized_merchant",
        "transaction_date",
        "charge_amount",
    ]
)

transactions = transactions.sort_values(
    ["normalized_merchant", "transaction_date"]
)

grouped = transactions.groupby("normalized_merchant")

# Features available at the current charge.
transactions["previous_charge_date"] = grouped[
    "transaction_date"
].shift(1)

transactions["previous_amount"] = grouped[
    "charge_amount"
].shift(1)

transactions["days_since_previous_charge"] = (
    transactions["transaction_date"]
    - transactions["previous_charge_date"]
).dt.days

transactions["amount_change"] = (
    transactions["charge_amount"]
    - transactions["previous_amount"]
)

transactions["billing_day"] = (
    transactions["transaction_date"].dt.day
)

transactions["billing_month"] = (
    transactions["transaction_date"].dt.month
)

# Labels: information from the NEXT charge.
transactions["next_charge_date"] = grouped[
    "transaction_date"
].shift(-1)

transactions["next_charge_amount"] = grouped[
    "charge_amount"
].shift(-1)

transactions["days_until_next_charge"] = (
    transactions["next_charge_date"]
    - transactions["transaction_date"]
).dt.days

# Keep rows with complete historical features and labels.
training_data = transactions.dropna(
    subset=[
        "days_since_previous_charge",
        "previous_amount",
        "days_until_next_charge",
        "next_charge_amount",
    ]
).copy()

training_data.to_csv(OUTPUT_PATH, index=False)

print("\n========== ML TRAINING DATA ==========")

print(f"Training examples: {len(training_data)}")

print("\nExamples by merchant:")
print(
    training_data["normalized_merchant"]
    .value_counts()
    .to_string()
)

print("\nSample training rows:")
print(
    training_data[
        [
            "normalized_merchant",
            "transaction_date",
            "charge_amount",
            "days_since_previous_charge",
            "days_until_next_charge",
            "next_charge_amount",
        ]
    ].head(15).to_string(index=False)
)

print(f"\nSaved to: {OUTPUT_PATH}")
print("\n========== DATA PREPARATION COMPLETE ==========")


from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "normalized_transactions.parquet"
)

ORIGINAL_DATA_PATH = (
    PROJECT_ROOT / "data" / "synthetic"
    / "bank_transactions.csv"
)

DETECTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_subscriptions.csv"
)

# Load normalized transactions and detector predictions
transactions = pd.read_parquet(TRANSACTIONS_PATH)
detections = pd.read_csv(DETECTIONS_PATH)

# Load labels separately, strictly for evaluation
original = pd.read_csv(
    ORIGINAL_DATA_PATH,
    usecols=[
        "transaction_id",
        "is_subscription_ground_truth",
    ],
)

# Join labels by transaction ID, never by row position
transactions = transactions.merge(
    original,
    on="transaction_id",
    how="left",
    validate="one_to_one",
)

if transactions["is_subscription_ground_truth"].isna().any():
    raise ValueError("Some transactions have no ground-truth labels.")

# Convert labels into booleans
actual_positive = (
    transactions["is_subscription_ground_truth"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

# Ground truth is used only for offline evaluation
actual_merchants = set(
    transactions.loc[
        actual_positive, "normalized_merchant"
    ].dropna()
)

predicted_merchants = set(
    detections["merchant_name"].dropna()
)

all_merchants = set(
    transactions["normalized_merchant"].dropna()
)

tp = len(actual_merchants & predicted_merchants)
fp = len(predicted_merchants - actual_merchants)
fn = len(actual_merchants - predicted_merchants)
tn = len(all_merchants - (actual_merchants | predicted_merchants))

precision = tp / (tp + fp) if tp + fp else 0.0
recall = tp / (tp + fn) if tp + fn else 0.0

f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0.0
)

print("\n========== SUBSCRIPTION DETECTION EVALUATION ==========")

print(f"Actual subscription merchants: {len(actual_merchants)}")
print(f"Predicted subscription merchants: {len(predicted_merchants)}")

print(f"\nTrue positives: {tp}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")
print(f"True negatives: {tn}")

print(f"\nPrecision: {precision:.2%}")
print(f"Recall: {recall:.2%}")
print(f"F1-score: {f1:.2%}")

print("\nMissed merchants:")
print(sorted(actual_merchants - predicted_merchants))

print("\nIncorrectly detected merchants:")
print(sorted(predicted_merchants - actual_merchants))

print("\n========== EVALUATION COMPLETE ==========")

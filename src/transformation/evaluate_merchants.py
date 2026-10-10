
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

# Compare predicted merchants against ground truth
predicted = df["normalized_merchant"].fillna("").str.upper().str.strip()
actual = df["merchant_ground_truth"].fillna("").str.upper().str.strip()

errors = df[predicted != actual].copy()

print("\n========== MERCHANT ERROR ANALYSIS ==========")

print(f"Total transactions: {len(df)}")
print(f"Correct predictions: {len(df) - len(errors)}")
print(f"Incorrect predictions: {len(errors)}")

print("\nTop incorrectly predicted merchants:")

print(
    errors.groupby(
        ["merchant_ground_truth", "normalized_merchant"]
    )
    .size()
    .sort_values(ascending=False)
    .head(20)
    .to_string()
)

print("\nSample incorrect descriptions:")

print(
    errors[
        [
            "description",
            "merchant_ground_truth",
            "normalized_merchant"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

# Save errors for analysis
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "merchant_errors.csv"
)

errors.to_csv(OUTPUT_PATH, index=False)

print(f"\nError report saved to: {OUTPUT_PATH}")

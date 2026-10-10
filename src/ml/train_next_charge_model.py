
from pathlib import Path
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "ml_prediction_training_data.csv"
)

df = pd.read_csv(INPUT_PATH)

df["transaction_date"] = pd.to_datetime(
    df["transaction_date"]
)

# Exclude merchants with insufficient examples.
merchant_counts = df["normalized_merchant"].value_counts()

df = df[
    df["normalized_merchant"].map(merchant_counts) >= 5
].copy()

features = [
    "charge_amount",
    "previous_amount",
    "days_since_previous_charge",
    "amount_change",
    "billing_day",
    "billing_month",
]

target = "days_until_next_charge"

# Use chronological splitting rather than random splitting.
df = df.sort_values("transaction_date")

split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index]
test_df = df.iloc[split_index:]

X_train = train_df[features]
y_train = train_df[target]

X_test = test_df[features]
y_test = test_df[target]

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=6,
    random_state=42,
    min_samples_leaf=2,
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

ml_mae = mean_absolute_error(y_test, predictions)

# Simple 30-day baseline for comparison.
baseline_predictions = [30] * len(y_test)

baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions,
)

print("\n========== ML NEXT-CHARGE MODEL ==========")

print(f"Training examples: {len(train_df)}")
print(f"Testing examples: {len(test_df)}")

print(f"\nRandom Forest MAE: {ml_mae:.2f} days")
print(f"30-day Baseline MAE: {baseline_mae:.2f} days")

print("\nSample predictions:")
comparison = test_df[
    ["normalized_merchant", "transaction_date"]
].copy()

comparison["actual_days"] = y_test.values
comparison["predicted_days"] = predictions.round(1)

print(comparison.head(15).to_string(index=False))

print("\n========== MODEL TRAINING COMPLETE ==========")

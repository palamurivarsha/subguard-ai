
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SUBSCRIPTIONS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_subscriptions.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "next_charge_predictions.csv"
)


def predict_next_charges():
    print("\n========== SUBGUARD NEXT-CHARGE PREDICTION ==========")

    subscriptions = pd.read_csv(SUBSCRIPTIONS_PATH)

    predictions = []

    for _, row in subscriptions.iterrows():
        merchant = row["merchant_name"]
        frequency = row["billing_frequency"]

        last_charge_date = pd.to_datetime(
            row["last_seen_date"]
        )

        latest_amount = float(row["latest_amount"])

        if frequency == "MONTHLY":
            next_date = last_charge_date + pd.DateOffset(months=1)
        elif frequency == "ANNUAL":
            next_date = last_charge_date + pd.DateOffset(years=1)
        else:
            continue

        predictions.append({
            "merchant_name": merchant,
            "billing_frequency": frequency,
            "last_charge_date": str(last_charge_date.date()),
            "predicted_next_charge_date": str(next_date.date()),
            "predicted_next_amount": round(latest_amount, 2),
            "detection_confidence": row["detection_confidence"],
        })

    result = pd.DataFrame(predictions)

    result.to_csv(OUTPUT_PATH, index=False)

    print("\n========== NEXT-CHARGE PREDICTIONS ==========")
    print(result.to_string(index=False))

    print(f"\nPredictions generated: {len(result)}")
    print(f"Saved to: {OUTPUT_PATH}")
    print("\n========== PREDICTION COMPLETE ==========")


if __name__ == "__main__":
    predict_next_charges()

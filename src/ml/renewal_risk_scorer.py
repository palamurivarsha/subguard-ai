
from pathlib import Path
from datetime import date
import argparse
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PREDICTIONS_PATH = (
    PROJECT_ROOT / "data/processed/next_charge_predictions.csv"
)
ANOMALIES_PATH = (
    PROJECT_ROOT / "data/processed/subscription_anomalies.csv"
)
OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/renewal_risk_scores.csv"
)


def urgency_points(days_until):
    if days_until < 0:
        return 0
    if days_until <= 3:
        return 40
    if days_until <= 7:
        return 30
    if days_until <= 14:
        return 20
    if days_until <= 30:
        return 10
    return 0


def amount_points(amount):
    if amount >= 75:
        return 20
    if amount >= 25:
        return 15
    if amount >= 10:
        return 10
    return 5


def risk_level(score):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def calculate_risk_scores(as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()

    predictions = pd.read_csv(PREDICTIONS_PATH)
    anomalies = pd.read_csv(ANOMALIES_PATH)

    predictions["predicted_next_charge_date"] = pd.to_datetime(
        predictions["predicted_next_charge_date"],
        errors="coerce"
    )
    predictions["predicted_next_amount"] = pd.to_numeric(
        predictions["predicted_next_amount"],
        errors="coerce"
    )

    predictions["detection_confidence"] = pd.to_numeric(
        predictions["detection_confidence"],
        errors="coerce"
    )

    anomalies["transaction_date"] = pd.to_datetime(
        anomalies["transaction_date"],
        errors="coerce"
    )

    # Avoid using anomalies that happened after the scoring date.
    historical_anomalies = anomalies[
        anomalies["transaction_date"].notna()
        & (anomalies["transaction_date"].dt.date <= as_of_date)
    ].copy()

    results = []

    for _, subscription in predictions.iterrows():
        merchant = subscription["merchant_name"]
        renewal_date = subscription["predicted_next_charge_date"]
        amount = subscription["predicted_next_amount"]
        confidence = subscription["detection_confidence"]

        if pd.isna(renewal_date) or pd.isna(amount):
            print(f"Skipping {merchant}: missing prediction data")
            continue

        if amount < 0:
            print(f"Skipping {merchant}: invalid amount")
            continue

        days_until = (renewal_date.date() - as_of_date).days

        urgency = urgency_points(days_until)
        financial_impact = amount_points(float(amount))

        merchant_anomalies = historical_anomalies[
            historical_anomalies["merchant_name"] == merchant
        ]

        anomaly_types = set(
            merchant_anomalies["anomaly_type"].dropna()
        )

        anomaly_score = 0

        if "duplicate_charge" in anomaly_types:
            anomaly_score += 15

        if "price_increase" in anomaly_types:
            anomaly_score += 15
        elif "unusual_amount" in anomaly_types:
            anomaly_score += 10

        anomaly_score = min(anomaly_score, 30)

        if pd.isna(confidence):
            confidence_score = 10
        else:
            confidence = max(0.0, min(1.0, float(confidence)))
            confidence_score = round((1 - confidence) * 10)

        total_score = min(
            100,
            urgency
            + financial_impact
            + anomaly_score
            + confidence_score
        )

        reasons = []

        if days_until < 0:
            reasons.append(
                "Predicted renewal date has passed; refresh prediction"
            )
        elif days_until <= 7:
            reasons.append("Renewal expected within 7 days")
        elif days_until <= 30:
            reasons.append("Renewal expected within 30 days")

        if amount >= 75:
            reasons.append("High expected charge amount")

        if "duplicate_charge" in anomaly_types:
            reasons.append("Historical duplicate charge detected")

        if "price_increase" in anomaly_types:
            reasons.append("Historical price increase detected")

        if "unusual_amount" in anomaly_types:
            reasons.append("Historical unusual charge detected")

        if confidence_score > 0:
            reasons.append("Lower subscription detection confidence")

        if not reasons:
            reasons.append("No immediate review signals")

        results.append({
            "merchant_name": merchant,
            "as_of_date": as_of_date.isoformat(),
            "predicted_next_charge_date": renewal_date.date().isoformat(),
            "days_until_renewal": days_until,
            "predicted_next_amount": round(float(amount), 2),
            "urgency_score": urgency,
            "amount_score": financial_impact,
            "anomaly_score": anomaly_score,
            "confidence_score": confidence_score,
            "risk_score": total_score,
            "risk_level": risk_level(total_score),
            "needs_prediction_refresh": days_until < 0,
            "risk_reasons": "; ".join(reasons),
        })

    result = pd.DataFrame(results)

    if not result.empty:
        result = result.sort_values(
            ["risk_score", "predicted_next_amount"],
            ascending=[False, False]
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\n========== SUBGUARD RENEWAL RISK SCORING ==========")
    print("As-of date:", as_of_date)
    print("Subscriptions scored:", len(result))

    if not result.empty:
        print(
            result[
                [
                    "merchant_name",
                    "days_until_renewal",
                    "predicted_next_amount",
                    "risk_score",
                    "risk_level",
                    "needs_prediction_refresh",
                ]
            ].to_string(index=False)
        )

    print("\nSaved to:", OUTPUT_PATH)
    print("========== RISK SCORING COMPLETE ==========")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        dest="as_of",
        default=date.today().isoformat(),
        help="Scoring date in YYYY-MM-DD format"
    )

    args = parser.parse_args()
    calculate_risk_scores(date.fromisoformat(args.as_of))

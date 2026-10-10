
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "normalized_transactions.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_subscriptions.csv"
)


def detect_subscriptions():
    print("\n========== SUBGUARD SUBSCRIPTION DETECTOR V2 ==========")

    df = pd.read_parquet(INPUT_PATH)
    print(f"Total transactions loaded: {len(df)}")

    # Ground-truth columns are evaluation-only.
    df = df.drop(
        columns=[
            "merchant_ground_truth",
            "is_subscription_ground_truth",
            "event_type_ground_truth",
        ],
        errors="ignore",
    )

    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"]
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    types = df["transaction_type"].astype(str).str.lower().str.strip()

    payments = df[
        (types == "debit")
        & (df["amount"] < 0)
    ].copy()

    payments["charge_amount"] = payments["amount"].abs()

    print(f"Outgoing transactions: {len(payments)}")

    subscriptions = []

    for merchant, group in payments.groupby("normalized_merchant"):
        if merchant == "UNKNOWN":
            continue

        group = group.sort_values("transaction_date").copy()

        # Remove exact duplicate payment observations.
        group = group.drop_duplicates(
            subset=["transaction_date", "charge_amount"]
        )

        if len(group) < 2:
            continue

        dates = group["transaction_date"]
        amounts = group["charge_amount"]

        gaps = dates.diff().dt.days.dropna()
        median_amount = amounts.median()


# Check whether consecutive charges have stable amounts.
# This supports subscriptions with a permanent price increase.
        amount_changes = amounts.diff().abs().dropna()

        previous_amounts = amounts.shift(1).dropna()

        allowed_changes = previous_amounts.apply(
            lambda value: max(2.0, value * 0.20)
        )

        if len(amount_changes) > 0:
            amount_stability = float(
                (amount_changes <= allowed_changes).mean()
            )
        else:
            amount_stability = 0.0


        monthly_matches = float(
            gaps.between(25, 35).mean()
        )

        # Also allow a skipped billing month.
        skipped_month_matches = float(
            gaps.between(55, 65).mean()
        )

        monthly_pattern = (
            monthly_matches + skipped_month_matches
        )

        annual_matches = float(
            gaps.between(350, 380).mean()
        )

        # Multiple purchases per month suggest
        # ordinary shopping rather than subscriptions.
        monthly_counts = group.groupby(
            group["transaction_date"].dt.to_period("M")
        ).size()

        single_charge_ratio = float(
            (monthly_counts == 1).mean()
        )

        billing_frequency = None
        confidence = 0.0

        # Monthly subscription candidate
        if (
            len(group) >= 3
            and monthly_pattern >= 0.70
            and amount_stability >= 0.70
            and single_charge_ratio >= 0.80
        ):
            billing_frequency = "MONTHLY"

            confidence = (
                0.40 * monthly_pattern
                + 0.35 * amount_stability
                + 0.25 * single_charge_ratio
            )

        # Annual subscription candidate
        elif (
            annual_matches >= 0.80
            and amount_stability >= 0.80
            and single_charge_ratio >= 0.80
        ):
            billing_frequency = "ANNUAL"

            confidence = (
                0.45 * annual_matches
                + 0.35 * amount_stability
                + 0.20 * single_charge_ratio
            )

        if billing_frequency is not None:
            subscriptions.append({
                "merchant_name": merchant,
                "billing_frequency": billing_frequency,
                "average_amount": round(
                    float(amounts.mean()), 2
                ),
                "latest_amount": round(
                    float(amounts.iloc[-1]), 2
                ),
                "first_seen_date": str(
                    dates.min().date()
                ),
                "last_seen_date": str(
                    dates.max().date()
                ),
                "detection_confidence": round(
                    float(confidence), 3
                ),
                "transaction_count": len(group),
            })

    columns = [
        "merchant_name",
        "billing_frequency",
        "average_amount",
        "latest_amount",
        "first_seen_date",
        "last_seen_date",
        "detection_confidence",
        "transaction_count",
    ]

    result = pd.DataFrame(subscriptions, columns=columns)

    if not result.empty:
        result = result.sort_values(
            "detection_confidence",
            ascending=False,
        )

    result.to_csv(OUTPUT_PATH, index=False)

    print("\n========== DETECTED SUBSCRIPTIONS ==========")

    if result.empty:
        print("No subscriptions detected.")
    else:
        print(result.to_string(index=False))

    print(f"\nSubscriptions detected: {len(result)}")
    print(f"Saved to: {OUTPUT_PATH}")
    print("\n========== DETECTION COMPLETE ==========")


if __name__ == "__main__":
    detect_subscriptions()

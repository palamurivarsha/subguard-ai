
from pathlib import Path
import pandas as pd

# ==========================================
# SUBGUARD AI - ANOMALY DETECTION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_PATH = (
    PROJECT_ROOT / "data/processed/normalized_transactions.parquet"
)

SUBSCRIPTIONS_PATH = (
    PROJECT_ROOT / "data/processed/detected_subscriptions.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/subscription_anomalies.csv"
)

ANOMALY_COLUMNS = [
    "transaction_id",
    "merchant_name",
    "transaction_date",
    "amount",
    "anomaly_type",
    "previous_amount",
    "percentage_change",
    "description",
]


def detect_anomalies():

    # --------------------------------------
    # 1. Load processed data
    # --------------------------------------

    transactions = pd.read_parquet(TRANSACTIONS_PATH)
    subscriptions = pd.read_csv(SUBSCRIPTIONS_PATH)

    print("\n========== SUBGUARD ANOMALY DETECTION ==========")

    # --------------------------------------
    # 2. Filter detected subscription merchants
    # --------------------------------------

    subscription_merchants = set(
        subscriptions["merchant_name"].dropna().astype(str)
    )

    print(
        "Subscription merchants:",
        sorted(subscription_merchants)
    )

    transactions = transactions[
        transactions["normalized_merchant"].isin(
            subscription_merchants
        )
    ].copy()

    # --------------------------------------
    # 3. Prepare transaction data
    # --------------------------------------

    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"],
        errors="coerce"
    )

    transactions["amount"] = pd.to_numeric(
        transactions["amount"],
        errors="coerce"
    )

    transactions = transactions.dropna(
        subset=["transaction_date", "amount"]
    )

    transactions = transactions.sort_values(
        [
            "normalized_merchant",
            "transaction_date",
            "transaction_id"
        ]
    )

    print(
        f"Subscription transactions analyzed: {len(transactions)}"
    )

    anomalies = []

    # --------------------------------------
    # 4. Analyze each subscription merchant
    # --------------------------------------

    for merchant, group in transactions.groupby(
        "normalized_merchant"
    ):

        previous_charges = []

        for _, transaction in group.iterrows():

            raw_amount = float(transaction["amount"])
            date = transaction["transaction_date"]

            transaction_type = str(
                transaction["transaction_type"]
            ).strip().lower()

            # ----------------------------------
            # 5. Exclude credits and refunds
            # ----------------------------------

            # Our synthetic dataset uses:
            # debit + negative amount = charge
            # credit + positive amount = refund

            if transaction_type != "debit" or raw_amount >= 0:
                continue

            amount = abs(raw_amount)

            # ----------------------------------
            # 6. Detect duplicate charges
            # ----------------------------------

            is_duplicate = False

            for previous in reversed(previous_charges):

                days_difference = (
                    date - previous["date"]
                ).total_seconds() / 86400

                if days_difference > 3:
                    break

                if (
                    0 <= days_difference <= 3
                    and abs(
                        amount - previous["amount"]
                    ) < 0.01
                ):
                    is_duplicate = True
                    break

            if is_duplicate:

                anomalies.append({
                    "transaction_id": transaction["transaction_id"],
                    "merchant_name": merchant,
                    "transaction_date": date.date(),
                    "amount": amount,
                    "anomaly_type": "duplicate_charge",
                    "previous_amount": amount,
                    "percentage_change": 0.0,
                    "description": (
                        "Possible duplicate subscription "
                        "charge within 3 days."
                    ),
                })

                # Do not let duplicate charges distort
                # historical subscription price.
                continue

            # ----------------------------------
            # 7. Detect subscription price changes
            # ----------------------------------

            # Require at least 3 earlier valid charges.
            if len(previous_charges) >= 3:

                # Compare against the latest charge.
                # This prevents repeatedly flagging
                # the same permanent price increase.
                baseline = previous_charges[-1]["amount"]

                if baseline > 0:

                    percentage_change = (
                        (amount - baseline) / baseline
                    ) * 100

                    anomaly_type = None

                    # Price increase of 15% or more.
                    if percentage_change >= 15:
                        anomaly_type = "price_increase"

                    # Other significant amount changes.
                    elif abs(percentage_change) >= 20:
                        anomaly_type = "unusual_amount"

                    if anomaly_type:

                        anomalies.append({
                            "transaction_id": transaction[
                                "transaction_id"
                            ],
                            "merchant_name": merchant,
                            "transaction_date": date.date(),
                            "amount": amount,
                            "anomaly_type": anomaly_type,
                            "previous_amount": round(
                                baseline, 2
                            ),
                            "percentage_change": round(
                                percentage_change, 2
                            ),
                            "description": (
                                f"Charge differs from previous "
                                f"amount of ${baseline:.2f}."
                            ),
                        })

            # ----------------------------------
            # 8. Update valid charge history
            # ----------------------------------

            previous_charges.append({
                "date": date,
                "amount": amount,
            })

    # --------------------------------------
    # 9. Save anomaly detection results
    # --------------------------------------

    result = pd.DataFrame(
        anomalies,
        columns=ANOMALY_COLUMNS
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # --------------------------------------
    # 10. Display results
    # --------------------------------------

    print(f"\nAnomalies detected: {len(result)}")

    if not result.empty:

        print("\nAnomalies by type:")

        print(
            result["anomaly_type"]
            .value_counts()
            .to_string()
        )

        print("\nDetected anomalies:")

        print(
            result[
                [
                    "merchant_name",
                    "transaction_date",
                    "amount",
                    "anomaly_type",
                    "percentage_change",
                ]
            ].to_string(index=False)
        )

    print(f"\nSaved to: {OUTPUT_PATH}")

    print(
        "========== ANOMALY DETECTION COMPLETE =========="
    )


if __name__ == "__main__":
    detect_anomalies()

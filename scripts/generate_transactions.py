from pathlib import Path
import random
import uuid

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
Faker.seed(SEED)

fake = Faker()

START_DATE = pd.Timestamp("2025-01-01")
END_DATE = pd.Timestamp("2026-09-30")


# ============================================================
# SUBSCRIPTIONS
# ============================================================

SUBSCRIPTIONS = [
    {
        "merchant": "Netflix",
        "descriptions": [
            "NETFLIX.COM",
            "NETFLIX *STREAMING",
            "NETFLIX 866-579-7172",
        ],
        "amount": 17.99,
        "billing_day": 10,
        "frequency": "monthly",
    },
    {
        "merchant": "Spotify",
        "descriptions": [
            "SPOTIFY USA",
            "SPOTIFY *PREMIUM",
            "SPOTIFY P123456",
        ],
        "amount": 11.99,
        "billing_day": 15,
        "frequency": "monthly",
    },
    {
        "merchant": "iCloud",
        "descriptions": [
            "APPLE.COM/BILL",
            "APPLE ICLOUD",
            "APL*ICLOUD STORAGE",
        ],
        "amount": 2.99,
        "billing_day": 5,
        "frequency": "monthly",
    },
    {
        "merchant": "Adobe",
        "descriptions": [
            "ADOBE *CREATIVE CLOUD",
            "ADOBE SYSTEMS",
            "ADOBE CC",
        ],
        "amount": 22.99,
        "billing_day": 20,
        "frequency": "monthly",
    },
    {
        "merchant": "Planet Fitness",
        "descriptions": [
            "PLANET FITNESS",
            "PLANETFITNESS CLUB",
            "PF MEMBERSHIP",
        ],
        "amount": 24.99,
        "billing_day": 17,
        "frequency": "monthly",
    },
]


# ============================================================
# NORMAL NON-SUBSCRIPTION MERCHANTS
# ============================================================

NORMAL_MERCHANTS = [
    "WALMART SUPERCENTER",
    "TARGET",
    "AMAZON MARKETPLACE",
    "SHELL OIL",
    "STARBUCKS",
    "CHIPOTLE",
    "CVS PHARMACY",
    "WALGREENS",
    "KROGER",
    "UBER",
    "DOORDASH",
    "HOME DEPOT",
]


# ============================================================
# HELPER FUNCTION
# ============================================================

def create_transaction(
    date,
    description,
    amount,
    merchant,
    is_subscription,
    event_type="purchase",
):
    return {
        "transaction_id": str(uuid.uuid4()),
        "transaction_date": date.date(),
        "description": description,
        "amount": round(amount, 2),
        "transaction_type": (
            "credit" if amount > 0 else "debit"
        ),
        "merchant_ground_truth": merchant,
        "is_subscription_ground_truth": is_subscription,
        "event_type_ground_truth": event_type,
    }


# ============================================================
# MONTHLY SUBSCRIPTIONS
# ============================================================

def generate_subscription_transactions():

    transactions = []

    months = pd.date_range(
        START_DATE,
        END_DATE,
        freq="MS",
    )

    for subscription in SUBSCRIPTIONS:

        current_amount = subscription["amount"]

        for month_number, month in enumerate(months):

            # Occasionally simulate a missed/failed billing month.
            if random.random() < 0.03:
                continue

            # Billing date can move by +/- 2 days.
            date_variation = random.choice(
                [-2, -1, 0, 0, 0, 1, 2]
            )

            billing_date = (
                month
                + pd.Timedelta(
                    days=subscription["billing_day"] - 1
                )
                + pd.Timedelta(days=date_variation)
            )

            if (
                billing_date < START_DATE
                or billing_date > END_DATE
            ):
                continue

            # ------------------------------------------------
            # PRICE INCREASE
            # ------------------------------------------------
            # Netflix increases after about one year.
            if (
                subscription["merchant"] == "Netflix"
                and month_number == 12
            ):
                current_amount += 5.00

            description = random.choice(
                subscription["descriptions"]
            )

            transaction = create_transaction(
                date=billing_date,
                description=description,
                amount=-current_amount,
                merchant=subscription["merchant"],
                is_subscription=1,
                event_type="subscription_charge",
            )

            transactions.append(transaction)

            # ------------------------------------------------
            # OCCASIONAL REFUND
            # ------------------------------------------------

            if random.random() < 0.02:

                refund_date = (
                    billing_date
                    + pd.Timedelta(
                        days=random.randint(1, 5)
                    )
                )

                if refund_date <= END_DATE:

                    transactions.append(
                        create_transaction(
                            date=refund_date,
                            description=(
                                description + " REFUND"
                            ),
                            amount=current_amount,
                            merchant=subscription["merchant"],
                            is_subscription=1,
                            event_type="refund",
                        )
                    )

    return transactions


# ============================================================
# FREE TRIAL -> PAID SUBSCRIPTION
# ============================================================

def generate_free_trial():

    transactions = []

    merchant = "Canva"

    trial_start = pd.Timestamp("2026-07-01")

    transactions.append(
        create_transaction(
            date=trial_start,
            description="CANVA PRO FREE TRIAL",
            amount=0.00,
            merchant=merchant,
            is_subscription=1,
            event_type="free_trial_start",
        )
    )

    # Trial converts to paid after 30 days.
    first_charge = trial_start + pd.Timedelta(days=30)

    charge_dates = pd.date_range(
        first_charge,
        END_DATE,
        freq=pd.DateOffset(months=1),
    )

    descriptions = [
        "CANVA PRO",
        "CANVA*PRO",
        "CANVA PTY LTD",
    ]

    for charge_date in charge_dates:

        transactions.append(
            create_transaction(
                date=charge_date,
                description=random.choice(descriptions),
                amount=-14.99,
                merchant=merchant,
                is_subscription=1,
                event_type="trial_conversion_charge",
            )
        )

    return transactions


# ============================================================
# ANNUAL SUBSCRIPTION
# ============================================================

def generate_annual_subscription():

    transactions = []

    dates = [
        pd.Timestamp("2025-03-12"),
        pd.Timestamp("2026-03-12"),
    ]

    descriptions = [
        "MICROSOFT 365",
        "MSFT *MICROSOFT 365",
        "MICROSOFT*SUBSCRIPTION",
    ]

    for date in dates:

        transactions.append(
            create_transaction(
                date=date,
                description=random.choice(descriptions),
                amount=-99.99,
                merchant="Microsoft 365",
                is_subscription=1,
                event_type="annual_subscription",
            )
        )

    return transactions


# ============================================================
# NORMAL EVERYDAY TRANSACTIONS
# ============================================================

def generate_normal_transactions():

    transactions = []

    dates = pd.date_range(
        START_DATE,
        END_DATE,
        freq="D",
    )

    for date in dates:

        number_of_transactions = np.random.randint(
            0,
            4,
        )

        for _ in range(number_of_transactions):

            merchant = random.choice(
                NORMAL_MERCHANTS
            )

            amount = np.random.uniform(
                4.00,
                150.00,
            )

            transactions.append(
                create_transaction(
                    date=date,
                    description=merchant,
                    amount=-amount,
                    merchant=merchant,
                    is_subscription=0,
                    event_type="normal_purchase",
                )
            )

    return transactions


# ============================================================
# DUPLICATE / NOISY TRANSACTIONS
# ============================================================

def add_duplicate_noise(transactions):

    noisy_transactions = []

    # Small percentage of transactions appear duplicated.
    sample_size = max(
        1,
        int(len(transactions) * 0.005),
    )

    selected = random.sample(
        transactions,
        sample_size,
    )

    for transaction in selected:

        duplicate = transaction.copy()

        # Give duplicate its own transaction ID.
        duplicate["transaction_id"] = str(
            uuid.uuid4()
        )

        duplicate["event_type_ground_truth"] = (
            "duplicate"
        )

        noisy_transactions.append(duplicate)

    return noisy_transactions


# ============================================================
# MAIN DATASET GENERATOR
# ============================================================

def main():

    subscription_transactions = (
        generate_subscription_transactions()
    )

    trial_transactions = (
        generate_free_trial()
    )

    annual_transactions = (
        generate_annual_subscription()
    )

    normal_transactions = (
        generate_normal_transactions()
    )

    transactions = (
        subscription_transactions
        + trial_transactions
        + annual_transactions
        + normal_transactions
    )

    duplicate_transactions = (
        add_duplicate_noise(transactions)
    )

    transactions.extend(
        duplicate_transactions
    )

    df = pd.DataFrame(transactions)

    df = df.sort_values(
        "transaction_date"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # SAVE DATASET
    # --------------------------------------------------------

    project_root = (
        Path(__file__).resolve().parents[1]
    )

    output_directory = (
        project_root
        / "data"
        / "synthetic"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_directory
        / "bank_transactions.csv"
    )

    df.to_csv(
        output_file,
        index=False,
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\nSubGuard AI synthetic dataset created!")
    print("--------------------------------------")

    print(
        f"Total transactions: {len(df)}"
    )

    print(
        "Subscription-related transactions:",
        int(
            df[
                "is_subscription_ground_truth"
            ].sum()
        ),
    )

    print(
        "\nEvent types:"
    )

    print(
        df[
            "event_type_ground_truth"
        ].value_counts()
    )

    print(
        f"\nDataset saved to:\n{output_file}"
    )


if __name__ == "__main__":
    main()
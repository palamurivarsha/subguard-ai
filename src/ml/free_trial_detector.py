
from pathlib import Path
import pandas as pd
from datetime import timedelta


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT / "data" / "synthetic"
    / "bank_transactions.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_free_trials.csv"
)

# Demo defaults, not verified subscription terms.
DEFAULT_TRIAL_DAYS = 14

TRIAL_KEYWORDS = [
    "free trial",
    "trial start",
    "trial started",
    "trial activation",
    "trial activated",
]

def detect_free_trials():
    print("\n========== SUBGUARD FREE-TRIAL DETECTOR ==========")

    df = pd.read_csv(INPUT_PATH)

    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"]
    )

    # Detection uses transaction descriptions only.
    # Ground-truth columns are never used as inputs.
    descriptions = (
        df["description"]
        .fillna("")
        .astype(str)
        .str.lower()
    )

    trial_mask = descriptions.apply(
        lambda description: any(
            keyword in description
            for keyword in TRIAL_KEYWORDS
        )
    )

    trials = df.loc[trial_mask].copy()

    results = []

    for _, row in trials.iterrows():
        start_date = row["transaction_date"]

        estimated_end_date = (
            start_date
            + timedelta(days=DEFAULT_TRIAL_DAYS)
        )

        results.append({
            "transaction_id": row["transaction_id"],
            "merchant_description": row["description"],
            "trial_start_date": start_date.date().isoformat(),
            "estimated_trial_end_date": (
                estimated_end_date.date().isoformat()
            ),
            "trial_duration_days": DEFAULT_TRIAL_DAYS,
            "status": "ESTIMATED",
            "reminder_3_day_date": (
                estimated_end_date
                - timedelta(days=3)
            ).date().isoformat(),
            "reminder_1_day_date": (
                estimated_end_date
                - timedelta(days=1)
            ).date().isoformat(),
        })

    columns = [
        "transaction_id",
        "merchant_description",
        "trial_start_date",
        "estimated_trial_end_date",
        "trial_duration_days",
        "status",
        "reminder_3_day_date",
        "reminder_1_day_date",
    ]

    result = pd.DataFrame(results, columns=columns)

    OUTPUT_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    result.to_csv(OUTPUT_PATH, index=False)

    print(f"Transactions scanned: {len(df)}")
    print(f"Potential free trials found: {len(result)}")

    if not result.empty:
        print("\nDetected free trials:")
        print(result.to_string(index=False))
    else:
        print("\nNo explicit trial-start descriptions found.")

    print(f"\nSaved to: {OUTPUT_PATH}")
    print("\n========== DETECTION COMPLETE ==========")


if __name__ == "__main__":
    detect_free_trials()

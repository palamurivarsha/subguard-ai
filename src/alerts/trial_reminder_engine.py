
from pathlib import Path
from datetime import date, timedelta
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRIALS_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "detected_free_trials.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed"
    / "trial_reminder_candidates.csv"
)


def generate_reminders(today=None):
    if today is None:
        today = date.today()

    print("\n========== SUBGUARD TRIAL REMINDER ENGINE ==========")
    print(f"Evaluation date: {today}")

    trials = pd.read_csv(TRIALS_PATH)

    reminders = []

    for _, trial in trials.iterrows():
        merchant = trial["merchant_description"]
        trial_id = trial["transaction_id"]

        trial_end = date.fromisoformat(
            trial["estimated_trial_end_date"]
        )

        status = str(trial["status"]).upper()

        # Never generate upcoming reminders for expired estimates.
        if trial_end <= today:
            print(f"Skipping past trial: {merchant}")
            continue

        for days_before in [3, 1]:
            reminder_date = trial_end - timedelta(
                days=days_before
            )

            if reminder_date != today:
                continue

            reminders.append({
                "trial_id": trial_id,
                "merchant": merchant,
                "reminder_type": f"{days_before}_DAY",
                "reminder_date": reminder_date.isoformat(),
                "estimated_trial_end_date": trial_end.isoformat(),
                "date_status": status,
                "delivery_status": "DRY_RUN",
            })

    columns = [
        "trial_id",
        "merchant",
        "reminder_type",
        "reminder_date",
        "estimated_trial_end_date",
        "date_status",
        "delivery_status",
    ]

    result = pd.DataFrame(reminders, columns=columns)

    OUTPUT_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    result.to_csv(OUTPUT_PATH, index=False)

    print(f"\nReminders due: {len(result)}")

    if not result.empty:
        print(result.to_string(index=False))
    else:
        print("No reminders due today.")

    print(f"\nSaved to: {OUTPUT_PATH}")
    print("\n========== REMINDER CHECK COMPLETE ==========")


if __name__ == "__main__":
    generate_reminders()
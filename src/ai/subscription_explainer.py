
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RISK_PATH = (
    PROJECT_ROOT / "data/processed/renewal_risk_scores.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/subscription_explanations.csv"
)


def explain_subscription(row):
    merchant = row["merchant_name"]
    amount = float(row["predicted_next_amount"])
    renewal_date = row["predicted_next_charge_date"]
    days = int(row["days_until_renewal"])
    score = int(row["risk_score"])
    level = row["risk_level"]

    explanation = (
        f"{merchant} has a review-priority score of "
        f"{score}/100 ({level}). "
    )

    if days < 0:
        explanation += (
            f"The predicted charge date of {renewal_date} "
            f"has passed. Check for a recent payment and "
            f"refresh the prediction before relying on it. "
        )
    elif days == 0:
        explanation += (
            f"A charge of approximately ${amount:.2f} "
            f"is predicted for today. "
        )
    else:
        explanation += (
            f"A charge of approximately ${amount:.2f} "
            f"is predicted for {renewal_date}, "
            f"in {days} day(s). "
        )

    reasons = str(row["risk_reasons"])

    if "Historical duplicate charge detected" in reasons:
        explanation += (
            "A possible duplicate charge was detected "
            "in the historical transactions. "
        )

    if "Historical price increase detected" in reasons:
        explanation += (
            "A previous subscription price increase "
            "was detected. "
        )

    if "High expected charge amount" in reasons:
        explanation += (
            "The expected payment amount is relatively high. "
        )

    explanation += (
        "Review the subscription and confirm whether "
        "you still want to keep it."
    )

    return explanation


def generate_explanations():
    scores = pd.read_csv(RISK_PATH)

    scores["explanation"] = scores.apply(
        explain_subscription,
        axis=1
    )

    output = scores[
        [
            "merchant_name",
            "risk_score",
            "risk_level",
            "explanation"
        ]
    ].copy()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.to_csv(OUTPUT_PATH, index=False)

    print("\n========== SUBGUARD AI EXPLANATIONS ==========")

    for _, row in output.iterrows():
        print(f"\nMerchant: {row['merchant_name']}")
        print(f"Risk Score: {row['risk_score']}")
        print(f"Risk Level: {row['risk_level']}")
        print(f"Explanation: {row['explanation']}")

    print(f"\nSaved to: {OUTPUT_PATH}")
    print("========== EXPLANATIONS COMPLETE ==========")


if __name__ == "__main__":
    generate_explanations()

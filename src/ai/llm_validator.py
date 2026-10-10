
from pathlib import Path
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LLM_PATH = (
    PROJECT_ROOT
    / "data/processed/llm_subscription_explanations.csv"
)

RISK_PATH = (
    PROJECT_ROOT
    / "data/processed/renewal_risk_scores.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/validated_subscription_explanations.csv"
)


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text)).lower()


def validate_explanation(row):
    explanation = normalize_text(row["llm_explanation"])
    merchant = normalize_text(row["merchant_name"])

    expected_amount = float(row["predicted_next_amount"])
    expected_date = pd.to_datetime(
        row["predicted_next_charge_date"]
    )

    problems = []

    # 1. Validate merchant name.
    if merchant not in explanation:
        problems.append("missing_merchant")

    # 2. Validate expected charge amount.
    amount_pattern = (
        rf"\$\s*{re.escape(f'{expected_amount:.2f}')}\b"
    )

    if not re.search(amount_pattern, explanation):
        problems.append("missing_expected_amount")

    # 3. Validate expected renewal date.
    date_iso = expected_date.strftime("%Y-%m-%d").lower()
    date_long = expected_date.strftime("%B %d, %Y").lower()

    date_long_no_zero = (
        f"{expected_date.strftime('%B')} "
        f"{expected_date.day}, {expected_date.year}"
    ).lower()

    if not any(
        date_text in explanation
        for date_text in [
            date_iso,
            date_long,
            date_long_no_zero,
        ]
    ):
        problems.append("missing_expected_date")

    # 4. Validate historical duplicate-charge warning.
    reasons = str(row["risk_reasons"]).lower()

    if "historical duplicate charge detected" in reasons:
        if "duplicate" not in explanation:
            problems.append("missing_duplicate_warning")

    # 5. Validate historical price-increase warning.
    if "historical price increase detected" in reasons:
        if "price increase" not in explanation:
            problems.append("missing_price_increase_warning")

    # 6. Validate stale prediction warning.
    refresh_value = row["needs_prediction_refresh"]

    needs_refresh = (
        str(refresh_value).strip().lower()
        in {"true", "1", "yes"}
    )

    if needs_refresh:
        stale_warning_phrases = [
            "has passed",
            "past",
            "overdue",
            "refresh",
            "check for a recent payment",
        ]

        if not any(
            phrase in explanation
            for phrase in stale_warning_phrases
        ):
            problems.append("missing_stale_prediction_warning")

    # 7. Detect selected unsupported claims.
    prohibited_phrases = [
        "set to expire",
        "will definitely be charged",
        "has been cancelled",
        "subscription has expired",
    ]

    for phrase in prohibited_phrases:
        if phrase in explanation:
            problems.append(
                f"unsupported_claim:{phrase}"
            )

    # 8. Detect unsupported dollar amounts.
    amounts_found = re.findall(
        r"\$\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
        explanation,
    )

    for amount_text in amounts_found:
        amount_value = float(
            amount_text.replace(",", "")
        )

        if abs(amount_value - expected_amount) > 0.001:
            issue = (
                f"unsupported_amount:{amount_value:.2f}"
            )

            if issue not in problems:
                problems.append(issue)

    # 9. Detect unsupported explicit calendar dates.
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:january|february|march|april|may|june|"
        r"july|august|september|october|november|december)"
        r"\s+\d{1,2},?\s+\d{4}\b",
    ]

    for pattern in date_patterns:
        for date_text in re.findall(
            pattern,
            explanation,
        ):
            parsed_date = pd.to_datetime(
                date_text,
                errors="coerce",
            )

            if pd.isna(parsed_date):
                if "invalid_date" not in problems:
                    problems.append("invalid_date")
                continue

            if parsed_date.date() != expected_date.date():
                issue = (
                    f"unsupported_date:"
                    f"{parsed_date.strftime('%Y-%m-%d')}"
                )

                if issue not in problems:
                    problems.append(issue)

    return problems


def main():
    if not LLM_PATH.exists():
        raise FileNotFoundError(
            f"LLM explanations not found: {LLM_PATH}"
        )

    if not RISK_PATH.exists():
        raise FileNotFoundError(
            f"Risk scores not found: {RISK_PATH}"
        )

    llm_data = pd.read_csv(LLM_PATH)
    risk_data = pd.read_csv(RISK_PATH)

    merged = llm_data.merge(
        risk_data[
            [
                "merchant_name",
                "predicted_next_charge_date",
                "predicted_next_amount",
                "risk_reasons",
                "needs_prediction_refresh",
            ]
        ],
        on="merchant_name",
        how="left",
        validate="one_to_one",
    )

    if merged[
        [
            "predicted_next_charge_date",
            "predicted_next_amount",
        ]
    ].isna().any().any():
        raise ValueError(
            "Missing prediction data for one or more merchants."
        )

    results = []

    print(
        "\n========== SUBGUARD LLM VALIDATION =========="
    )

    for _, row in merged.iterrows():
        merchant = row["merchant_name"]

        problems = validate_explanation(row)

        if problems:
            final_explanation = row["original_explanation"]
            status = "FALLBACK"
        else:
            final_explanation = row["llm_explanation"]
            status = "PASSED"

        results.append({
            "merchant_name": merchant,
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
            "validation_status": status,
            "validation_issues": "; ".join(problems),
            "final_explanation": final_explanation,
        })

        print(f"\nMerchant: {merchant}")
        print(f"Status: {status}")
        print(
            f"Issues: {problems if problems else 'None'}"
        )

    output = pd.DataFrame(results)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nValidation summary:")
    print(
        output["validation_status"]
        .value_counts()
        .to_string()
    )

    print(f"\nSaved to: {OUTPUT_PATH}")

    print(
        "========== VALIDATION COMPLETE =========="
    )


if __name__ == "__main__":
    main()

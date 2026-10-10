
from pathlib import Path
import pandas as pd
from ollama import Client

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT / "data/processed/subscription_explanations.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data/processed/llm_subscription_explanations.csv"
)

MODEL_NAME = "llama3.2:3b"

client = Client(host="http://localhost:11434")


def generate_llm_explanation(merchant, original_explanation):
    system_prompt = """
You are SubGuard AI, a subscription management assistant.

Your task is to rewrite an existing subscription explanation
in clear, natural, user-friendly English.

Rules:
1. Use only facts in the supplied explanation.
2. Do not invent dates, prices, merchants, or transactions.
3. Do not claim a predicted charge has already happened.
4. Do not say that a subscription has been cancelled.
5. Do not claim that a payment will definitely occur.
6. Preserve uncertainty about predictions and anomalies.
7. Keep the explanation to 2-4 sentences.
8. Do not add unsupported cancellation links or advice.
9. Do not change the risk score or risk level.
"""

    user_prompt = f"""
Merchant: {merchant}

Verified explanation:
{original_explanation}

Rewrite this explanation for a subscription dashboard.
"""

    response = client.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        options={
            "temperature": 0.1,
        },
    )

    return response.message.content.strip()


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing input file: {INPUT_PATH}"
        )

    data = pd.read_csv(INPUT_PATH)

    results = []

    print("\n========== SUBGUARD LOCAL LLM EXPLANATIONS ==========")

    for _, row in data.iterrows():
        merchant = str(row["merchant_name"])
        original = str(row["explanation"])

        print(f"\nProcessing: {merchant}")

        try:
            llm_explanation = generate_llm_explanation(
                merchant,
                original,
            )

            if not llm_explanation:
                raise ValueError("LLM returned an empty response")

            source = "ollama"

        except Exception as error:
            print(f"LLM error: {error}")

            # Preserve the existing verified explanation.
            llm_explanation = original
            source = "rule_based_fallback"

        results.append({
            "merchant_name": merchant,
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
            "original_explanation": original,
            "llm_explanation": llm_explanation,
            "explanation_source": source,
        })

        print(f"Source: {source}")
        print(f"Explanation: {llm_explanation}")

    output = pd.DataFrame(results)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"\nExplanations generated: {len(output)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print(
        "\n========== LOCAL LLM EXPLANATIONS COMPLETE =========="
    )


if __name__ == "__main__":
    main()

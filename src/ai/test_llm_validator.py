
import unittest
import pandas as pd

from src.ai.llm_validator import validate_explanation


class TestLLMValidator(unittest.TestCase):

    def setUp(self):
        self.row = pd.Series({
            "merchant_name": "NETFLIX",
            "predicted_next_amount": 22.99,
            "predicted_next_charge_date": "2026-10-10",
            "risk_reasons": "Historical price increase detected",
            "needs_prediction_refresh": False,
            "llm_explanation": (
                "NETFLIX has a predicted charge of approximately "
                "$22.99 on October 10, 2026. "
                "A historical price increase was detected."
            ),
        })

    def test_valid_explanation(self):
        problems = validate_explanation(self.row)
        self.assertEqual(problems, [])

    def test_missing_amount(self):
        row = self.row.copy()
        row["llm_explanation"] = (
            "NETFLIX has a predicted charge on October 10, 2026. "
            "A historical price increase was detected."
        )

        problems = validate_explanation(row)
        self.assertIn("missing_expected_amount", problems)

    def test_unsupported_expiration(self):
        row = self.row.copy()
        row["llm_explanation"] += (
            " Your subscription is set to expire."
        )

        problems = validate_explanation(row)

        self.assertIn(
            "unsupported_claim:set to expire",
            problems,
        )

    def test_invented_amount(self):
        row = self.row.copy()
        row["llm_explanation"] += (
            " An additional charge of $49.99 is expected."
        )

        problems = validate_explanation(row)

        self.assertIn(
            "unsupported_amount:49.99",
            problems,
        )

    def test_invented_date(self):
        row = self.row.copy()
        row["llm_explanation"] += (
            " Another payment is scheduled for October 20, 2026."
        )

        problems = validate_explanation(row)

        self.assertIn(
            "unsupported_date:2026-10-20",
            problems,
        )



if __name__ == "__main__":
    unittest.main()

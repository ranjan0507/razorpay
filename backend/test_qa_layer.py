import sys
import os
import json

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.analytics import run_merchant_analytics
from app.ai import (
    generate_risk_explanation,
    answer_risk_question,
    RiskExplanationResponse,
    RiskQAResponse,
)


def run_qa_layer_verification():
    print("=" * 80)
    print("DISPUTEGUARD GEMINI MERCHANT Q&A LAYER VERIFICATION TEST (MERCHANT 2)")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Step 1: Verify Existing Analytics Functionality
        print("\n[1] Verifying Existing Analytics Functionality (run_merchant_analytics)...")
        analytics_result = run_merchant_analytics(db, merchant_id=2)
        assert analytics_result is not None, "FAILED: run_merchant_analytics(db, 2) returned None"
        print("  [PASS] Deterministic analytics executed successfully for Merchant 2.")

        # Step 2: Verify Existing Explanation Functionality
        print("\n[2] Verifying Existing Explanation Functionality (generate_risk_explanation)...")
        existing_explanation = generate_risk_explanation(analytics_result)
        assert isinstance(existing_explanation, RiskExplanationResponse), "FAILED: generate_risk_explanation returned invalid type"
        assert len(existing_explanation.summary) > 0, "FAILED: generate_risk_explanation summary is empty"
        print("  [PASS] Existing Gemini explanation layer executed successfully.")

        # Step 3: Run Q&A Verification Suite (5 Test Questions)
        print("\n[3] Running Merchant Q&A Verification Questions:")
        print("-" * 80)

        test_cases = [
            {
                "id": 1,
                "question": "Why is my risk increasing?",
                "expected_grounded": True,
                "verify_func": lambda ans: any(w in ans.lower() for w in ["upward", "increas", "trend", "driver", "electronics", "partner"]),
                "description": "Answer references upward trend and/or observed risk drivers."
            },
            {
                "id": 2,
                "question": "Which segment is driving the increase?",
                "expected_grounded": True,
                "verify_func": lambda ans: "electronics" in ans.lower() and ("partner_c" in ans.lower() or "partner c" in ans.lower()),
                "description": "Answer identifies Electronics + Partner_C as the strongest observed driver."
            },
            {
                "id": 3,
                "question": "When am I projected to cross the threshold?",
                "expected_grounded": True,
                "verify_func": lambda ans: any(w in ans.lower() for w in ["september 2026", "2026-09", "sept 2026"]),
                "description": "Answer identifies September 2026 / 2026-09."
            },
            {
                "id": 4,
                "question": "What is the weather today?",
                "expected_grounded": False,
                "verify_func": lambda ans: any(w in ans.lower() for w in ["not available", "supplied", "analytic", "cannot", "do not provide", "outside"]),
                "description": "Answer explains that weather is not available in the supplied analytics."
            },
            {
                "id": 5,
                "question": "What does Razorpay's chargeback policy say?",
                "expected_grounded": False,
                "verify_func": lambda ans: any(w in ans.lower() for w in ["policy", "external", "not available", "supplied", "analytic", "outside", "do not provide"]),
                "description": "Answer explains that external policy information is outside supplied analytics."
            }
        ]

        all_passed = True
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        for test in test_cases:
            q_id = test["id"]
            question = test["question"]
            expected_grounded = test["expected_grounded"]
            verify_func = test["verify_func"]

            print(f"\nTest {q_id}: \"{question}\"")

            qa_res: RiskQAResponse = answer_risk_question(analytics_result, question)

            print(f"  Grounded : {qa_res.grounded} (Expected: {expected_grounded})")
            print(f"  Answer   : {qa_res.answer}")

            # Grounded flag check
            grounded_ok = (qa_res.grounded == expected_grounded)
            # Content verification check
            content_ok = verify_func(qa_res.answer)

            if grounded_ok and content_ok:
                print(f"  Status   : [PASS] ({test['description']})")
            else:
                all_passed = False
                print(f"  Status   : [FAIL] (Grounded match: {grounded_ok}, Content check: {content_ok})")

            # API Key Exposure check
            if api_key and api_key in qa_res.answer:
                all_passed = False
                print(f"  [SECURITY FAIL] API key detected in output answer!")

        # Step 4: Security Verification (API key exposure scan across all outputs)
        print("\n[4] Verifying Security (API Key Non-Exposure)...")
        if api_key:
            assert api_key not in existing_explanation.model_dump_json(), "API key exposed in existing explanation!"
            print("  [PASS] API key is NOT exposed in any response objects.")
        else:
            print("  [INFO] GEMINI_API_KEY is not set in environment (fallback mode active).")

        print("\n" + "=" * 80)
        if all_passed:
            print("SUCCESS: ALL QA LAYER VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        else:
            print("FAILURE: ONE OR MORE QA LAYER VERIFICATION CHECKS FAILED.")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_qa_layer_verification()

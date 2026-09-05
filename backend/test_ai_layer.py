import sys
import os
import json
import re

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.analytics import run_merchant_analytics
from app.ai import generate_risk_explanation, RiskExplanationResponse

def extract_all_numbers(obj):
    """Recursively collect all numeric floats/ints from a nested dict/list structure."""
    nums = []
    if isinstance(obj, dict):
        for v in obj.values():
            nums.extend(extract_all_numbers(v))
    elif isinstance(obj, list):
        for item in obj:
            nums.extend(extract_all_numbers(item))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        nums.append(float(obj))
    return nums

def is_numerical_match(num_val: float, fact_nums: list) -> bool:
    """Checks if a numerical value from text corresponds to any known fact value or percentage representation."""
    for fact in fact_nums:
        if fact == 0:
            if abs(num_val) < 1e-5:
                return True
            continue
        # Direct absolute error check (< 0.001)
        if abs(num_val - fact) < 0.001:
            return True
        # Relative error check (< 1%)
        if abs(num_val - fact) / abs(fact) < 0.01:
            return True
        # Percentage conversion check (e.g. 0.01965 vs 1.965%)
        if abs(num_val / 100.0 - fact) < 0.001 or abs((num_val / 100.0 - fact) / fact) < 0.01:
            return True
        if abs(num_val * 100.0 - fact) < 0.001 or abs((num_val * 100.0 - fact) / fact) < 0.01:
            return True
    return False

def main():
    print("=" * 80)
    print("RISKWATCH GEMINI AI LAYER STRICT GROUNDING VERIFICATION TEST (MERCHANTS 2 & 4)")
    print("=" * 80)

    db = SessionLocal()
    try:
        # ----------------------------------------------------------------------
        # PART 1: MERCHANT 2 VERIFICATION (Escalating E-commerce)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("PART 1: MERCHANT 2 (Escalating E-commerce)")
        print("-" * 80)

        analytics_result_m2 = run_merchant_analytics(db, merchant_id=2)
        assert analytics_result_m2 is not None, "Failed to load Merchant 2 analytics"
        
        print("\n[1] Generating explanation for Merchant 2...")
        explanation_m2 = generate_risk_explanation(analytics_result_m2)
        exp_dict_m2 = explanation_m2.model_dump()

        print("\n[2] Generated Merchant 2 Structured Pydantic Explanation:")
        print("-" * 60)
        print(json.dumps(exp_dict_m2, indent=2))
        print("-" * 60)

        print(f"\n[3] Merchant 2 recommended_action Output:\n  \"{explanation_m2.recommended_action}\"")

        # Grounding & evidence checks for Merchant 2
        full_text_m2 = " ".join([
            explanation_m2.summary,
            explanation_m2.trend_explanation,
            explanation_m2.driver_explanation,
            explanation_m2.forecast_explanation,
            explanation_m2.focus_area,
            explanation_m2.recommended_action
        ])
        full_text_lower_m2 = full_text_m2.lower()
        rec_act_lower_m2 = explanation_m2.recommended_action.lower()

        grounding_rules_m2 = [
            (
                "Current Dispute Rate (~1.965% or 0.01965)",
                any(v in full_text_m2 for v in ["1.965", "1.97", "1.96%", "0.0196", "0.01965", "0.019647", "0.019648"])
            ),
            (
                "Risk Threshold (~2.000% or 0.02)",
                any(v in full_text_m2 for v in ["2.000", "2.0%", "2%", "0.02", "0.020"])
            ),
            (
                "Observed Lift (~6.76x)",
                any(v in full_text_m2 for v in ["6.76", "6.759", "6.8", "6.76x", "6.759337"])
            ),
            (
                "Projected Crossing Month (September 2026 / 2026-09)",
                any(v in full_text_lower_m2 for v in ["2026-09", "september 2026", "sept 2026"])
            ),
            (
                "Upward Trend Classification",
                any(v in full_text_lower_m2 for v in ["upward", "escalating", "increasing"])
            ),
            (
                "Categorical Segment: Electronics",
                "electronics" in full_text_lower_m2
            ),
            (
                "Categorical Segment: Delivery Partner C",
                ("partner_c" in full_text_lower_m2 or "partner c" in full_text_lower_m2)
            ),
            (
                "Recommended Action References Electronics",
                "electronics" in rec_act_lower_m2
            ),
            (
                "Recommended Action References Partner_C",
                ("partner_c" in rec_act_lower_m2 or "partner c" in rec_act_lower_m2)
            ),
            (
                "Recommended Action Has No Unsupported Causal Phrases",
                not any(w in rec_act_lower_m2 for w in ["caused by", "causing disputes", "root cause"])
            ),
            (
                "Recommended Action Has No Unsupported Operational Assumptions",
                not any(w in rec_act_lower_m2 for w in ["product quality", "fulfillment failure", "fulfillment process is failing", "customers are unhappy"])
            )
        ]

        strict_passed_m2 = True
        print("\n[4] Strict Evidence-Based Grounding Verification (Merchant 2):")
        for rule_name, passed in grounding_rules_m2:
            status = "PASS" if passed else "FAIL"
            if not passed:
                strict_passed_m2 = False
            print(f"  [{status}] {rule_name}")

        # Anti-Hallucination Claim Scan M2
        print("\n[5] Anti-Hallucination Claim Scan (Merchant 2):")
        valid_date_patterns = [
            "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09",
            "march 2026", "april 2026", "may 2026", "june 2026", "july 2026", "august 2026", "september 2026"
        ]

        dates_in_text = re.findall(r'\b20\d{2}-\d{2}\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d{2}\b', full_text_lower_m2)
        unsupported_dates = [d for d in dates_in_text if d not in valid_date_patterns]

        fact_numbers_m2 = extract_all_numbers(analytics_result_m2)
        extracted_num_strings_m2 = re.findall(r'\b\d+\.\d+%?\b|\b\d+%\b', full_text_m2)
        unsupported_numbers_m2 = []

        for num_str in extracted_num_strings_m2:
            clean_str = num_str.rstrip('%').rstrip('x')
            try:
                num_val = float(clean_str)
                if not is_numerical_match(num_val, fact_numbers_m2):
                    unsupported_numbers_m2.append(num_str)
            except ValueError:
                pass

        anti_hallucination_passed_m2 = (len(unsupported_dates) == 0 and len(unsupported_numbers_m2) == 0)
        print(f"  [{'PASS' if anti_hallucination_passed_m2 else 'FAIL'}] M2 dates and numbers match facts.")

        # ----------------------------------------------------------------------
        # PART 2: MERCHANT 4 VERIFICATION (Escalating Subscription)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("PART 2: MERCHANT 4 (Escalating Subscription)")
        print("-" * 80)

        analytics_result_m4 = run_merchant_analytics(db, merchant_id=4)
        assert analytics_result_m4 is not None, "Failed to load Merchant 4 analytics"

        print("\n[1] Generating explanation for Merchant 4...")
        explanation_m4 = generate_risk_explanation(analytics_result_m4)
        exp_dict_m4 = explanation_m4.model_dump()

        print("\n[2] Generated Merchant 4 Structured Pydantic Explanation:")
        print("-" * 60)
        print(json.dumps(exp_dict_m4, indent=2))
        print("-" * 60)

        print(f"\n[3] Merchant 4 recommended_action Output:\n  \"{explanation_m4.recommended_action}\"")

        rec_act_lower_m4 = explanation_m4.recommended_action.lower()

        grounding_rules_m4 = [
            (
                "Recommended Action References Annual Subscription",
                "annual" in rec_act_lower_m4
            ),
            (
                "Recommended Action References Renewal Transaction Type",
                ("renewal" in rec_act_lower_m4 or "renewals" in rec_act_lower_m4)
            ),
            (
                "Recommended Action References Observed Refund-Not-Processed Pattern",
                ("refund_not_processed" in rec_act_lower_m4 or "refund" in rec_act_lower_m4)
            ),
            (
                "Recommended Action Has No Unsupported Causal Phrases",
                not any(w in rec_act_lower_m4 for w in ["caused by", "causing disputes", "root cause"])
            )
        ]

        strict_passed_m4 = True
        print("\n[4] Strict Evidence-Based Grounding Verification (Merchant 4):")
        for rule_name, passed in grounding_rules_m4:
            status = "PASS" if passed else "FAIL"
            if not passed:
                strict_passed_m4 = False
            print(f"  [{status}] {rule_name}")

        # ----------------------------------------------------------------------
        # OVERALL VERIFICATION SUMMARY
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        all_ok = strict_passed_m2 and anti_hallucination_passed_m2 and strict_passed_m4
        if all_ok:
            print("SUCCESS: ALL GEMINI EXPLANATION GROUNDING & RECOMMENDATION TESTS PASSED!")
        else:
            print("FAILURE: ONE OR MORE GROUNDING CHECKS FAILED.")
        print("=" * 80 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()

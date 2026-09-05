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
    print("DISPUTEGUARD GEMINI AI LAYER STRICT GROUNDING VERIFICATION TEST (MERCHANT 2)")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Step 1: Run deterministic analytics for Merchant 2
        analytics_result = run_merchant_analytics(db, merchant_id=2)
        
        print("\n[1] Deterministic Facts Loaded from Backend Pipeline:")
        m = analytics_result["merchant"]
        o = analytics_result["overall_metrics"]
        t = analytics_result["trend"]
        d = analytics_result["segment_drivers"][0]
        f = analytics_result["forecast"]

        print(f"  Merchant Profile  : #{m['id']} - {m['name']} ({m['type']})")
        print(f"  Current Rate      : {o['current_dispute_rate']*100:.3f}% ({o['current_dispute_rate']})")
        print(f"  Risk Threshold    : {m['risk_threshold']*100:.3f}% ({m['risk_threshold']})")
        print(f"  Trend Direction   : {t.get('trend_direction', 'neutral')} (slope: {t.get('slope', 0):.6f})")
        print(f"  Top Driver        : {' + '.join([f'{k}={v}' for k, v in d['values'].items()])}")
        print(f"  Observed Lift     : {d['lift']:.2f}x ({d['lift']})")
        print(f"  Forecast Crossing : {f['estimated_crossing_month']} (status: {f['status']})")

        # Step 2: Generate explanation using Gemini API
        print("\n[2] Calling generate_risk_explanation(analytics_result)...")
        explanation = generate_risk_explanation(analytics_result)
        exp_dict = explanation.model_dump()

        print("\n[3] Generated Structured Pydantic Explanation:")
        print("-" * 60)
        print(json.dumps(exp_dict, indent=2))
        print("-" * 60)

        # Step 3: Strict Grounding Fact Verification
        print("\n[4] Strict Evidence-Based Grounding Verification:")
        
        full_text = " ".join([
            explanation.summary,
            explanation.trend_explanation,
            explanation.driver_explanation,
            explanation.forecast_explanation,
            explanation.focus_area
        ])
        full_text_lower = full_text.lower()

        # Define strict evidence rules
        grounding_rules = [
            (
                "Current Dispute Rate (~1.965% or 0.01965)",
                any(v in full_text for v in ["1.965", "1.97", "1.96%", "0.0196", "0.01965", "0.019647", "0.019648"])
            ),
            (
                "Risk Threshold (~2.000% or 0.02)",
                any(v in full_text for v in ["2.000", "2.0%", "2%", "0.02", "0.020"])
            ),
            (
                "Observed Lift (~6.76x)",
                any(v in full_text for v in ["6.76", "6.759", "6.8", "6.76x", "6.759337"])
            ),
            (
                "Projected Crossing Month (September 2026 / 2026-09)",
                any(v in full_text_lower for v in ["2026-09", "september 2026", "sept 2026"])
            ),
            (
                "Upward Trend Classification",
                any(v in full_text_lower for v in ["upward", "escalating", "increasing"])
            ),
            (
                "Categorical Segment: Electronics",
                "electronics" in full_text_lower
            ),
            (
                "Categorical Segment: Delivery Partner C",
                ("partner_c" in full_text_lower or "partner c" in full_text_lower)
            ),
        ]

        strict_passed = True
        for rule_name, passed in grounding_rules:
            status = "PASS" if passed else "FAIL"
            if not passed:
                strict_passed = False
            print(f"  [{status}] Grounded fact evidence verified: {rule_name}")

        # Step 4: Anti-Hallucination Claim Scan
        print("\n[5] Anti-Hallucination Claim Scan:")
        
        valid_date_patterns = [
            "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09",
            "march 2026", "april 2026", "may 2026", "june 2026", "july 2026", "august 2026", "september 2026"
        ]

        dates_in_text = re.findall(r'\b20\d{2}-\d{2}\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d{2}\b', full_text_lower)
        unsupported_dates = [d for d in dates_in_text if d not in valid_date_patterns]

        # Extract all numbers from M2 analytics facts
        fact_numbers = extract_all_numbers(analytics_result)

        # Find numbers in generated explanation
        extracted_num_strings = re.findall(r'\b\d+\.\d+%?\b|\b\d+%\b', full_text)
        unsupported_numbers = []

        for num_str in extracted_num_strings:
            clean_str = num_str.rstrip('%').rstrip('x')
            try:
                num_val = float(clean_str)
                if not is_numerical_match(num_val, fact_numbers):
                    unsupported_numbers.append(num_str)
            except ValueError:
                pass

        anti_hallucination_passed = (len(unsupported_dates) == 0 and len(unsupported_numbers) == 0)

        if len(unsupported_dates) > 0:
            print(f"  [FAIL] Unsupported date(s) detected: {unsupported_dates}")
        else:
            print("  [PASS] No unsupported dates detected in generated output.")

        if len(unsupported_numbers) > 0:
            print(f"  [FAIL] Unsupported number(s) detected: {unsupported_numbers}")
        else:
            print("  [PASS] All extracted numerical values match supplied analytics facts.")

        print("\n" + "=" * 80)
        if strict_passed and anti_hallucination_passed:
            print("SUCCESS: Gemini AI layer passed strict grounding & anti-hallucination verification!")
        else:
            print("FAILURE: Grounding or anti-hallucination verification checks failed.")
        print("=" * 80 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()

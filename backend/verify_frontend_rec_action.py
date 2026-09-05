import sys
import os
import json
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app


def verify_frontend_recommended_action():
    client = TestClient(app)

    print("=" * 80)
    print("DISPUTEGUARD FRONTEND RECOMMENDED ACTION INTEGRATION VERIFICATION")
    print("=" * 80)

    # 1. Merchant 2 Explanation & Recommended Action
    print("\n[Test 1] Merchant 2: GET /merchants/2/explanation")
    r2 = client.get("/merchants/2/explanation")
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}"
    d2 = r2.json()
    print(f"  HTTP Status        : {r2.status_code}")
    print(f"  Recommended Action : \"{d2.get('recommended_action')}\"")
    rec2_lower = d2.get("recommended_action", "").lower()
    assert len(rec2_lower) > 0, "Merchant 2 recommended_action is empty"
    assert "electronics" in rec2_lower, "Merchant 2 recommended_action missing 'electronics'"
    assert ("partner_c" in rec2_lower or "partner c" in rec2_lower), "Merchant 2 recommended_action missing 'Partner_C'"
    assert ("product_not_received" in rec2_lower or "product-not-received" in rec2_lower or "product" in rec2_lower), "Merchant 2 recommended_action missing 'product-not-received' pattern"
    print("  Status             : [PASS]")

    # 2. Merchant 4 Explanation & Recommended Action (Context Switching)
    print("\n[Test 2] Merchant 4: GET /merchants/4/explanation")
    r4 = client.get("/merchants/4/explanation")
    assert r4.status_code == 200, f"Expected 200, got {r4.status_code}"
    d4 = r4.json()
    print(f"  HTTP Status        : {r4.status_code}")
    print(f"  Recommended Action : \"{d4.get('recommended_action')}\"")
    rec4_lower = d4.get("recommended_action", "").lower()
    assert len(rec4_lower) > 0, "Merchant 4 recommended_action is empty"
    assert "annual" in rec4_lower, "Merchant 4 recommended_action missing 'annual'"
    assert ("renewal" in rec4_lower or "renewals" in rec4_lower), "Merchant 4 recommended_action missing 'renewal'"
    assert ("refund_not_processed" in rec4_lower or "refund" in rec4_lower), "Merchant 4 recommended_action missing 'refund-not-processed' pattern"
    assert rec4_lower != rec2_lower, "Merchant 4 recommendation must reflect Merchant 4 facts, not Merchant 2!"
    print("  Status             : [PASS]")

    # 3. Merchant 1 & Merchant 3 Render Checks
    print("\n[Test 3] Verifying Merchants 1 & 3 Explanations:")
    r1 = client.get("/merchants/1/explanation")
    assert r1.status_code == 200, "Merchant 1 explanation failed"
    print(f"  Merchant 1 Recommended Action: \"{r1.json().get('recommended_action')}\"")

    r3 = client.get("/merchants/3/explanation")
    assert r3.status_code == 200, "Merchant 3 explanation failed"
    print(f"  Merchant 3 Recommended Action: \"{r3.json().get('recommended_action')}\"")
    print("  Status                        : [PASS]")

    # 4. Q&A & Analytics Health Check
    print("\n[Test 4] Verifying Q&A & Analytics Endpoints:")
    qa_res = client.post("/merchants/2/ask", json={"question": "Why is my risk increasing?"})
    assert qa_res.status_code == 200, "Q&A endpoint failed"
    print(f"  Q&A endpoint status           : HTTP {qa_res.status_code}")

    an_res = client.get("/merchants/2/analytics")
    assert an_res.status_code == 200, "Analytics endpoint failed"
    print(f"  Analytics endpoint status     : HTTP {an_res.status_code}")
    print("  Status                        : [PASS]")

    # 5. Security Scan of Frontend Code
    print("\n[Security Scan] Scanning frontend source files for Gemini credentials/keys...")
    app_jsx_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "App.jsx")
    with open(app_jsx_path, "r", encoding="utf-8") as f:
        app_jsx_code = f.read()

    forbidden_terms = ["GEMINI_API_KEY", "AIzaSy", "genai", "GoogleGenerativeAI"]
    found_keys = [term for term in forbidden_terms if term in app_jsx_code]
    assert len(found_keys) == 0, f"SECURITY FAIL: Found forbidden credentials/symbols in frontend code: {found_keys}"
    print("  [PASS] Zero Gemini API keys or credentials present in frontend code.")

    print("\n" + "=" * 80)
    print("SUCCESS: ALL RECOMMENDED ACTION FRONTEND INTEGRATION TESTS PASSED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    verify_frontend_recommended_action()

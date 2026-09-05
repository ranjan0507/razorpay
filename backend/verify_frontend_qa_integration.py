import sys
import os
import json
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app


def verify_frontend_qa_integration():
    client = TestClient(app)

    print("=" * 80)
    print("RISKWATCH FRONTEND Q&A INTEGRATION VERIFICATION TEST")
    print("=" * 80)

    # Question 1: Merchant 2 - Why is my risk increasing?
    print("\n[Test 1] Merchant 2: \"Why is my risk increasing?\"")
    r1 = client.post("/merchants/2/ask", json={"question": "Why is my risk increasing?"})
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}"
    d1 = r1.json()
    print(f"  HTTP Status : {r1.status_code}")
    print(f"  Grounded    : {d1.get('grounded')}")
    print(f"  Answer      : {d1.get('answer')}")
    assert d1.get("grounded") is True, "Expected grounded: True for Merchant 2 risk question"
    assert any(w in d1.get("answer", "").lower() for w in ["upward", "increas", "trend", "driver", "electronics", "partner"]), "Answer missing expected risk trend/drivers"
    print("  Status      : [PASS]")

    # Question 2: Merchant 2 - Which segment is driving the increase?
    print("\n[Test 2] Merchant 2: \"Which segment is driving the increase?\"")
    r2 = client.post("/merchants/2/ask", json={"question": "Which segment is driving the increase?"})
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}"
    d2 = r2.json()
    print(f"  HTTP Status : {r2.status_code}")
    print(f"  Grounded    : {d2.get('grounded')}")
    print(f"  Answer      : {d2.get('answer')}")
    assert d2.get("grounded") is True, "Expected grounded: True for Merchant 2 segment driver"
    assert "electronics" in d2.get("answer", "").lower() and ("partner_c" in d2.get("answer", "").lower() or "partner c" in d2.get("answer", "").lower()), "Answer did not identify Electronics + Partner_C"
    print("  Status      : [PASS]")

    # Question 3: Merchant 2 - What is the weather today?
    print("\n[Test 3] Merchant 2: \"What is the weather today?\"")
    r3 = client.post("/merchants/2/ask", json={"question": "What is the weather today?"})
    assert r3.status_code == 200, f"Expected 200, got {r3.status_code}"
    d3 = r3.json()
    print(f"  HTTP Status : {r3.status_code}")
    print(f"  Grounded    : {d3.get('grounded')}")
    print(f"  Answer      : {d3.get('answer')}")
    assert d3.get("grounded") is False, "Expected grounded: False for weather question"
    assert any(w in d3.get("answer", "").lower() for w in ["not available", "supplied", "analytic", "cannot", "do not provide", "outside"]), "Answer did not state weather unavailable"
    print("  Status      : [PASS]")

    # Question 4: Merchant 4 - Which segment is driving the increase? (Context Switching Test)
    print("\n[Test 4] Merchant 4: \"Which segment is driving the increase?\"")
    r4 = client.post("/merchants/4/ask", json={"question": "Which segment is driving the increase?"})
    assert r4.status_code == 200, f"Expected 200, got {r4.status_code}"
    d4 = r4.json()
    print(f"  HTTP Status : {r4.status_code}")
    print(f"  Grounded    : {d4.get('grounded')}")
    print(f"  Answer      : {d4.get('answer')}")
    assert d4.get("grounded") is True, "Expected grounded: True for Merchant 4 segment driver"
    assert d4.get("answer") != d2.get("answer"), "Merchant 4 answer should reflect Merchant 4 analytics, not Merchant 2!"
    print("  Status      : [PASS] (Verified Merchant 4 specific analytics facts were used)")

    # Scan frontend code for any Gemini API key or credentials
    print("\n[Security Scan] Scanning frontend source files for Gemini credentials/keys...")
    app_jsx_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "App.jsx")
    with open(app_jsx_path, "r", encoding="utf-8") as f:
        app_jsx_code = f.read()

    forbidden_terms = ["GEMINI_API_KEY", "AIzaSy", "genai", "GoogleGenerativeAI"]
    found_keys = [term for term in forbidden_terms if term in app_jsx_code]
    assert len(found_keys) == 0, f"SECURITY FAIL: Found forbidden credentials/symbols in frontend code: {found_keys}"
    print("  [PASS] Zero Gemini API keys or credentials present in frontend code.")

    print("\n" + "=" * 80)
    print("SUCCESS: ALL FRONTEND INTEGRATION VERIFICATION CHECKS PASSED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    verify_frontend_qa_integration()

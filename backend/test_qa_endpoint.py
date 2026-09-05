import sys
import os
import json
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app


def test_qa_endpoint():
    client = TestClient(app)

    print("=" * 80)
    print("DISPUTEGUARD FASTAPI QA ENDPOINT VERIFICATION TEST")
    print("=" * 80)

    # 1. Verify Existing Endpoints
    print("\n[1] Verifying Existing Endpoints:")
    
    r_health = client.get("/health")
    print(f"  GET /health -> HTTP {r_health.status_code}: {r_health.json()}")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "ok"}

    r_analytics = client.get("/merchants/2/analytics")
    print(f"  GET /merchants/2/analytics -> HTTP {r_analytics.status_code}")
    assert r_analytics.status_code == 200
    assert "merchant" in r_analytics.json()

    r_explanation = client.get("/merchants/2/explanation")
    print(f"  GET /merchants/2/explanation -> HTTP {r_explanation.status_code}")
    assert r_explanation.status_code == 200
    assert "summary" in r_explanation.json()

    print("  [PASS] Existing endpoints (/health, /analytics, /explanation) operational.")

    # 2. Test POST /merchants/2/ask Test Cases
    print("\n[2] Testing POST /merchants/2/ask Test Cases:")
    print("-" * 80)

    qa_test_cases = [
        {
            "id": 1,
            "merchant_id": 2,
            "payload": {"question": "Why is my risk increasing?"},
            "expected_status": 200,
            "expected_grounded": True,
            "verify_func": lambda data: any(w in data["answer"].lower() for w in ["upward", "increas", "trend", "driver", "electronics", "partner"]),
            "desc": "References upward trend and/or risk drivers"
        },
        {
            "id": 2,
            "merchant_id": 2,
            "payload": {"question": "Which segment is driving the increase?"},
            "expected_status": 200,
            "expected_grounded": True,
            "verify_func": lambda data: "electronics" in data["answer"].lower() and ("partner_c" in data["answer"].lower() or "partner c" in data["answer"].lower()),
            "desc": "Identifies Electronics + Partner_C as strongest driver"
        },
        {
            "id": 3,
            "merchant_id": 2,
            "payload": {"question": "When am I projected to cross the threshold?"},
            "expected_status": 200,
            "expected_grounded": True,
            "verify_func": lambda data: any(w in data["answer"].lower() for w in ["september 2026", "2026-09", "sept 2026"]),
            "desc": "Identifies September 2026 / 2026-09"
        },
        {
            "id": 4,
            "merchant_id": 2,
            "payload": {"question": "What is the weather today?"},
            "expected_status": 200,
            "expected_grounded": False,
            "verify_func": lambda data: any(w in data["answer"].lower() for w in ["not available", "supplied", "analytic", "cannot", "do not provide", "outside"]),
            "desc": "Explains weather is not available"
        },
        {
            "id": 5,
            "merchant_id": 2,
            "payload": {"question": "What does Razorpay's chargeback policy say?"},
            "expected_status": 200,
            "expected_grounded": False,
            "verify_func": lambda data: any(w in data["answer"].lower() for w in ["policy", "external", "not available", "supplied", "analytic", "outside", "do not provide"]),
            "desc": "Explains external policy is outside analytics"
        },
    ]

    all_passed = True

    for test in qa_test_cases:
        m_id = test["merchant_id"]
        payload = test["payload"]
        exp_status = test["expected_status"]
        exp_grounded = test["expected_grounded"]
        verify_func = test["verify_func"]

        print(f"\nTest {test['id']}: POST /merchants/{m_id}/ask - \"{payload['question']}\"")
        res = client.post(f"/merchants/{m_id}/ask", json=payload)
        
        status_ok = (res.status_code == exp_status)
        print(f"  HTTP Status : {res.status_code} (Expected: {exp_status})")
        
        if status_ok and exp_status == 200:
            data = res.json()
            grounded = data.get("grounded")
            answer = data.get("answer", "")
            print(f"  Grounded    : {grounded} (Expected: {exp_grounded})")
            print(f"  Answer      : {answer}")

            grounded_ok = (grounded == exp_grounded)
            content_ok = verify_func(data)

            if grounded_ok and content_ok:
                print(f"  Status      : [PASS] ({test['desc']})")
            else:
                all_passed = False
                print(f"  Status      : [FAIL] (Grounded match: {grounded_ok}, Content check: {content_ok})")
        else:
            if not status_ok:
                all_passed = False
                print(f"  Status      : [FAIL] Expected HTTP {exp_status}, got {res.status_code}")

    # 3. Edge Case: Non-existent Merchant 999
    print("\n[3] Testing Non-existent Merchant: POST /merchants/999/ask")
    res_404 = client.post("/merchants/999/ask", json={"question": "Why is my risk increasing?"})
    print(f"  HTTP Status : {res_404.status_code} (Expected: 404)")
    print(f"  Response    : {res_404.json()}")
    assert res_404.status_code == 404, f"Expected HTTP 404, got {res_404.status_code}"
    print("  [PASS] Returned HTTP 404 for non-existent merchant.")

    # 4. Edge Case: Empty & Whitespace Questions
    print("\n[4] Testing Empty and Whitespace Question Validation:")

    res_empty = client.post("/merchants/2/ask", json={"question": ""})
    print(f"  Empty String ('')       -> HTTP {res_empty.status_code} (Expected: 422)")
    assert res_empty.status_code == 422, f"Expected HTTP 422, got {res_empty.status_code}"

    res_space = client.post("/merchants/2/ask", json={"question": "   \n\t   "})
    print(f"  Whitespace Only ('  ')  -> HTTP {res_space.status_code} (Expected: 422)")
    assert res_space.status_code == 422, f"Expected HTTP 422, got {res_space.status_code}"

    print("  [PASS] Returned HTTP 422 for invalid empty/whitespace questions.")

    print("\n" + "=" * 80)
    if all_passed:
        print("SUCCESS: ALL FASTAPI QA ENDPOINT VERIFICATION TESTS PASSED!")
    else:
        print("FAILURE: ONE OR MORE QA ENDPOINT CHECKS FAILED.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_qa_endpoint()

import sys
import os
import json
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app


def test_intervention_api():
    client = TestClient(app)

    print("=" * 80)
    print("DISPUTEGUARD INTERVENTION RECORDING & RETRIEVAL API VERIFICATION TEST")
    print("=" * 80)

    # 1. Test POST /merchants/2/interventions (Record Merchant 2 Intervention)
    print("\n[1] Testing POST /merchants/2/interventions:")
    post_payload = {
        "action_description": "Reviewed Partner_C delivery handling for electronics orders",
        "start_date": "2026-08-15T00:00:00",
        "target_segment": "Electronics + Partner_C",
        "status": "completed"
    }
    
    res_post = client.post("/merchants/2/interventions", json=post_payload)
    print(f"  HTTP Status Code : {res_post.status_code} (Expected: 201 or 200)")
    assert res_post.status_code in (200, 201), f"Expected 200/201, got {res_post.status_code}"
    
    created = res_post.json()
    print("  Returned Response:")
    print(json.dumps(created, indent=4))

    assert created.get("id") is not None and created["id"] > 0, "Missing or invalid intervention ID"
    assert created.get("merchant_id") == 2, f"Expected merchant_id=2, got {created.get('merchant_id')}"
    assert created.get("action_description") == post_payload["action_description"]
    assert created.get("target_segment") == post_payload["target_segment"]
    assert created.get("status") == post_payload["status"]
    assert "2026-08-15" in created.get("start_date", "")
    print("  [PASS] Successfully created intervention record for Merchant 2.")

    # 2. Test GET /merchants/2/interventions (Retrieve Merchant 2 Interventions)
    print("\n[2] Testing GET /merchants/2/interventions:")
    res_get_m2 = client.get("/merchants/2/interventions")
    print(f"  HTTP Status Code : {res_get_m2.status_code} (Expected: 200)")
    assert res_get_m2.status_code == 200, f"Expected 200, got {res_get_m2.status_code}"
    
    interventions_m2 = res_get_m2.json()
    print(f"  Retrieved {len(interventions_m2)} intervention(s):")
    print(json.dumps(interventions_m2, indent=4))

    assert isinstance(interventions_m2, list) and len(interventions_m2) > 0, "Expected non-empty interventions list for Merchant 2"
    matching = [i for i in interventions_m2 if i.get("id") == created["id"]]
    assert len(matching) == 1, "Created intervention not found in retrieved list"
    print("  [PASS] Successfully retrieved recorded intervention list for Merchant 2.")

    # 3. Test GET /merchants/1/interventions (Retrieve Merchant 1 Interventions)
    print("\n[3] Testing GET /merchants/1/interventions:")
    res_get_m1 = client.get("/merchants/1/interventions")
    print(f"  HTTP Status Code : {res_get_m1.status_code} (Expected: 200)")
    assert res_get_m1.status_code == 200, f"Expected 200, got {res_get_m1.status_code}"
    interventions_m1 = res_get_m1.json()
    assert isinstance(interventions_m1, list), "Expected list response for Merchant 1"
    print(f"  Merchant 1 returned valid list with {len(interventions_m1)} item(s).")
    print("  [PASS] Returned valid interventions list for Merchant 1.")

    # 4. Test POST /merchants/999/interventions (Non-existent Merchant)
    print("\n[4] Testing POST /merchants/999/interventions (Non-existent Merchant):")
    res_404_post = client.post("/merchants/999/interventions", json=post_payload)
    print(f"  HTTP Status Code : {res_404_post.status_code} (Expected: 404)")
    assert res_404_post.status_code == 404, f"Expected 404, got {res_404_post.status_code}"
    assert res_404_post.json().get("detail") == "Merchant not found"
    print("  [PASS] Returned HTTP 404 for non-existent merchant.")

    # 5. Test GET /merchants/999/interventions (Non-existent Merchant)
    print("\n[5] Testing GET /merchants/999/interventions (Non-existent Merchant):")
    res_404_get = client.get("/merchants/999/interventions")
    print(f"  HTTP Status Code : {res_404_get.status_code} (Expected: 404)")
    assert res_404_get.status_code == 404, f"Expected 404, got {res_404_get.status_code}"
    assert res_404_get.json().get("detail") == "Merchant not found"
    print("  [PASS] Returned HTTP 404 for non-existent merchant GET.")

    # 6. Test Validation: Empty Action Description
    print("\n[6] Testing Validation: Empty action_description:")
    bad_payload = {
        "action_description": "   ",
        "start_date": "2026-08-15T00:00:00",
        "target_segment": "Electronics + Partner_C",
        "status": "completed"
    }
    res_422 = client.post("/merchants/2/interventions", json=bad_payload)
    print(f"  HTTP Status Code : {res_422.status_code} (Expected: 422)")
    assert res_422.status_code == 422, f"Expected 422, got {res_422.status_code}"
    print("  [PASS] Returned HTTP 422 for empty/whitespace action_description.")

    # 7. Confirmation of Existing Endpoints
    print("\n[7] Verifying Existing Endpoints:")
    
    r_health = client.get("/health")
    assert r_health.status_code == 200, "Health check failed"
    print(f"  GET /health                   -> HTTP {r_health.status_code}")

    r_analytics = client.get("/merchants/2/analytics")
    assert r_analytics.status_code == 200, "Analytics endpoint failed"
    print(f"  GET /merchants/2/analytics    -> HTTP {r_analytics.status_code}")

    r_explanation = client.get("/merchants/2/explanation")
    assert r_explanation.status_code == 200, "Explanation endpoint failed"
    print(f"  GET /merchants/2/explanation  -> HTTP {r_explanation.status_code}")

    r_qa = client.post("/merchants/2/ask", json={"question": "Why is my risk increasing?"})
    assert r_qa.status_code == 200, "Q&A endpoint failed"
    print(f"  POST /merchants/2/ask         -> HTTP {r_qa.status_code}")

    print("  [PASS] All existing endpoints (/health, /analytics, /explanation, /ask) operational.")

    print("\n" + "=" * 80)
    print("SUCCESS: ALL INTERVENTION API VERIFICATION CHECKS PASSED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_intervention_api()

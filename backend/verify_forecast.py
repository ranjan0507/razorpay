import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 75)
print("THRESHOLD FORECAST VERIFICATION REPORT")
print("=" * 75)

expected_forecasts = {
    1: {
        "status": "projected_breach",
        "estimated_crossing_month": "2033-01",
        "is_highly_uncertain": True,
    },
    2: {
        "status": "projected_breach",
        "estimated_crossing_month": "2026-09",
        "is_highly_uncertain": False,
    },
    3: {
        "status": "no_breach_projected",
        "estimated_crossing_month": None,
        "is_highly_uncertain": False,
    },
    4: {
        "status": "already_breached",
        "estimated_crossing_month": "2026-08",
        "is_highly_uncertain": False,
    },
}

for mid in (1, 2, 3, 4):
    res = urllib.request.urlopen(f"{BASE_URL}/merchants/{mid}/analytics")
    data = json.loads(res.read().decode("utf-8"))
    
    fc = data["forecast"]
    exp = expected_forecasts[mid]
    
    print(f"\n--- Merchant {mid}: {data['merchant']['name']} ---")
    print(f"  Forecast Status       : {fc['status']}")
    print(f"  Crossing Month        : {fc['estimated_crossing_month']}")
    print(f"  Forecast Window       : {fc['forecast_start']} -> {fc['forecast_end']}")
    print(f"  High Uncertainty      : {fc['is_highly_uncertain']}")
    
    assert fc["status"] == exp["status"], f"Status mismatch M{mid}: got {fc['status']}, expected {exp['status']}"
    assert fc["estimated_crossing_month"] == exp["estimated_crossing_month"], f"Crossing month mismatch M{mid}"
    assert fc["is_highly_uncertain"] == exp["is_highly_uncertain"], f"Uncertainty mismatch M{mid}"

print("\n" + "=" * 75)
print("SUCCESS: All 4 merchants match expected threshold forecast states!")
print("=" * 75 + "\n")

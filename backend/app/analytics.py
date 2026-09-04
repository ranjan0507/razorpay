import itertools
import math
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Dispute, Merchant, Transaction


def detect_trend(monthly_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate deterministic trend metrics using ordinary least-squares linear regression

    and historical vs. recent cohort averages.
    """
    n = len(monthly_metrics)
    if n == 0:
        return {
            "slope": 0.0,
            "historical_average": 0.0,
            "recent_average": 0.0,
            "absolute_change": 0.0,
            "relative_change": 0.0,
            "recent_months_above_historical": 0,
            "recent_month_count": 0,
            "trend_persistence": 0.0,
            "trend_direction": "stable",
            "trend_strength": 0.0,
        }

    rates = [m["dispute_rate"] for m in monthly_metrics]

    if n == 1:
        avg = rates[0]
        return {
            "slope": 0.0,
            "historical_average": avg,
            "recent_average": avg,
            "absolute_change": 0.0,
            "relative_change": 0.0,
            "recent_months_above_historical": 0,
            "recent_month_count": 0,
            "trend_persistence": 0.0,
            "trend_direction": "stable",
            "trend_strength": 0.0,
        }

    # Ordinary Least-Squares (OLS) Linear Regression: r_t = a + b*t
    t_values = list(range(1, n + 1))
    sum_t = sum(t_values)
    sum_t2 = sum(t ** 2 for t in t_values)
    sum_r = sum(rates)
    sum_tr = sum(t * r for t, r in zip(t_values, rates))

    denom = (n * sum_t2) - (sum_t ** 2)
    slope = ((n * sum_tr) - (sum_t * sum_r)) / denom if denom != 0 else 0.0
    if abs(slope) < 1e-12:
        slope = 0.0

    # Historical vs. Recent split
    mid = n // 2
    historical_rates = rates[:mid]
    recent_rates = rates[mid:]

    historical_average = (sum(historical_rates) / len(historical_rates)) if historical_rates else 0.0
    recent_average = (sum(recent_rates) / len(recent_rates)) if recent_rates else 0.0

    absolute_change = recent_average - historical_average

    # Zero-baseline relative change logic
    if historical_average > 0:
        relative_change = absolute_change / historical_average
        trend_strength = abs(relative_change)
    elif recent_average == 0:
        relative_change = 0.0
        trend_strength = 0.0
    else:  # historical_average == 0 and recent_average > 0
        relative_change = None
        trend_strength = None

    recent_months_above_historical = sum(1 for r in recent_rates if r > historical_average)
    recent_month_count = len(recent_rates)
    trend_persistence = (recent_months_above_historical / recent_month_count) if recent_month_count > 0 else 0.0

    # Trend Direction Classification
    if slope > 0 and recent_average > historical_average:
        trend_direction = "upward"
    elif slope < 0 and recent_average < historical_average:
        trend_direction = "downward"
    else:
        trend_direction = "stable"

    return {
        "slope": slope,
        "historical_average": historical_average,
        "recent_average": recent_average,
        "absolute_change": absolute_change,
        "relative_change": relative_change,
        "recent_months_above_historical": recent_months_above_historical,
        "recent_month_count": recent_month_count,
        "trend_persistence": trend_persistence,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
    }


def analyze_segment_drivers(db: Session, merchant_id: int) -> Dict[str, Any]:
    """Analyze single-dimension and 2-way dimension combinations to identify

    the strongest observed drivers of a merchant's dispute volume.
    Strictly counts unique transactions and unique disputed transactions per segment.
    Filters out segments with non-positive excess disputes (excess_disputes <= 0).
    """
    # 1. Fetch all distinct transactions for merchant_id
    transactions = (
        db.query(
            Transaction.id,
            Transaction.payment_method,
            Transaction.product_category,
            Transaction.delivery_partner,
            Transaction.geography,
            Transaction.customer_segment,
            Transaction.subscription_type,
            Transaction.transaction_type,
        )
        .filter(Transaction.merchant_id == merchant_id)
        .all()
    )

    total_transactions = len(transactions)
    minimum_transactions = max(100, math.ceil(0.01 * total_transactions))

    if total_transactions == 0:
        return {
            "merchant_id": merchant_id,
            "baseline_rate": 0.0,
            "minimum_transactions": minimum_transactions,
            "drivers": [],
        }

    # 2. Fetch set of distinct disputed transaction IDs for this merchant
    disputed_tx_ids = (
        db.query(Dispute.transaction_id)
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .distinct()
        .all()
    )
    disputed_tx_set = {row[0] for row in disputed_tx_ids if row[0] is not None}

    # 3. Distinct dispute count and baseline rate
    total_disputes = sum(1 for tx in transactions if tx.id in disputed_tx_set)
    baseline_rate = (total_disputes / total_transactions) if total_transactions > 0 else 0.0

    candidate_fields = [
        "payment_method",
        "product_category",
        "delivery_partner",
        "geography",
        "customer_segment",
        "subscription_type",
        "transaction_type",
    ]

    # 4. Identify non-NULL candidate dimensions for this merchant
    valid_dimensions = []
    for idx, field_name in enumerate(candidate_fields, start=1):
        has_non_null = any(tx[idx] is not None for tx in transactions)
        if has_non_null:
            valid_dimensions.append((field_name, idx))

    # 5. Build 1-way and 2-way dimension combinations
    dimension_combinations = []
    for dim_name, idx in valid_dimensions:
        dimension_combinations.append([(dim_name, idx)])
    for (dim1_name, idx1), (dim2_name, idx2) in itertools.combinations(valid_dimensions, 2):
        dimension_combinations.append([(dim1_name, idx1), (dim2_name, idx2)])

    drivers = []

    # 6. Aggregate unique counts across candidate segments
    for dim_set in dimension_combinations:
        dim_names = [d[0] for d in dim_set]
        dim_indices = [d[1] for d in dim_set]

        segment_counts: Dict[tuple, list] = {}  # val_tuple -> [tx_count, disp_count]

        for tx in transactions:
            vals = tuple(tx[idx] for idx in dim_indices)
            if any(v is None for v in vals):
                continue

            if vals not in segment_counts:
                segment_counts[vals] = [0, 0]

            segment_counts[vals][0] += 1
            if tx.id in disputed_tx_set:
                segment_counts[vals][1] += 1

        for val_tuple, (tx_count, disp_count) in segment_counts.items():
            if tx_count < minimum_transactions:
                continue

            segment_dispute_rate = disp_count / tx_count
            excess_disputes = tx_count * (segment_dispute_rate - baseline_rate)

            # Filter out non-positive drivers (excess_disputes <= 0)
            if excess_disputes <= 0:
                continue

            lift = (segment_dispute_rate / baseline_rate) if baseline_rate > 0 else 0.0
            values_dict = {dim_names[i]: val_tuple[i] for i in range(len(dim_names))}

            drivers.append({
                "dimensions": dim_names,
                "values": values_dict,
                "transaction_count": tx_count,
                "dispute_count": disp_count,
                "dispute_rate": segment_dispute_rate,
                "baseline_rate": baseline_rate,
                "lift": lift,
                "excess_disputes": excess_disputes,
            })

    # 7. Rank drivers primarily by descending excess_disputes, secondarily by lift
    drivers.sort(key=lambda d: (d["excess_disputes"], d["lift"]), reverse=True)

    return {
        "merchant_id": merchant_id,
        "baseline_rate": baseline_rate,
        "minimum_transactions": minimum_transactions,
        "drivers": drivers,
    }


def calculate_risk_score(
    risk_threshold: float,
    monthly_metrics: List[Dict[str, Any]],
    trend: Dict[str, Any],
    drivers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate deterministic 0-100 risk score based on 4 components:

    - Threshold proximity: 30 points
    - Trend: 30 points
    - Persistence: 20 points
    - Segment anomaly: 20 points
    """
    # 1. Threshold Proximity (30 points)
    current_rate = monthly_metrics[-1]["dispute_rate"] if monthly_metrics else 0.0
    if risk_threshold <= 0:
        threshold_score = 0.0
    else:
        threshold_score = min(30.0, max(0.0, 30.0 * (current_rate / risk_threshold)))

    # 2. Trend (30 points)
    trend_direction = trend.get("trend_direction", "stable")
    trend_strength = trend.get("trend_strength")
    if trend_direction == "upward" and trend_strength is not None:
        trend_score = min(30.0, max(0.0, 30.0 * (trend_strength / (1.0 + trend_strength))))
    else:
        trend_score = 0.0

    # 3. Persistence (20 points)
    trend_persistence = trend.get("trend_persistence", 0.0)
    persistence_score = min(20.0, max(0.0, 20.0 * trend_persistence))

    # 4. Segment Anomaly (20 points)
    strongest_driver = drivers[0] if drivers else None
    if strongest_driver is None:
        lift = 0.0
        segment_score = 0.0
    else:
        lift = strongest_driver.get("lift", 0.0)
        if lift <= 1.0:
            segment_score = 0.0
        else:
            segment_score = min(20.0, max(0.0, 20.0 * ((lift - 1.0) / lift)))

    # 5. Final Aggregated Score
    raw_score = threshold_score + trend_score + persistence_score + segment_score
    risk_score = min(100.0, max(0.0, raw_score))

    return {
        "risk_score": risk_score,
        "breakdown": {
            "threshold_proximity": threshold_score,
            "trend": trend_score,
            "persistence": persistence_score,
            "segment_anomaly": segment_score,
        },
        "facts": {
            "current_rate": current_rate,
            "risk_threshold": risk_threshold,
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "trend_persistence": trend_persistence,
            "strongest_driver_lift": lift,
            "strongest_driver_dimensions": strongest_driver.get("dimensions", []) if strongest_driver else [],
            "strongest_driver_values": strongest_driver.get("values", {}) if strongest_driver else {},
        },
    }


def get_merchant_dispute_metrics(db: Session, merchant_id: int) -> Dict[str, Any]:
    """Calculate deterministic cohort-based dispute metrics for a merchant,

    including trend detection, segment driver analysis, and 0-100 risk scoring.
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    risk_threshold = merchant.risk_threshold if merchant else 0.02

    # 1. Total transaction count
    total_transactions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.merchant_id == merchant_id)
        .scalar()
        or 0
    )

    # 2. Total dispute count
    total_disputes = (
        db.query(func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .scalar()
        or 0
    )

    # 3. Overall dispute rate
    overall_dispute_rate = (
        (total_disputes / total_transactions) if total_transactions > 0 else 0.0
    )

    # 4. Monthly transaction counts (grouped by Transaction timestamp month)
    tx_by_month_raw = (
        db.query(
            func.strftime("%Y-%m", Transaction.timestamp).label("month"),
            func.count(Transaction.id).label("tx_count"),
        )
        .filter(Transaction.merchant_id == merchant_id)
        .group_by("month")
        .all()
    )
    monthly_tx_map = {m: count for m, count in tx_by_month_raw if m}

    # 5. Monthly dispute counts (grouped by Transaction timestamp month cohort)
    disp_by_tx_month_raw = (
        db.query(
            func.strftime("%Y-%m", Transaction.timestamp).label("month"),
            func.count(Dispute.id).label("disp_count"),
        )
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .group_by("month")
        .all()
    )
    monthly_disp_map = {m: count for m, count in disp_by_tx_month_raw if m}

    # 6. All transaction months in chronological order
    all_months = sorted(list(monthly_tx_map.keys()))

    monthly_metrics: List[Dict[str, Any]] = []
    for month in all_months:
        tx_count = monthly_tx_map.get(month, 0)
        disp_count = monthly_disp_map.get(month, 0)
        disp_rate = (disp_count / tx_count) if tx_count > 0 else 0.0

        monthly_metrics.append({
            "month": month,
            "transaction_count": tx_count,
            "dispute_count": disp_count,
            "dispute_rate": disp_rate,
        })

    # 7. Trend Detection
    trend_facts = detect_trend(monthly_metrics)

    # 8. Segment Driver Analysis
    driver_facts = analyze_segment_drivers(db, merchant_id)

    # 9. 0-100 Risk Score Calculation
    risk_info = calculate_risk_score(
        risk_threshold=risk_threshold,
        monthly_metrics=monthly_metrics,
        trend=trend_facts,
        drivers=driver_facts["drivers"],
    )

    return {
        "merchant_id": merchant_id,
        "total_transactions": total_transactions,
        "total_disputes": total_disputes,
        "overall_dispute_rate": overall_dispute_rate,
        "monthly_metrics": monthly_metrics,
        "trend": trend_facts,
        "drivers": driver_facts["drivers"],
        "risk_assessment": risk_info,
    }


def verify_risk_score_edge_cases():
    """Verify edge cases for calculate_risk_score function."""
    print("\n" + "=" * 70)
    print("VERIFYING RISK SCORE EDGE CASES")
    print("=" * 70)

    # Edge Case 1: No transactions / no monthly metrics
    r1 = calculate_risk_score(0.02, [], {"trend_direction": "stable", "trend_strength": 0.0, "trend_persistence": 0.0}, [])
    print(f"1. No transactions           -> Score: {r1['risk_score']:.1f} (Expected: 0.0)")
    assert r1["risk_score"] == 0.0

    # Edge Case 2: Risk threshold = 0
    r2 = calculate_risk_score(0.0, [{"dispute_rate": 0.01}], {"trend_direction": "stable", "trend_strength": 0.0, "trend_persistence": 0.0}, [])
    print(f"2. Risk threshold = 0        -> Score: {r2['risk_score']:.1f} (Expected: 0.0)")
    assert r2["breakdown"]["threshold_proximity"] == 0.0

    # Edge Case 3 & 4: Stable / Downward trend
    r3 = calculate_risk_score(0.02, [{"dispute_rate": 0.007}], {"trend_direction": "stable", "trend_strength": 0.2, "trend_persistence": 0.5}, [])
    r4 = calculate_risk_score(0.02, [{"dispute_rate": 0.007}], {"trend_direction": "downward", "trend_strength": 0.3, "trend_persistence": 0.0}, [])
    print(f"3. Stable trend              -> Trend Score: {r3['breakdown']['trend']:.1f} (Expected: 0.0)")
    print(f"4. Downward trend            -> Trend Score: {r4['breakdown']['trend']:.1f} (Expected: 0.0)")
    assert r3["breakdown"]["trend"] == 0.0
    assert r4["breakdown"]["trend"] == 0.0

    # Edge Case 5: trend_strength = None
    r5 = calculate_risk_score(0.02, [{"dispute_rate": 0.01}], {"trend_direction": "upward", "trend_strength": None, "trend_persistence": 0.5}, [])
    print(f"5. trend_strength = None     -> Trend Score: {r5['breakdown']['trend']:.1f} (Expected: 0.0)")
    assert r5["breakdown"]["trend"] == 0.0

    # Edge Case 6 & 7: No drivers / Lift <= 1
    r6 = calculate_risk_score(0.02, [{"dispute_rate": 0.01}], {"trend_direction": "stable", "trend_strength": 0.0, "trend_persistence": 0.0}, [])
    r7 = calculate_risk_score(0.02, [{"dispute_rate": 0.01}], {"trend_direction": "stable", "trend_strength": 0.0, "trend_persistence": 0.0}, [{"lift": 0.95}])
    print(f"6. No drivers                -> Segment Score: {r6['breakdown']['segment_anomaly']:.1f} (Expected: 0.0)")
    print(f"7. Lift <= 1 (0.95)          -> Segment Score: {r7['breakdown']['segment_anomaly']:.1f} (Expected: 0.0)")
    assert r6["breakdown"]["segment_anomaly"] == 0.0
    assert r7["breakdown"]["segment_anomaly"] == 0.0

    # Edge Case 8: Moderate high inputs (trend_strength=5.0, lift=10.0) -> Expected: 93.0
    r8 = calculate_risk_score(0.02, [{"dispute_rate": 0.05}], {"trend_direction": "upward", "trend_strength": 5.0, "trend_persistence": 1.0}, [{"lift": 10.0}])
    print(f"8. High inputs (strength 5, lift 10) -> Score: {r8['risk_score']:.1f} (Expected: 93.0)")
    assert math.isclose(r8["risk_score"], 93.0, abs_tol=1e-1)

    # Edge Case 9: Maximum 100/100 score test (extreme high inputs)
    r9 = calculate_risk_score(0.02, [{"dispute_rate": 0.05}], {"trend_direction": "upward", "trend_strength": 1e9, "trend_persistence": 1.0}, [{"lift": 1e9}])
    print(f"9. Extreme max inputs (strength 1e9, lift 1e9) -> Score: {r9['risk_score']:.1f} (Expected: 100.0)")
    assert math.isclose(r9["risk_score"], 100.0, abs_tol=1e-3)
    assert r9["breakdown"]["threshold_proximity"] == 30.0
    assert math.isclose(r9["breakdown"]["trend"], 30.0, abs_tol=1e-5)
    assert r9["breakdown"]["persistence"] == 20.0
    assert math.isclose(r9["breakdown"]["segment_anomaly"], 20.0, abs_tol=1e-5)

    print("=" * 70 + "\n")


def run_analytics_verification():
    """Callable verification runner computing metrics, trends, segment drivers, and risk scores."""
    db = SessionLocal()
    try:
        merchants = db.query(Merchant).order_by(Merchant.id).all()
        if not merchants:
            print("No merchants found in database.")
            return

        print("\n" + "=" * 70)
        print("DETERMINISTIC 0-100 RISK SCORING VERIFICATION REPORT (STEP 4D)")
        print("=" * 70)

        for merchant in merchants:
            metrics = get_merchant_dispute_metrics(db, merchant.id)
            ra = metrics["risk_assessment"]
            bd = ra["breakdown"]
            facts = ra["facts"]

            driver_str = (
                f"[{' + '.join(facts['strongest_driver_dimensions'])}] -> "
                f"({', '.join(f'{k}={v}' for k, v in facts['strongest_driver_values'].items())})"
                if facts['strongest_driver_dimensions']
                else "None"
            )

            trend_str_val = f"{facts['trend_strength']:.3f}" if facts['trend_strength'] is not None else "None"

            print(f"\nMerchant ID {merchant.id}: {merchant.name} ({merchant.merchant_type})")
            print("-" * 65)
            print(f"  Current dispute rate      : {facts['current_rate'] * 100:.3f}%")
            print(f"  Risk threshold            : {facts['risk_threshold'] * 100:.3f}%")
            print(f"  Threshold proximity score  : {bd['threshold_proximity']:.2f} / 30.0")
            print(f"  Trend direction           : {facts['trend_direction'].upper()}")
            print(f"  Trend strength            : {trend_str_val}")
            print(f"  Trend score               : {bd['trend']:.2f} / 30.0")
            print(f"  Trend persistence         : {facts['trend_persistence']:.3f}")
            print(f"  Persistence score         : {bd['persistence']:.2f} / 20.0")
            print(f"  Strongest driver          : {driver_str}")
            print(f"  Strongest driver lift     : {facts['strongest_driver_lift']:.2f}x")
            print(f"  Segment anomaly score     : {bd['segment_anomaly']:.2f} / 20.0")
            print("-" * 65)
            print(f"  FINAL RISK SCORE          : {ra['risk_score']:.2f} / 100.0")

        verify_risk_score_edge_cases()
    finally:
        db.close()


if __name__ == "__main__":
    run_analytics_verification()

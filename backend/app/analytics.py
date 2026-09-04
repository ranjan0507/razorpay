import itertools
import math
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Dispute, Merchant, Transaction


def convert_index_to_month_str(start_month_str: str, t: float) -> str:
    """Convert continuous time index t (where t=0 is start_month_str) to 'YYYY-MM'.

    Convention: Integer t=k corresponds to observation month k. A fractional index
    t > k indicates crossing occurs after month k, so math.ceil(t) is used for the
    month offset from the start month.
    """
    year, month = map(int, start_month_str.split("-"))
    month_offset = math.ceil(t) if t > 0 else math.floor(t)
    total_months = (month - 1) + month_offset
    new_year = year + (total_months // 12)
    new_month = (total_months % 12) + 1
    return f"{new_year:04d}-{new_month:02d}"


def get_merchant_dispute_metrics(db: Session, merchant_id: int) -> Dict[str, Any]:
    """Calculate basic cohort dispute metrics for a merchant (Step 4A).

    Derives metrics strictly from Transaction and Dispute records using the transaction
    month as the cohort.
    """
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

    return {
        "merchant_id": merchant_id,
        "total_transactions": total_transactions,
        "total_disputes": total_disputes,
        "overall_dispute_rate": overall_dispute_rate,
        "monthly_metrics": monthly_metrics,
    }


def detect_trend(monthly_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate deterministic trend metrics using ordinary least-squares linear regression

    and historical vs. recent cohort averages (Step 4B).
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

    the strongest observed drivers of a merchant's dispute volume (Step 4C).
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
    """Calculate deterministic 0-100 risk score based on 4 components (Step 4D):

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


def forecast_threshold_crossing(
    risk_threshold: float,
    monthly_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Forecast when a merchant's monthly dispute rate will cross their risk threshold

    using an OLS linear trend and residual standard deviation window (Step 4E).
    Time index convention: t = 0, 1, 2, ..., n-1
    Model: rate(t) = a + b * t
    """
    n = len(monthly_metrics)

    # 1. Invalid threshold
    if risk_threshold <= 0:
        return {
            "status": "invalid_threshold",
            "current_rate": monthly_metrics[-1]["dispute_rate"] if monthly_metrics else 0.0,
            "risk_threshold": risk_threshold,
            "slope": 0.0,
            "intercept": 0.0,
            "residual_std": 0.0,
            "estimated_crossing_index": None,
            "estimated_crossing_month": None,
            "forecast_start": None,
            "forecast_end": None,
            "number_of_observations": n,
            "is_highly_uncertain": False,
            "reason": "Risk threshold must be greater than zero",
        }

    # 2. No monthly observations
    if n == 0:
        return {
            "status": "insufficient_data",
            "current_rate": 0.0,
            "risk_threshold": risk_threshold,
            "slope": 0.0,
            "intercept": 0.0,
            "residual_std": 0.0,
            "estimated_crossing_index": None,
            "estimated_crossing_month": None,
            "forecast_start": None,
            "forecast_end": None,
            "number_of_observations": 0,
            "is_highly_uncertain": False,
            "reason": "No monthly observations available",
        }

    current_rate = monthly_metrics[-1]["dispute_rate"]

    # 3. Fewer than 3 observations
    if n < 3:
        return {
            "status": "insufficient_data",
            "current_rate": current_rate,
            "risk_threshold": risk_threshold,
            "slope": 0.0,
            "intercept": 0.0,
            "residual_std": 0.0,
            "estimated_crossing_index": None,
            "estimated_crossing_month": None,
            "forecast_start": None,
            "forecast_end": None,
            "number_of_observations": n,
            "is_highly_uncertain": False,
            "reason": "Fewer than 3 monthly observations available for residual estimation",
        }

    # Fit OLS linear trend: rate(t) = a + b * t for t = 0, 1, ..., n-1
    rates = [m["dispute_rate"] for m in monthly_metrics]
    t_values = list(range(n))

    sum_t = sum(t_values)
    sum_t2 = sum(t ** 2 for t in t_values)
    sum_r = sum(rates)
    sum_tr = sum(t * r for t, r in zip(t_values, rates))

    denom = (n * sum_t2) - (sum_t ** 2)
    b = ((n * sum_tr) - (sum_t * sum_r)) / denom if denom != 0 else 0.0
    if abs(b) < 1e-12:
        b = 0.0

    a = (sum_r - b * sum_t) / n

    # Residuals & Residual standard deviation: sqrt(sum(residual_i^2) / (n - 2))
    residuals = [r - (a + b * t) for t, r in zip(t_values, rates)]
    residual_variance = sum(res ** 2 for res in residuals) / (n - 2)
    residual_std = math.sqrt(residual_variance)

    # 4. Check if already breached (Preserve OLS trend facts)
    if current_rate >= risk_threshold:
        return {
            "status": "already_breached",
            "current_rate": current_rate,
            "risk_threshold": risk_threshold,
            "slope": b,
            "intercept": a,
            "residual_std": residual_std,
            "estimated_crossing_index": None,
            "estimated_crossing_month": monthly_metrics[-1]["month"],
            "forecast_start": None,
            "forecast_end": None,
            "number_of_observations": n,
            "is_highly_uncertain": False,
            "reason": "Current monthly dispute rate is already at or above risk threshold",
        }

    # 5. Non-positive slope
    if b <= 0:
        return {
            "status": "no_breach_projected",
            "current_rate": current_rate,
            "risk_threshold": risk_threshold,
            "slope": b,
            "intercept": a,
            "residual_std": residual_std,
            "estimated_crossing_index": None,
            "estimated_crossing_month": None,
            "forecast_start": None,
            "forecast_end": None,
            "number_of_observations": n,
            "is_highly_uncertain": False,
            "reason": "Dispute rate trend is non-positive; no threshold breach projected",
        }

    # 6. Projected breach logic
    t_cross = (risk_threshold - a) / b
    delta_t = residual_std / b if b > 0 else 0.0

    t_early = t_cross - delta_t
    t_late = t_cross + delta_t

    # Constrain window to be future-oriented (not earlier than month after latest observed, t = n)
    t_next_month = float(n)
    t_early_future = max(t_next_month, t_early)
    t_late_future = max(t_early_future, t_late)

    start_month_str = monthly_metrics[0]["month"]
    crossing_month_str = convert_index_to_month_str(start_month_str, t_cross)
    forecast_start_str = convert_index_to_month_str(start_month_str, t_early_future)
    forecast_end_str = convert_index_to_month_str(start_month_str, t_late_future)

    # Indicate high uncertainty if crossing point is far in the future (> 24 months beyond latest observation)
    is_highly_uncertain = (t_cross - (n - 1)) > 24.0

    return {
        "status": "projected_breach",
        "current_rate": current_rate,
        "risk_threshold": risk_threshold,
        "slope": b,
        "intercept": a,
        "residual_std": residual_std,
        "estimated_crossing_index": t_cross,
        "estimated_crossing_month": crossing_month_str,
        "forecast_start": forecast_start_str,
        "forecast_end": forecast_end_str,
        "number_of_observations": n,
        "is_highly_uncertain": is_highly_uncertain,
    }


def run_merchant_analytics(db: Session, merchant_id: int) -> Optional[Dict[str, Any]]:
    """Single orchestration function for the deterministic analytics pipeline.

    Executes in order:
    1. Loads merchant record and threshold context.
    2. Calculates monthly cohort dispute metrics (Step 4A).
    3. Detects trend trajectory (Step 4B).
    4. Analyzes segment drivers (Step 4C).
    5. Calculates 0-100 risk score and breakdown (Step 4D).
    6. Forecasts threshold crossing (Step 4E).

    Returns structured analytics result, or None if merchant_id is not found.
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if merchant is None:
        return None

    # Step 4A: Basic Cohort Metrics
    basic_metrics = get_merchant_dispute_metrics(db, merchant_id)
    monthly_metrics = basic_metrics.get("monthly_metrics", [])

    # Step 4B: Trend Detection
    trend_facts = detect_trend(monthly_metrics)

    # Step 4C: Segment Driver Analysis
    driver_facts = analyze_segment_drivers(db, merchant_id)
    drivers = driver_facts.get("drivers", [])

    # Step 4D: 0-100 Risk Score Calculation
    risk_info = calculate_risk_score(
        risk_threshold=merchant.risk_threshold,
        monthly_metrics=monthly_metrics,
        trend=trend_facts,
        drivers=drivers,
    )

    # Step 4E: Threshold Crossing Forecast
    forecast_info = forecast_threshold_crossing(
        risk_threshold=merchant.risk_threshold,
        monthly_metrics=monthly_metrics,
    )

    current_dispute_rate = (
        monthly_metrics[-1]["dispute_rate"] if monthly_metrics else 0.0
    )

    return {
        "merchant": {
            "id": merchant.id,
            "name": merchant.name,
            "type": merchant.merchant_type,
            "risk_threshold": merchant.risk_threshold,
            "alert_threshold": merchant.alert_threshold,
            "historical_baseline": merchant.historical_baseline,
        },
        "overall_metrics": {
            "total_transactions": basic_metrics["total_transactions"],
            "total_disputes": basic_metrics["total_disputes"],
            "overall_dispute_rate": basic_metrics["overall_dispute_rate"],
            "current_dispute_rate": current_dispute_rate,
        },
        "monthly_metrics": monthly_metrics,
        "trend": trend_facts,
        "segment_drivers": drivers,
        "risk_assessment": risk_info,
        "forecast": forecast_info,
    }


def run_analytics_verification():
    """Callable verification runner running run_merchant_analytics() for M1–M4 and edge cases."""
    db = SessionLocal()
    try:
        print("\n" + "=" * 75)
        print("DETERMINISTIC ANALYTICS PIPELINE ORCHESTRATION REPORT")
        print("=" * 75)

        for merchant_id in (1, 2, 3, 4):
            res = run_merchant_analytics(db, merchant_id)
            assert res is not None, f"Merchant {merchant_id} returned None"

            m = res["merchant"]
            om = res["overall_metrics"]
            tr = res["trend"]
            drivers = res["segment_drivers"]
            ra = res["risk_assessment"]
            fc = res["forecast"]

            top_driver_str = "None"
            if drivers:
                d = drivers[0]
                dims = " + ".join(d["dimensions"])
                vals = ", ".join(f"{k}={v}" for k, v in d["values"].items())
                top_driver_str = f"[{dims}] -> ({vals}) (lift: {d['lift']:.2f}x)"

            crossing_info = "N/A"
            if fc["status"] == "projected_breach":
                crossing_info = f"{fc['estimated_crossing_month']} (Window: {fc['forecast_start']} to {fc['forecast_end']})"
                if fc.get("is_highly_uncertain"):
                    crossing_info += " [Highly Uncertain]"
            elif fc["status"] == "already_breached":
                crossing_info = f"Already Breached ({fc['estimated_crossing_month']})"

            print(f"\nMerchant ID {m['id']}: {m['name']} ({m['type']})")
            print("-" * 70)
            print(f"  Risk Threshold            : {m['risk_threshold'] * 100:.3f}%")
            print(f"  Current Dispute Rate      : {om['current_dispute_rate'] * 100:.3f}%")
            print(f"  Trend Direction           : {tr['trend_direction'].upper()}")
            print(f"  Monthly OLS Slope (b)     : {tr['slope'] * 100:.4f}% / month")
            print(f"  Top Segment Driver        : {top_driver_str}")
            print(f"  Final Risk Score (0-100)  : {ra['risk_score']:.2f} / 100.0")
            print(f"  Forecast Status           : {fc['status'].upper()}")
            print(f"  Forecast Crossing Info    : {crossing_info}")

        print("\n" + "=" * 75)
        print("VERIFYING NONEXISTENT MERCHANT HANDLING")
        print("=" * 75)
        non_existent = run_merchant_analytics(db, 999)
        print(f"run_merchant_analytics(db, 999) -> {non_existent} (Expected: None)")
        assert non_existent is None
        print("=" * 75 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_analytics_verification()

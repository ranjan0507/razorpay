from typing import Any, Dict, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Dispute, Merchant, Transaction


def get_merchant_dispute_metrics(db: Session, merchant_id: int) -> Dict[str, Any]:
    """Calculate deterministic cohort-based dispute metrics for a merchant.

    Attribute disputes to their associated transaction's timestamp month (cohort)
    rather than the dispute's own timestamp month.
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


def verify_dispute_lag(db: Session, merchant_id: int):
    """Find disputes whose Dispute.timestamp month differs from Transaction.timestamp month

    and confirm cohort attribution.
    """
    lagged_disputes = (
        db.query(
            Dispute.id.label("dispute_id"),
            Dispute.timestamp.label("dispute_ts"),
            Transaction.timestamp.label("tx_ts"),
            func.strftime("%Y-%m", Transaction.timestamp).label("tx_month"),
            func.strftime("%Y-%m", Dispute.timestamp).label("disp_month"),
        )
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(
            Transaction.merchant_id == merchant_id,
            func.strftime("%Y-%m", Transaction.timestamp)
            != func.strftime("%Y-%m", Dispute.timestamp),
        )
        .all()
    )

    return lagged_disputes


def run_analytics_verification():
    """Callable verification runner that computes and prints metrics for all merchants."""
    db = SessionLocal()
    try:
        merchants = db.query(Merchant).order_by(Merchant.id).all()
        if not merchants:
            print("No merchants found in database.")
            return

        print("\n" + "=" * 70)
        print("CORRECTED COHORT ANALYTICS VERIFICATION REPORT (STEP 4A)")
        print("=" * 70)

        for merchant in merchants:
            metrics = get_merchant_dispute_metrics(db, merchant.id)

            print(f"\nMerchant ID {metrics['merchant_id']}: {merchant.name} ({merchant.merchant_type})")
            print("-" * 55)
            print(f"  Total Transactions : {metrics['total_transactions']:,}")
            print(f"  Total Disputes     : {metrics['total_disputes']:,}")
            print(f"  Overall Dispute Rate: {metrics['overall_dispute_rate'] * 100:.3f}% ({metrics['overall_dispute_rate']:.6f})")

            print("\n  Monthly Cohort Metrics (Attributed to Transaction Month):")
            sum_tx = 0
            sum_disp = 0
            for mm in metrics["monthly_metrics"]:
                sum_tx += mm["transaction_count"]
                sum_disp += mm["dispute_count"]
                print(
                    f"    - {mm['month']}: {mm['transaction_count']:6,d} tx | "
                    f"{mm['dispute_count']:4,d} disputes | "
                    f"rate: {mm['dispute_rate'] * 100:.3f}%"
                )

            # Reconcile monthly sums with totals
            tx_reconciled = (sum_tx == metrics["total_transactions"])
            disp_reconciled = (sum_disp == metrics["total_disputes"])

            print(f"\n  Reconciliation Checks:")
            print(f"    - Monthly Tx Sum ({sum_tx:,}) == Total Tx ({metrics['total_transactions']:,}): {'PASSED' if tx_reconciled else 'FAILED'}")
            print(f"    - Monthly Dispute Sum ({sum_disp:,}) == Total Dispute ({metrics['total_disputes']:,}): {'PASSED' if disp_reconciled else 'FAILED'}")

            # Dispute lag verification
            lagged = verify_dispute_lag(db, merchant.id)
            print(f"\n  Dispute Lag Verification:")
            print(f"    - Cross-Month Lagged Disputes Count: {len(lagged)}")
            if lagged:
                # Group by (tx_month -> disp_month)
                lag_counts: Dict[str, int] = {}
                for l in lagged:
                    key = f"{l.tx_month} tx -> {l.disp_month} dispute"
                    lag_counts[key] = lag_counts.get(key, 0) + 1
                for key, cnt in sorted(lag_counts.items()):
                    print(f"      * {key}: {cnt} disputes correctly attributed to {key.split()[0]} cohort")

        print("\n" + "=" * 70 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    run_analytics_verification()

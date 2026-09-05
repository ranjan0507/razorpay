import sys
import os
from datetime import datetime
from sqlalchemy import func

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import Merchant, Transaction, Dispute
from app.analytics import analyze_segment_drivers

def analyze_m2_drivers_split():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("MERCHANT 2 DRIVERS & EVALUATION STRATEGY DETAILED ANALYSIS")
        print("=" * 80)

        int_date = datetime(2026, 8, 15, 0, 0, 0)

        # Fixed Day Windows:
        # Window 1: 15-day comparison
        # Pre: Aug 1, 2026 00:00:00 to Aug 14, 2026 23:59:59 (14 full days)
        # Post: Aug 15, 2026 00:00:00 to Aug 31, 2026 23:59:59 (17 full days)

        # Window 2: 30-day pre vs post available
        # Pre: Jul 16, 2026 00:00:00 to Aug 14, 2026 23:59:59 (30 days)
        # Post: Aug 15, 2026 00:00:00 to Aug 31, 2026 23:59:59 (17 days available in DB)

        pre_30_tx = (
            db.query(Transaction)
            .filter(Transaction.merchant_id == 2)
            .filter(Transaction.timestamp >= datetime(2026, 7, 16, 0, 0, 0))
            .filter(Transaction.timestamp < int_date)
            .all()
        )
        post_avail_tx = (
            db.query(Transaction)
            .filter(Transaction.merchant_id == 2)
            .filter(Transaction.timestamp >= int_date)
            .all()
        )

        disputed_tx_ids = (
            db.query(Dispute.transaction_id)
            .join(Transaction, Dispute.transaction_id == Transaction.id)
            .filter(Transaction.merchant_id == 2)
            .distinct()
            .all()
        )
        disputed_tx_set = {r[0] for r in disputed_tx_ids if r[0] is not None}

        print("\n[Strategy Comparison Breakdown]")

        # Strategy A: Calendar Cohort Comparison
        print("\n--- Strategy A: Calendar-Cohort Comparison ---")
        print("  Available Cohorts:")
        print("    Pre-Intervention Complete Calendar Months  : March 2026, April 2026, May 2026, June 2026, July 2026 (5 full months: 2026-03 to 2026-07)")
        print("    Partial Month                              : August 2026 (contains intervention on Aug 15)")
        print("    Post-Intervention Complete Calendar Months : NONE (Latest transaction timestamp in DB is 2026-08-31)")

        m3_m7_tx = [t for t in db.query(Transaction).filter(Transaction.merchant_id == 2).filter(Transaction.timestamp < datetime(2026, 8, 1, 0, 0, 0)).all()]
        m3_m7_ids = {t.id for t in m3_m7_tx}
        m3_m7_disp = len(disputed_tx_set.intersection(m3_m7_ids))

        m3_m7_seg_tx = [t for t in m3_m7_tx if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        m3_m7_seg_ids = {t.id for t in m3_m7_seg_tx}
        m3_m7_seg_disp = len(disputed_tx_set.intersection(m3_m7_seg_ids))

        print(f"  Pre-Intervention Baseline (March–July 2026):")
        print(f"    Overall Tx: {len(m3_m7_tx)}, Disputed: {m3_m7_disp}, Rate: {m3_m7_disp / len(m3_m7_tx) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(m3_m7_seg_tx)}, Disputed: {m3_m7_seg_disp}, Rate: {m3_m7_seg_disp / len(m3_m7_seg_tx) * 100:.3f}%")
        print(f"  Post-Intervention Complete Calendar Month Observations: 0 (No September 2026 data in DB)")

        # Strategy B: Fixed-Day Comparison (Intra-Month August 2026)
        print("\n--- Strategy B: Fixed-Day Comparison ---")
        aug_1_14_tx = [t for t in db.query(Transaction).filter(Transaction.merchant_id == 2).filter(Transaction.timestamp >= datetime(2026, 8, 1)).filter(Transaction.timestamp < int_date).all()]
        aug_1_14_ids = {t.id for t in aug_1_14_tx}
        aug_1_14_disp = len(disputed_tx_set.intersection(aug_1_14_ids))
        aug_1_14_seg_tx = [t for t in aug_1_14_tx if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        aug_1_14_seg_disp = len(disputed_tx_set.intersection({t.id for t in aug_1_14_seg_tx}))

        aug_15_31_tx = post_avail_tx
        aug_15_31_ids = {t.id for t in aug_15_31_tx}
        aug_15_31_disp = len(disputed_tx_set.intersection(aug_15_31_ids))
        aug_15_31_seg_tx = [t for t in aug_15_31_tx if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        aug_15_31_seg_disp = len(disputed_tx_set.intersection({t.id for t in aug_15_31_seg_tx}))

        print(f"  14-Day Pre-Intervention Window (Aug 1 - Aug 14):")
        print(f"    Overall Tx: {len(aug_1_14_tx)}, Disputed: {aug_1_14_disp}, Rate: {aug_1_14_disp / len(aug_1_14_tx) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(aug_1_14_seg_tx)}, Disputed: {aug_1_14_seg_disp}, Rate: {aug_1_14_seg_disp / len(aug_1_14_seg_tx) * 100:.3f}%")

        print(f"  17-Day Post-Intervention Window (Aug 15 - Aug 31):")
        print(f"    Overall Tx: {len(aug_15_31_tx)}, Disputed: {aug_15_31_disp}, Rate: {aug_15_31_disp / len(aug_15_31_tx) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(aug_15_31_seg_tx)}, Disputed: {aug_15_31_seg_disp}, Rate: {aug_15_31_seg_disp / len(aug_15_31_seg_tx) * 100:.3f}%")

    finally:
        db.close()

if __name__ == "__main__":
    analyze_m2_drivers_split()

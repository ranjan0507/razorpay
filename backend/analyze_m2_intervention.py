import sys
import os
from datetime import datetime, date
from sqlalchemy import func

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import Merchant, Transaction, Dispute

def analyze_m2_intervention():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("MERCHANT 2 INTERVENTION BEFORE/AFTER DATASET ANALYSIS")
        print("=" * 80)

        merchant = db.query(Merchant).filter(Merchant.id == 2).first()
        print(f"Merchant Profile: #{merchant.id} - {merchant.name} ({merchant.merchant_type})")

        # 1. Total transaction date range
        min_date = db.query(func.min(Transaction.timestamp)).filter(Transaction.merchant_id == 2).scalar()
        max_date = db.query(func.max(Transaction.timestamp)).filter(Transaction.merchant_id == 2).scalar()
        print(f"Transaction Timestamp Range : {min_date} to {max_date}")

        # Total transactions and total disputes
        total_tx = db.query(func.count(Transaction.id)).filter(Transaction.merchant_id == 2).scalar()
        
        disputed_tx_ids = (
            db.query(Dispute.transaction_id)
            .join(Transaction, Dispute.transaction_id == Transaction.id)
            .filter(Transaction.merchant_id == 2)
            .distinct()
            .all()
        )
        disputed_tx_set = {r[0] for r in disputed_tx_ids if r[0] is not None}
        total_disp = len(disputed_tx_set)

        print(f"Total Transactions          : {total_tx}")
        print(f"Total Disputed Transactions : {total_disp}")
        print(f"Overall Dispute Rate        : {total_disp / total_tx * 100:.3f}%")

        # 2. Monthly breakdowns (YYYY-MM)
        print("\n" + "-" * 70)
        print("MONTHLY TRANSACTION & DISPUTE BREAKDOWN (ALL COHORTS)")
        print("-" * 70)

        tx_by_month = (
            db.query(
                func.strftime("%Y-%m", Transaction.timestamp).label("month"),
                func.count(Transaction.id).label("tx_count"),
            )
            .filter(Transaction.merchant_id == 2)
            .group_by("month")
            .order_by("month")
            .all()
        )

        all_months = [row.month for row in tx_by_month]
        print(f"All Month Cohorts in DB: {all_months}")

        for row in tx_by_month:
            m = row.month
            tx_cnt = row.tx_count

            # Disputed tx count in month m
            m_disp_cnt = (
                db.query(func.count(Dispute.id))
                .join(Transaction, Dispute.transaction_id == Transaction.id)
                .filter(Transaction.merchant_id == 2)
                .filter(func.strftime("%Y-%m", Transaction.timestamp) == m)
                .scalar()
                or 0
            )

            # Target segment: electronics + Partner_C in month m
            seg_tx_cnt = (
                db.query(func.count(Transaction.id))
                .filter(Transaction.merchant_id == 2)
                .filter(Transaction.product_category == "electronics")
                .filter(Transaction.delivery_partner == "Partner_C")
                .filter(func.strftime("%Y-%m", Transaction.timestamp) == m)
                .scalar()
                or 0
            )

            seg_disp_cnt = (
                db.query(func.count(Dispute.id))
                .join(Transaction, Dispute.transaction_id == Transaction.id)
                .filter(Transaction.merchant_id == 2)
                .filter(Transaction.product_category == "electronics")
                .filter(Transaction.delivery_partner == "Partner_C")
                .filter(func.strftime("%Y-%m", Transaction.timestamp) == m)
                .scalar()
                or 0
            )

            m_rate = (m_disp_cnt / tx_cnt * 100) if tx_cnt > 0 else 0.0
            seg_rate = (seg_disp_cnt / seg_tx_cnt * 100) if seg_tx_cnt > 0 else 0.0

            print(f"Cohort {m}:")
            print(f"  Overall : {m_disp_cnt} disp / {tx_cnt} tx = {m_rate:.3f}%")
            print(f"  Target Seg (Electronics+Partner_C): {seg_disp_cnt} disp / {seg_tx_cnt} tx = {seg_rate:.3f}%")

        # 3. Intervention date split: 2026-08-15
        int_date = datetime(2026, 8, 15, 0, 0, 0)
        print("\n" + "-" * 70)
        print(f"INTERVENTION DATE SPLIT ANALYSIS (Start Date: {int_date})")
        print("-" * 70)

        # Before 2026-08-15
        tx_before_int = (
            db.query(Transaction)
            .filter(Transaction.merchant_id == 2)
            .filter(Transaction.timestamp < int_date)
            .all()
        )
        tx_before_ids = {t.id for t in tx_before_int}
        disp_before_cnt = len(disputed_tx_set.intersection(tx_before_ids))

        # Target segment before 2026-08-15
        seg_tx_before = [t for t in tx_before_int if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        seg_tx_before_ids = {t.id for t in seg_tx_before}
        seg_disp_before_cnt = len(disputed_tx_set.intersection(seg_tx_before_ids))

        # On or after 2026-08-15
        tx_after_int = (
            db.query(Transaction)
            .filter(Transaction.merchant_id == 2)
            .filter(Transaction.timestamp >= int_date)
            .all()
        )
        tx_after_ids = {t.id for t in tx_after_int}
        disp_after_cnt = len(disputed_tx_set.intersection(tx_after_ids))

        # Target segment on or after 2026-08-15
        seg_tx_after = [t for t in tx_after_int if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        seg_tx_after_ids = {t.id for t in seg_tx_after}
        seg_disp_after_cnt = len(disputed_tx_set.intersection(seg_tx_after_ids))

        print("Strict Timestamp Split (< 2026-08-15 vs >= 2026-08-15):")
        print(f"  BEFORE 2026-08-15:")
        print(f"    Overall Tx: {len(tx_before_int)}, Disputed: {disp_before_cnt}, Rate: {disp_before_cnt / len(tx_before_int) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(seg_tx_before)}, Disputed: {seg_disp_before_cnt}, Rate: {seg_disp_before_cnt / len(seg_tx_before) * 100:.3f}%")
        print(f"  AFTER 2026-08-15 (Aug 15 - Aug 31):")
        print(f"    Overall Tx: {len(tx_after_int)}, Disputed: {disp_after_cnt}, Rate: {disp_after_cnt / len(tx_after_int) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(seg_tx_after)}, Disputed: {seg_disp_after_cnt}, Rate: {seg_disp_after_cnt / len(seg_tx_after) * 100:.3f}%")

        # 4. Detailed August 2026 breakdown (Aug 1-14 vs Aug 15-31)
        aug_tx_before_15 = (
            db.query(Transaction)
            .filter(Transaction.merchant_id == 2)
            .filter(Transaction.timestamp >= datetime(2026, 8, 1, 0, 0, 0))
            .filter(Transaction.timestamp < datetime(2026, 8, 15, 0, 0, 0))
            .all()
        )
        aug_tx_before_15_ids = {t.id for t in aug_tx_before_15}
        aug_disp_before_15_cnt = len(disputed_tx_set.intersection(aug_tx_before_15_ids))

        aug_seg_before_15 = [t for t in aug_tx_before_15 if t.product_category == "electronics" and t.delivery_partner == "Partner_C"]
        aug_seg_before_15_ids = {t.id for t in aug_seg_before_15}
        aug_seg_disp_before_15_cnt = len(disputed_tx_set.intersection(aug_seg_before_15_ids))

        print("\nAugust 2026 Intra-Month Split:")
        print(f"  Aug 1 - Aug 14 (Pre-Intervention):")
        print(f"    Overall Tx: {len(aug_tx_before_15)}, Disputed: {aug_disp_before_15_cnt}, Rate: {aug_disp_before_15_cnt / len(aug_tx_before_15) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(aug_seg_before_15)}, Disputed: {aug_seg_disp_before_15_cnt}, Rate: {aug_seg_disp_before_15_cnt / len(aug_seg_before_15) * 100:.3f}%")

        print(f"  Aug 15 - Aug 31 (Post-Intervention):")
        print(f"    Overall Tx: {len(tx_after_int)}, Disputed: {disp_after_cnt}, Rate: {disp_after_cnt / len(tx_after_int) * 100:.3f}%")
        print(f"    Target Seg Tx: {len(seg_tx_after)}, Disputed: {seg_disp_after_cnt}, Rate: {seg_disp_after_cnt / len(seg_tx_after) * 100:.3f}%")

        # 5. Check Strategy B: Fixed-Day Comparison (e.g. 15 days before vs 15 days after)
        # Aug 1-15 (15 days) vs Aug 15-30 (15 days)
        # Or July 16 - Aug 14 (30 days) vs Aug 15 - Sep 13 (30 days)
        # Let's check max date in DB
        print(f"\nMax Date in DB: {max_date}")

    finally:
        db.close()

if __name__ == "__main__":
    analyze_m2_intervention()

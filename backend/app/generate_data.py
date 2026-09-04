from datetime import datetime, timedelta
import random
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Dispute, Merchant, Transaction

# Seed for reproducible synthetic data generation
RANDOM_SEED = 42

# -------------------------------------------------------------------------
# Merchant 1: Healthy E-commerce Scenario Configuration
# -------------------------------------------------------------------------
HEALTHY_ECOMMERCE_CONFIG = {
    "merchant_id": 1,
    "name": "Healthy E-commerce",
    "merchant_type": "ecommerce",
    "risk_threshold": 0.02,
    "alert_threshold": 0.015,
    "historical_baseline": 0.005,
    "monthly_target_volume": 6000,
    "volume_variation": 300,
    "months": [
        ("2026-03-01 00:00:00", "2026-03-31 23:59:59"),
        ("2026-04-01 00:00:00", "2026-04-30 23:59:59"),
        ("2026-05-01 00:00:00", "2026-05-31 23:59:59"),
        ("2026-06-01 00:00:00", "2026-06-30 23:59:59"),
        ("2026-07-01 00:00:00", "2026-07-31 23:59:59"),
        ("2026-08-01 00:00:00", "2026-08-31 23:59:59"),
    ],
    "payment_methods": {
        "card": 0.45,
        "upi": 0.35,
        "netbanking": 0.12,
        "wallet": 0.08,
    },
    "product_categories": {
        "electronics": 0.30,
        "clothing": 0.25,
        "home": 0.20,
        "beauty": 0.15,
        "groceries": 0.10,
    },
    "delivery_partners": {
        "Partner_A": 0.40,
        "Partner_B": 0.35,
        "Partner_C": 0.25,
    },
    "geographies": {
        "Mumbai": 0.25,
        "Delhi": 0.22,
        "Bengaluru": 0.20,
        "Hyderabad": 0.13,
        "Chennai": 0.10,
        "Pune": 0.10,
    },
    "customer_segments": {
        "returning": 0.65,
        "new": 0.35,
    },
    "subscription_type": None,
    "transaction_type": "purchase",
    "status": "completed",
    "amount_params": {
        "mu": 6.5,  # Log-normal mu parameter (~₹665 median)
        "sigma": 0.7,  # Log-normal sigma parameter
        "min_amount": 100.0,
        "max_amount": 25000.0,
    },
}

HEALTHY_DISPUTE_CONFIG = {
    "merchant_id": 1,
    "base_dispute_rate": 0.007,  # ~0.7% stable base dispute rate
    "dispute_reasons": {
        "product_not_received": 0.35,
        "fraud": 0.25,
        "refund_not_processed": 0.20,
        "duplicate_charge": 0.12,
        "other": 0.08,
    },
    "resolution_statuses": {
        "pending": 0.25,
        "resolved": 0.35,
        "accepted": 0.20,
        "rejected": 0.20,
    },
    "min_delay_days": 1,
    "max_delay_days": 14,
}

# -------------------------------------------------------------------------
# Merchant 2: Escalating E-commerce Scenario Configuration
# -------------------------------------------------------------------------
ESCALATING_ECOMMERCE_CONFIG = {
    "merchant_id": 2,
    "name": "Escalating E-commerce",
    "merchant_type": "ecommerce",
    "risk_threshold": 0.02,
    "alert_threshold": 0.015,
    "historical_baseline": 0.005,
    "monthly_target_volume": 6000,
    "volume_variation": 300,
    "months": [
        ("2026-03-01 00:00:00", "2026-03-31 23:59:59"),
        ("2026-04-01 00:00:00", "2026-04-30 23:59:59"),
        ("2026-05-01 00:00:00", "2026-05-31 23:59:59"),
        ("2026-06-01 00:00:00", "2026-06-30 23:59:59"),
        ("2026-07-01 00:00:00", "2026-07-31 23:59:59"),
        ("2026-08-01 00:00:00", "2026-08-31 23:59:59"),
    ],
    "payment_methods": {
        "card": 0.45,
        "upi": 0.35,
        "netbanking": 0.12,
        "wallet": 0.08,
    },
    "product_categories": {
        "electronics": 0.30,
        "clothing": 0.25,
        "home": 0.20,
        "beauty": 0.15,
        "groceries": 0.10,
    },
    "delivery_partners": {
        "Partner_A": 0.40,
        "Partner_B": 0.35,
        "Partner_C": 0.25,
    },
    "geographies": {
        "Mumbai": 0.25,
        "Delhi": 0.22,
        "Bengaluru": 0.20,
        "Hyderabad": 0.13,
        "Chennai": 0.10,
        "Pune": 0.10,
    },
    "customer_segments": {
        "returning": 0.65,
        "new": 0.35,
    },
    "subscription_type": None,
    "transaction_type": "purchase",
    "status": "completed",
    "amount_params": {
        "mu": 6.5,
        "sigma": 0.7,
        "min_amount": 100.0,
        "max_amount": 25000.0,
    },
}

ESCALATING_DISPUTE_CONFIG = {
    "merchant_id": 2,
    "base_dispute_rate": 0.007,
    "partner_c_electronics_monthly_rates": {
        "2026-03": 0.02,
        "2026-04": 0.04,
        "2026-05": 0.07,
        "2026-06": 0.10,
        "2026-07": 0.14,
        "2026-08": 0.175,
    },
    "standard_reasons": {
        "product_not_received": 0.35,
        "fraud": 0.25,
        "refund_not_processed": 0.20,
        "duplicate_charge": 0.12,
        "other": 0.08,
    },
    "target_segment_reasons": {
        "product_not_received": 0.70,
        "refund_not_processed": 0.10,
        "fraud": 0.08,
        "duplicate_charge": 0.07,
        "other": 0.05,
    },
    "resolution_statuses": {
        "pending": 0.25,
        "resolved": 0.35,
        "accepted": 0.20,
        "rejected": 0.20,
    },
    "min_delay_days": 1,
    "max_delay_days": 14,
}

# -------------------------------------------------------------------------
# Merchant 3: Healthy Subscription Scenario Configuration
# -------------------------------------------------------------------------
HEALTHY_SUBSCRIPTION_CONFIG = {
    "merchant_id": 3,
    "name": "Healthy Subscription",
    "merchant_type": "subscription",
    "risk_threshold": 0.02,
    "alert_threshold": 0.015,
    "historical_baseline": 0.005,
    "monthly_target_volume": 6000,
    "volume_variation": 300,
    "months": [
        ("2026-03-01 00:00:00", "2026-03-31 23:59:59"),
        ("2026-04-01 00:00:00", "2026-04-30 23:59:59"),
        ("2026-05-01 00:00:00", "2026-05-31 23:59:59"),
        ("2026-06-01 00:00:00", "2026-06-30 23:59:59"),
        ("2026-07-01 00:00:00", "2026-07-31 23:59:59"),
        ("2026-08-01 00:00:00", "2026-08-31 23:59:59"),
    ],
    "subscription_types": {
        "monthly": 0.80,
        "annual": 0.20,
    },
    "transaction_types": {
        "renewal": 0.70,
        "purchase": 0.30,
    },
    "payment_methods": {
        "card": 0.45,
        "upi": 0.35,
        "netbanking": 0.12,
        "wallet": 0.08,
    },
    "product_categories": None,
    "delivery_partners": None,
    "geographies": {
        "Mumbai": 0.25,
        "Delhi": 0.22,
        "Bengaluru": 0.20,
        "Hyderabad": 0.13,
        "Chennai": 0.10,
        "Pune": 0.10,
    },
    "customer_segments": {
        "returning": 0.65,
        "new": 0.35,
    },
    "status": "completed",
    "amount_params": {
        "monthly": {"mu": 6.2, "sigma": 0.5, "min_amount": 199.0, "max_amount": 1999.0},
        "annual": {"mu": 8.5, "sigma": 0.5, "min_amount": 1999.0, "max_amount": 14999.0},
    },
}

HEALTHY_SUBSCRIPTION_DISPUTE_CONFIG = {
    "merchant_id": 3,
    "base_dispute_rate": 0.007,
    "dispute_reasons": {
        "product_not_received": 0.35,
        "fraud": 0.25,
        "refund_not_processed": 0.20,
        "duplicate_charge": 0.12,
        "other": 0.08,
    },
    "resolution_statuses": {
        "pending": 0.25,
        "resolved": 0.35,
        "accepted": 0.20,
        "rejected": 0.20,
    },
    "min_delay_days": 1,
    "max_delay_days": 14,
}

# -------------------------------------------------------------------------
# Merchant 4: Escalating Subscription Scenario Configuration
# -------------------------------------------------------------------------
ESCALATING_SUBSCRIPTION_CONFIG = {
    "merchant_id": 4,
    "name": "Escalating Subscription",
    "merchant_type": "subscription",
    "risk_threshold": 0.02,
    "alert_threshold": 0.015,
    "historical_baseline": 0.005,
    "monthly_target_volume": 6000,
    "volume_variation": 300,
    "months": [
        ("2026-03-01 00:00:00", "2026-03-31 23:59:59"),
        ("2026-04-01 00:00:00", "2026-04-30 23:59:59"),
        ("2026-05-01 00:00:00", "2026-05-31 23:59:59"),
        ("2026-06-01 00:00:00", "2026-06-30 23:59:59"),
        ("2026-07-01 00:00:00", "2026-07-31 23:59:59"),
        ("2026-08-01 00:00:00", "2026-08-31 23:59:59"),
    ],
    "subscription_types": {
        "monthly": 0.80,
        "annual": 0.20,
    },
    "transaction_types": {
        "renewal": 0.70,
        "purchase": 0.30,
    },
    "payment_methods": {
        "card": 0.45,
        "upi": 0.35,
        "netbanking": 0.12,
        "wallet": 0.08,
    },
    "product_categories": None,
    "delivery_partners": None,
    "geographies": {
        "Mumbai": 0.25,
        "Delhi": 0.22,
        "Bengaluru": 0.20,
        "Hyderabad": 0.13,
        "Chennai": 0.10,
        "Pune": 0.10,
    },
    "customer_segments": {
        "returning": 0.65,
        "new": 0.35,
    },
    "status": "completed",
    "amount_params": {
        "monthly": {"mu": 6.2, "sigma": 0.5, "min_amount": 199.0, "max_amount": 1999.0},
        "annual": {"mu": 8.5, "sigma": 0.5, "min_amount": 1999.0, "max_amount": 14999.0},
    },
}

ESCALATING_SUBSCRIPTION_DISPUTE_CONFIG = {
    "merchant_id": 4,
    "base_dispute_rate": 0.007,
    "annual_renewal_monthly_rates": {
        "2026-03": 0.02,
        "2026-04": 0.04,
        "2026-05": 0.07,
        "2026-06": 0.10,
        "2026-07": 0.14,
        "2026-08": 0.175,
    },
    "standard_reasons": {
        "product_not_received": 0.35,
        "fraud": 0.25,
        "refund_not_processed": 0.20,
        "duplicate_charge": 0.12,
        "other": 0.08,
    },
    "target_segment_reasons": {
        "refund_not_processed": 0.65,
        "other": 0.15,
        "fraud": 0.10,
        "duplicate_charge": 0.07,
        "product_not_received": 0.03,
    },
    "resolution_statuses": {
        "pending": 0.25,
        "resolved": 0.35,
        "accepted": 0.20,
        "rejected": 0.20,
    },
    "min_delay_days": 1,
    "max_delay_days": 14,
}


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def weighted_choice(distribution: dict[str, float]) -> str:
    """Select a single key from a dict of {key: probability_weight}."""
    keys = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(keys, weights=weights, k=1)[0]


def generate_amount(params: dict) -> float:
    """Generate a realistic transaction amount using a bounded log-normal distribution."""
    raw_amount = random.lognormvariate(params["mu"], params["sigma"])
    bounded_amount = max(params["min_amount"], min(params["max_amount"], raw_amount))
    return round(bounded_amount, 2)


def generate_random_timestamp(start_str: str, end_str: str) -> datetime:
    """Generate a random datetime within the given start and end timestamps."""
    start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
    total_seconds = int((end_dt - start_dt).total_seconds())
    random_second = random.randint(0, total_seconds)
    return start_dt + timedelta(seconds=random_second)


# -------------------------------------------------------------------------
# Transaction Generator
# -------------------------------------------------------------------------
def generate_merchant_transactions(db: Session, config: dict):
    """Generate synthetic transactions for a given merchant configuration."""
    merchant_id = config["merchant_id"]
    random.seed(RANDOM_SEED + merchant_id * 100)

    # 1. Ensure Merchant exists in DB
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        merchant = Merchant(
            id=merchant_id,
            name=config["name"],
            merchant_type=config["merchant_type"],
            risk_threshold=config["risk_threshold"],
            alert_threshold=config["alert_threshold"],
            historical_baseline=config["historical_baseline"],
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        print(f"Created Merchant: {merchant.name} (ID: {merchant.id})")
    else:
        print(f"Merchant {merchant.name} (ID: {merchant.id}) already exists.")

    # 2. Idempotency: Clear existing disputes FIRST, then transactions for merchant_id
    existing_tx_ids = (
        db.query(Transaction.id).filter(Transaction.merchant_id == merchant_id).scalar_subquery()
    )
    deleted_disputes = (
        db.query(Dispute).filter(Dispute.transaction_id.in_(existing_tx_ids)).delete(synchronize_session=False)
    )
    deleted_transactions = (
        db.query(Transaction).filter(Transaction.merchant_id == merchant_id).delete(synchronize_session=False)
    )
    db.commit()
    if deleted_transactions > 0 or deleted_disputes > 0:
        print(
            f"Cleared {deleted_disputes} disputes and {deleted_transactions} transactions for Merchant {merchant_id}."
        )

    # 3. Generate transactions month by month
    transactions_to_insert = []

    for month_start, month_end in config["months"]:
        monthly_count = config["monthly_target_volume"] + random.randint(
            -config["volume_variation"], config["volume_variation"]
        )

        for _ in range(monthly_count):
            timestamp = generate_random_timestamp(month_start, month_end)

            # E-commerce vs Subscription attributes
            product_category = weighted_choice(config["product_categories"]) if config.get("product_categories") else None
            delivery_partner = weighted_choice(config["delivery_partners"]) if config.get("delivery_partners") else None
            subscription_type = weighted_choice(config["subscription_types"]) if config.get("subscription_types") else config.get("subscription_type")
            transaction_type = weighted_choice(config["transaction_types"]) if config.get("transaction_types") else config.get("transaction_type")

            # Determine amount
            if isinstance(config["amount_params"], dict) and subscription_type in config["amount_params"]:
                amount = generate_amount(config["amount_params"][subscription_type])
            else:
                amount = generate_amount(config["amount_params"])

            payment_method = weighted_choice(config["payment_methods"])
            geography = weighted_choice(config["geographies"])
            customer_segment = weighted_choice(config["customer_segments"])

            tx = Transaction(
                merchant_id=merchant_id,
                timestamp=timestamp,
                amount=amount,
                payment_method=payment_method,
                product_category=product_category,
                delivery_partner=delivery_partner,
                geography=geography,
                customer_segment=customer_segment,
                subscription_type=subscription_type,
                transaction_type=transaction_type,
                status=config["status"],
            )
            transactions_to_insert.append(tx)

    # Sort transactions chronologically by timestamp
    transactions_to_insert.sort(key=lambda t: t.timestamp)

    # 4. Bulk insert into database
    print(f"Inserting {len(transactions_to_insert)} generated transactions for Merchant {merchant_id} into SQLite...")
    batch_size = 5000
    for i in range(0, len(transactions_to_insert), batch_size):
        db.bulk_save_objects(transactions_to_insert[i : i + batch_size])
        db.commit()

    print(f"Transaction generation for Merchant {merchant_id} complete successfully!")


# -------------------------------------------------------------------------
# Dispute Generators
# -------------------------------------------------------------------------
def generate_healthy_disputes(db: Session, config: dict):
    """Generate synthetic disputes for a healthy merchant based on stable ~0.7% probability."""
    merchant_id = config["merchant_id"]
    random.seed(RANDOM_SEED + merchant_id * 100 + 1)

    tx_ids_subquery = (
        db.query(Transaction.id).filter(Transaction.merchant_id == merchant_id).scalar_subquery()
    )
    deleted_disputes = (
        db.query(Dispute)
        .filter(Dispute.transaction_id.in_(tx_ids_subquery))
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted_disputes > 0:
        print(f"Cleared {deleted_disputes} existing disputes for Merchant {merchant_id}.")

    merchant_transactions = (
        db.query(Transaction)
        .filter(Transaction.merchant_id == merchant_id)
        .order_by(Transaction.timestamp)
        .all()
    )

    if not merchant_transactions:
        print(f"No transactions found for Merchant {merchant_id}. Generate transactions first.")
        return

    disputes_to_insert = []
    base_rate = config["base_dispute_rate"]

    for tx in merchant_transactions:
        if random.random() < base_rate:
            delay_seconds = random.randint(
                config["min_delay_days"] * 86400, config["max_delay_days"] * 86400
            )
            dispute_dt = tx.timestamp + timedelta(seconds=delay_seconds)
            reason = weighted_choice(config["dispute_reasons"])
            status = weighted_choice(config["resolution_statuses"])

            dispute = Dispute(
                transaction_id=tx.id,
                timestamp=dispute_dt,
                dispute_reason=reason,
                dispute_amount=tx.amount,
                resolution_status=status,
            )
            disputes_to_insert.append(dispute)

    print(f"Inserting {len(disputes_to_insert)} generated disputes for Merchant {merchant_id} into SQLite...")
    batch_size = 5000
    for i in range(0, len(disputes_to_insert), batch_size):
        db.bulk_save_objects(disputes_to_insert[i : i + batch_size])
        db.commit()

    print(f"Dispute generation for Merchant {merchant_id} complete successfully!")


def generate_escalating_ecommerce_disputes(db: Session, config: dict = ESCALATING_DISPUTE_CONFIG):
    """Generate synthetic disputes for Merchant 2 with escalating risk on Partner C + Electronics."""
    merchant_id = config["merchant_id"]
    random.seed(RANDOM_SEED + merchant_id * 100 + 1)

    m2_tx_ids_subquery = (
        db.query(Transaction.id).filter(Transaction.merchant_id == merchant_id).scalar_subquery()
    )
    deleted_disputes = (
        db.query(Dispute)
        .filter(Dispute.transaction_id.in_(m2_tx_ids_subquery))
        .delete(synchronize_session=False)
    )
    db.commit()

    m2_transactions = (
        db.query(Transaction)
        .filter(Transaction.merchant_id == merchant_id)
        .order_by(Transaction.timestamp)
        .all()
    )

    if not m2_transactions:
        print(f"No transactions found for Merchant {merchant_id}. Generate transactions first.")
        return

    disputes_to_insert = []

    for tx in m2_transactions:
        is_target_segment = (
            tx.delivery_partner == "Partner_C" and tx.product_category == "electronics"
        )
        tx_month = tx.timestamp.strftime("%Y-%m")

        if is_target_segment:
            dispute_rate = config["partner_c_electronics_monthly_rates"].get(
                tx_month, config["base_dispute_rate"]
            )
            reasons = config["target_segment_reasons"]
        else:
            dispute_rate = config["base_dispute_rate"]
            reasons = config["standard_reasons"]

        if random.random() < dispute_rate:
            delay_seconds = random.randint(
                config["min_delay_days"] * 86400, config["max_delay_days"] * 86400
            )
            dispute_dt = tx.timestamp + timedelta(seconds=delay_seconds)
            reason = weighted_choice(reasons)
            status = weighted_choice(config["resolution_statuses"])

            dispute = Dispute(
                transaction_id=tx.id,
                timestamp=dispute_dt,
                dispute_reason=reason,
                dispute_amount=tx.amount,
                resolution_status=status,
            )
            disputes_to_insert.append(dispute)

    print(f"Inserting {len(disputes_to_insert)} generated disputes for Merchant {merchant_id} into SQLite...")
    batch_size = 5000
    for i in range(0, len(disputes_to_insert), batch_size):
        db.bulk_save_objects(disputes_to_insert[i : i + batch_size])
        db.commit()

    print(f"Dispute generation for Merchant {merchant_id} complete successfully!")


def generate_escalating_subscription_disputes(db: Session, config: dict = ESCALATING_SUBSCRIPTION_DISPUTE_CONFIG):
    """Generate synthetic disputes for Merchant 4 with escalating risk on Annual + Renewal."""
    merchant_id = config["merchant_id"]
    random.seed(RANDOM_SEED + merchant_id * 100 + 1)

    m4_tx_ids_subquery = (
        db.query(Transaction.id).filter(Transaction.merchant_id == merchant_id).scalar_subquery()
    )
    deleted_disputes = (
        db.query(Dispute)
        .filter(Dispute.transaction_id.in_(m4_tx_ids_subquery))
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted_disputes > 0:
        print(f"Cleared {deleted_disputes} existing disputes for Merchant {merchant_id}.")

    m4_transactions = (
        db.query(Transaction)
        .filter(Transaction.merchant_id == merchant_id)
        .order_by(Transaction.timestamp)
        .all()
    )

    if not m4_transactions:
        print(f"No transactions found for Merchant {merchant_id}. Generate transactions first.")
        return

    disputes_to_insert = []

    for tx in m4_transactions:
        is_target_segment = (
            tx.subscription_type == "annual" and tx.transaction_type == "renewal"
        )
        tx_month = tx.timestamp.strftime("%Y-%m")

        if is_target_segment:
            dispute_rate = config["annual_renewal_monthly_rates"].get(
                tx_month, config["base_dispute_rate"]
            )
            reasons = config["target_segment_reasons"]
        else:
            dispute_rate = config["base_dispute_rate"]
            reasons = config["standard_reasons"]

        if random.random() < dispute_rate:
            delay_seconds = random.randint(
                config["min_delay_days"] * 86400, config["max_delay_days"] * 86400
            )
            dispute_dt = tx.timestamp + timedelta(seconds=delay_seconds)
            reason = weighted_choice(reasons)
            status = weighted_choice(config["resolution_statuses"])

            dispute = Dispute(
                transaction_id=tx.id,
                timestamp=dispute_dt,
                dispute_reason=reason,
                dispute_amount=tx.amount,
                resolution_status=status,
            )
            disputes_to_insert.append(dispute)

    print(f"Inserting {len(disputes_to_insert)} generated disputes for Merchant {merchant_id} into SQLite...")
    batch_size = 5000
    for i in range(0, len(disputes_to_insert), batch_size):
        db.bulk_save_objects(disputes_to_insert[i : i + batch_size])
        db.commit()

    print(f"Dispute generation for Merchant {merchant_id} complete successfully!")


# -------------------------------------------------------------------------
# Verification Reports
# -------------------------------------------------------------------------
def print_m4_verification_report(db: Session):
    """Print verification report for Merchant 4 (Escalating Subscription)."""
    merchant_id = 4

    # 1 & 2. Counts
    m4_tx_count = db.query(func.count(Transaction.id)).filter(Transaction.merchant_id == merchant_id).scalar()
    m4_dispute_count = (
        db.query(func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .scalar()
    )

    # 3. Overall rate
    overall_rate = (m4_dispute_count / m4_tx_count * 100) if m4_tx_count > 0 else 0.0

    print("\n" + "=" * 65)
    print(f"VERIFICATION REPORT FOR MERCHANT {merchant_id} (Escalating Subscription)")
    print("=" * 65)
    print(f"1. M4 Transaction Count : {m4_tx_count}")
    print(f"2. M4 Dispute Count     : {m4_dispute_count}")
    print(f"3. Overall Dispute Rate : {overall_rate:.3f}%")

    # 4, 5, 6, 7. Monthly Breakdown (Overall vs Annual + Renewal)
    print("\n4, 5, 6, 7. Monthly Breakdown (Overall vs Annual + Renewal):")
    tx_by_month = dict(
        db.query(func.strftime('%Y-%m', Transaction.timestamp), func.count(Transaction.id))
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(func.strftime('%Y-%m', Transaction.timestamp))
        .all()
    )
    disps_by_month = dict(
        db.query(func.strftime('%Y-%m', Transaction.timestamp), func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(func.strftime('%Y-%m', Transaction.timestamp))
        .all()
    )

    ar_tx_by_month = dict(
        db.query(func.strftime('%Y-%m', Transaction.timestamp), func.count(Transaction.id))
        .filter(Transaction.merchant_id == merchant_id, Transaction.subscription_type == "annual", Transaction.transaction_type == "renewal")
        .group_by(func.strftime('%Y-%m', Transaction.timestamp))
        .all()
    )
    ar_disps_by_month = dict(
        db.query(func.strftime('%Y-%m', Transaction.timestamp), func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id, Transaction.subscription_type == "annual", Transaction.transaction_type == "renewal")
        .group_by(func.strftime('%Y-%m', Transaction.timestamp))
        .all()
    )

    for m in sorted(tx_by_month.keys()):
        m_tx = tx_by_month[m]
        m_disp = disps_by_month.get(m, 0)
        m_rate = (m_disp / m_tx * 100) if m_tx > 0 else 0.0

        ar_tx = ar_tx_by_month.get(m, 0)
        ar_disp = ar_disps_by_month.get(m, 0)
        ar_rate = (ar_disp / ar_tx * 100) if ar_tx > 0 else 0.0

        print(f"  - {m}: Overall {m_disp}/{m_tx} ({m_rate:.2f}%) | Annual + Renewal {ar_disp}/{ar_tx} ({ar_rate:.2f}%)")

    # 8. Dispute rate outside Annual + Renewal
    non_ar_tx = db.query(func.count(Transaction.id)).filter(
        Transaction.merchant_id == merchant_id,
        ~((Transaction.subscription_type == "annual") & (Transaction.transaction_type == "renewal"))
    ).scalar()
    non_ar_disp = db.query(func.count(Dispute.id)).join(Transaction, Dispute.transaction_id == Transaction.id).filter(
        Transaction.merchant_id == merchant_id,
        ~((Transaction.subscription_type == "annual") & (Transaction.transaction_type == "renewal"))
    ).scalar()
    non_ar_rate = (non_ar_disp / non_ar_tx * 100) if non_ar_tx > 0 else 0.0
    print(f"\n8. Overall Dispute Rate Outside Annual + Renewal: {non_ar_disp} / {non_ar_tx} ({non_ar_rate:.3f}%)")

    # 9. Dispute reasons FOR Annual + Renewal
    print("\n9. Dispute Reasons FOR Annual + Renewal:")
    ar_reasons = (
        db.query(Dispute.dispute_reason, func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id, Transaction.subscription_type == "annual", Transaction.transaction_type == "renewal")
        .group_by(Dispute.dispute_reason)
        .all()
    )
    ar_disp_total = sum(c for _, c in ar_reasons)
    for r, count in sorted(ar_reasons, key=lambda x: x[1], reverse=True):
        pct = (count / ar_disp_total * 100) if ar_disp_total > 0 else 0.0
        print(f"  - {r}: {count} ({pct:.1f}%)")

    # 10. Dispute reasons OUTSIDE Annual + Renewal
    print("\n10. Dispute Reasons OUTSIDE Annual + Renewal:")
    non_ar_reasons = (
        db.query(Dispute.dispute_reason, func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(
            Transaction.merchant_id == merchant_id,
            ~((Transaction.subscription_type == "annual") & (Transaction.transaction_type == "renewal"))
        )
        .group_by(Dispute.dispute_reason)
        .all()
    )
    non_ar_disp_total = sum(c for _, c in non_ar_reasons)
    for r, count in sorted(non_ar_reasons, key=lambda x: x[1], reverse=True):
        pct = (count / non_ar_disp_total * 100) if non_ar_disp_total > 0 else 0.0
        print(f"  - {r}: {count} ({pct:.1f}%)")

    # 11. Dispute rate by subscription_type
    print("\n11. Dispute Rate by Subscription Type:")
    tx_by_sub = dict(
        db.query(Transaction.subscription_type, func.count(Transaction.id))
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(Transaction.subscription_type)
        .all()
    )
    disps_by_sub = dict(
        db.query(Transaction.subscription_type, func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(Transaction.subscription_type)
        .all()
    )
    for st in sorted(tx_by_sub.keys()):
        s_tx = tx_by_sub[st]
        s_disp = disps_by_sub.get(st, 0)
        s_rate = (s_disp / s_tx * 100) if s_tx > 0 else 0.0
        print(f"  - {st}: {s_disp} / {s_tx} ({s_rate:.3f}%)")

    # 12. Dispute rate by transaction_type
    print("\n12. Dispute Rate by Transaction Type:")
    tx_by_tt = dict(
        db.query(Transaction.transaction_type, func.count(Transaction.id))
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(Transaction.transaction_type)
        .all()
    )
    disps_by_tt = dict(
        db.query(Transaction.transaction_type, func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id)
        .group_by(Transaction.transaction_type)
        .all()
    )
    for tt in sorted(tx_by_tt.keys()):
        t_tx = tx_by_tt[tt]
        t_disp = disps_by_tt.get(tt, 0)
        t_rate = (t_disp / t_tx * 100) if t_tx > 0 else 0.0
        print(f"  - {tt}: {t_disp} / {t_tx} ({t_rate:.3f}%)")

    # 13. Foreign-key integrity check
    invalid_fk_count = (
        db.query(func.count(Dispute.id))
        .outerjoin(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Dispute.transaction_id != None, Transaction.id == None)
        .scalar()
    )
    print(f"\n13. Foreign-Key Integrity Check: {'PASSED' if invalid_fk_count == 0 else 'FAILED'} (Invalid FKs: {invalid_fk_count})")

    # 14. Timestamp chronology check
    invalid_time_count = (
        db.query(func.count(Dispute.id))
        .join(Transaction, Dispute.transaction_id == Transaction.id)
        .filter(Transaction.merchant_id == merchant_id, Dispute.timestamp <= Transaction.timestamp)
        .scalar()
    )
    print(f"14. Timestamp Chronology Check (Dispute > Transaction): {'PASSED' if invalid_time_count == 0 else 'FAILED'} (Invalid Timestamps: {invalid_time_count})")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        # Step 3A & 3B: Merchant 1 (Healthy E-commerce)
        generate_merchant_transactions(db, HEALTHY_ECOMMERCE_CONFIG)
        generate_healthy_disputes(db, HEALTHY_DISPUTE_CONFIG)

        # Step 3C & 3D: Merchant 2 (Escalating E-commerce)
        generate_merchant_transactions(db, ESCALATING_ECOMMERCE_CONFIG)
        generate_escalating_ecommerce_disputes(db, ESCALATING_DISPUTE_CONFIG)

        # Step 3E & 3F: Merchant 3 (Healthy Subscription)
        generate_merchant_transactions(db, HEALTHY_SUBSCRIPTION_CONFIG)
        generate_healthy_disputes(db, HEALTHY_SUBSCRIPTION_DISPUTE_CONFIG)

        # Step 3G & 3H: Merchant 4 (Escalating Subscription)
        generate_merchant_transactions(db, ESCALATING_SUBSCRIPTION_CONFIG)
        generate_escalating_subscription_disputes(db, ESCALATING_SUBSCRIPTION_DISPUTE_CONFIG)

        # Print M4 verification report
        print_m4_verification_report(db)
    finally:
        db.close()

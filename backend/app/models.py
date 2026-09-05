from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Merchant(Base):
    """Represents a merchant monitored by RiskWatch."""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    merchant_type: Mapped[str] = mapped_column(String(100))
    risk_threshold: Mapped[float] = mapped_column(Float)
    alert_threshold: Mapped[float] = mapped_column(Float)
    historical_baseline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan"
    )
    interventions: Mapped[list["Intervention"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan"
    )


class Transaction(Base):
    """Represents a payment transaction supporting both e-commerce and subscription scenarios."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[float] = mapped_column(Float)
    payment_method: Mapped[str] = mapped_column(String(50))
    product_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_partner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geography: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    customer_segment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subscription_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50))

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    disputes: Mapped[list["Dispute"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class Dispute(Base):
    """Represents a dispute/chargeback associated with a transaction."""

    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    dispute_reason: Mapped[str] = mapped_column(String(255))
    dispute_amount: Mapped[float] = mapped_column(Float)
    resolution_status: Mapped[str] = mapped_column(String(50))

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="disputes")


class Intervention(Base):
    """Represents a merchant action taken in response to risk."""

    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    action_description: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    target_segment: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="interventions")

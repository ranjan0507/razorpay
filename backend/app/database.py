from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Path to SQLite database file inside backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "disputeguard.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create synchronous SQLite engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all ORM models using SQLAlchemy 2.x DeclarativeBase
class Base(DeclarativeBase):
    pass


def init_db():
    """Import models and create database tables if they do not exist."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

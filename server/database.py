from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# SQLite database URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feedback.db")

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_feedback_table_columns():
    """Ensure optional columns exist on feedback_entries table."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        # Rely on migrations for non-SQLite databases
        return

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(feedback_entries);"))
        columns = {row[1] for row in result}
        if "story_metadata" not in columns:
            conn.execute(text("ALTER TABLE feedback_entries ADD COLUMN story_metadata TEXT;"))


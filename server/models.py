from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to feedback entries
    feedback_entries = relationship("FeedbackEntry", back_populates="owner", cascade="all, delete-orphan")


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    sentiment = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    user_story = Column(Text, nullable=True)
    story_metadata = Column(Text, nullable=True)
    insights = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to user
    owner = relationship("User", back_populates="feedback_entries")


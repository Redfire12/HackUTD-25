from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

# Feedback schemas
class FeedbackCreate(BaseModel):
    text: str

class FeedbackResponse(BaseModel):
    id: int
    text: str
    sentiment: Optional[float]
    sentiment_label: Optional[str]
    user_story: Optional[str]
    insights: Optional[Dict[str, Any]]
    story_source: Optional[str] = None
    story_model: Optional[str] = None
    story_reason: Optional[str] = None
    insights_source: Optional[str] = None
    insights_model: Optional[str] = None
    insights_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SentimentResponse(BaseModel):
    sentiment: float
    label: str

class StoryResponse(BaseModel):
    story: str
    source: str  # "huggingface" or "fallback"
    model: Optional[str] = None
    reason: Optional[str] = None

class InsightsResponse(BaseModel):
    themes: List[Dict[str, Any]]
    anomalies: List[str]
    timestamp: str
    source: str  # "huggingface" or "fallback"
    summary: Optional[str] = None
    model: Optional[str] = None
    reason: Optional[str] = None


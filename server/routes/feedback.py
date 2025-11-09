from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, FeedbackEntry
from schemas import FeedbackCreate, FeedbackResponse, SentimentResponse, StoryResponse, InsightsResponse
from auth import get_current_user
from services.sentiment import analyze_sentiment
from services.openai_service import generate_story_with_retry, generate_insights_with_retry
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/analyze", response_model=SentimentResponse)
def analyze_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze sentiment of feedback."""
    result = analyze_sentiment(feedback.text)
    logger.info(f"Sentiment analyzed for user {current_user.username}: {result['label']}")
    return result

@router.post("/generate-story", response_model=StoryResponse)
def generate_story(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate user story from feedback."""
    result = generate_story_with_retry(feedback.text)
    logger.info(f"Story generated for user {current_user.username} (source: {result['source']})")
    return result

@router.post("/insights", response_model=InsightsResponse)
def get_insights(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights from feedback."""
    result = generate_insights_with_retry(feedback.text)
    logger.info(f"Insights generated for user {current_user.username} (source: {result.get('source', 'unknown')})")
    return result

@router.post("/submit", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback and get complete analysis (sentiment, story, insights)."""
    # Analyze sentiment
    sentiment_result = analyze_sentiment(feedback.text)
    
    # Generate story
    story_result = generate_story_with_retry(feedback.text)
    logger.info(f"Story generated for user {current_user.username} (source: {story_result.get('source', 'unknown')})")
    
    # Generate insights
    insights_result = generate_insights_with_retry(feedback.text)
    logger.info(f"Insights generated for user {current_user.username} (source: {insights_result.get('source', 'unknown')})")
    
    # Save to database
    db_entry = FeedbackEntry(
        user_id=current_user.id,
        text=feedback.text,
        sentiment=sentiment_result["sentiment"],
        sentiment_label=sentiment_result["label"],
        user_story=story_result["story"],
        story_metadata=json.dumps(story_result),
        insights=json.dumps(insights_result)
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    logger.info(f"Feedback submitted by user {current_user.username} (ID: {db_entry.id})")
    
    # Return response with structured data
    return FeedbackResponse(
        id=db_entry.id,
        text=db_entry.text,
        sentiment=db_entry.sentiment,
        sentiment_label=db_entry.sentiment_label,
        user_story=db_entry.user_story,
        insights=insights_result,  # Already a dict, no need to parse
        story_source=story_result.get("source"),
        story_model=story_result.get("model"),
        story_reason=story_result.get("reason"),
        insights_source=insights_result.get("source") if isinstance(insights_result, dict) else None,
        insights_model=insights_result.get("model") if isinstance(insights_result, dict) else None,
        insights_reason=insights_result.get("reason") if isinstance(insights_result, dict) else None,
        created_at=db_entry.created_at
    )

@router.get("/history", response_model=List[FeedbackResponse])
def get_feedback_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get user's feedback history."""
    entries = db.query(FeedbackEntry)\
        .filter(FeedbackEntry.user_id == current_user.id)\
        .order_by(FeedbackEntry.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    result = []
    for entry in entries:
        story_meta = {}
        if entry.story_metadata:
            try:
                story_meta = json.loads(entry.story_metadata)
            except json.JSONDecodeError:
                story_meta = {}
        insights_dict = {}
        if entry.insights:
            try:
                insights_dict = json.loads(entry.insights) if isinstance(entry.insights, str) else entry.insights
            except json.JSONDecodeError:
                insights_dict = {}
        
        result.append(FeedbackResponse(
            id=entry.id,
            text=entry.text,
            sentiment=entry.sentiment,
            sentiment_label=entry.sentiment_label,
            user_story=entry.user_story,
            insights=insights_dict,
            story_source=story_meta.get("source"),
            story_model=story_meta.get("model"),
            story_reason=story_meta.get("reason"),
            insights_source=insights_dict.get("source") if isinstance(insights_dict, dict) else None,
            insights_model=insights_dict.get("model") if isinstance(insights_dict, dict) else None,
            insights_reason=insights_dict.get("reason") if isinstance(insights_dict, dict) else None,
            created_at=entry.created_at
        ))
    
    return result

@router.get("/{feedback_id}", response_model=FeedbackResponse)
def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific feedback entry."""
    entry = db.query(FeedbackEntry)\
        .filter(FeedbackEntry.id == feedback_id)\
        .filter(FeedbackEntry.user_id == current_user.id)\
        .first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    insights_dict = {}
    if entry.insights:
        try:
            insights_dict = json.loads(entry.insights) if isinstance(entry.insights, str) else entry.insights
        except json.JSONDecodeError:
            insights_dict = {}
    story_meta = {}
    if entry.story_metadata:
        try:
            story_meta = json.loads(entry.story_metadata)
        except json.JSONDecodeError:
            story_meta = {}
    
    return FeedbackResponse(
        id=entry.id,
        text=entry.text,
        sentiment=entry.sentiment,
        sentiment_label=entry.sentiment_label,
        user_story=entry.user_story,
        insights=insights_dict,
        story_source=story_meta.get("source"),
        story_model=story_meta.get("model"),
        story_reason=story_meta.get("reason"),
        insights_source=insights_dict.get("source") if isinstance(insights_dict, dict) else None,
        insights_model=insights_dict.get("model") if isinstance(insights_dict, dict) else None,
        insights_reason=insights_dict.get("reason") if isinstance(insights_dict, dict) else None,
        created_at=entry.created_at
    )

@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a feedback entry."""
    entry = db.query(FeedbackEntry)\
        .filter(FeedbackEntry.id == feedback_id)\
        .filter(FeedbackEntry.user_id == current_user.id)\
        .first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    db.delete(entry)
    db.commit()
    logger.info(f"Feedback {feedback_id} deleted by user {current_user.username}")
    return None


@router.put("/{feedback_id}", response_model=FeedbackResponse)
def update_feedback(
    feedback_id: int,
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update feedback text and regenerate analysis."""
    entry = db.query(FeedbackEntry)\
        .filter(FeedbackEntry.id == feedback_id)\
        .filter(FeedbackEntry.user_id == current_user.id)\
        .first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Re-analyze content
    sentiment_result = analyze_sentiment(feedback.text)
    story_result = generate_story_with_retry(feedback.text)
    insights_result = generate_insights_with_retry(feedback.text)

    entry.text = feedback.text
    entry.sentiment = sentiment_result["sentiment"]
    entry.sentiment_label = sentiment_result["label"]
    entry.user_story = story_result["story"]
    entry.story_metadata = json.dumps(story_result)
    entry.insights = json.dumps(insights_result)
    db.commit()
    db.refresh(entry)

    logger.info(f"Feedback {feedback_id} updated by user {current_user.username}")

    return FeedbackResponse(
        id=entry.id,
        text=entry.text,
        sentiment=entry.sentiment,
        sentiment_label=entry.sentiment_label,
        user_story=entry.user_story,
        insights=insights_result,
        story_source=story_result.get("source"),
        story_model=story_result.get("model"),
        story_reason=story_result.get("reason"),
        insights_source=insights_result.get("source") if isinstance(insights_result, dict) else None,
        insights_model=insights_result.get("model") if isinstance(insights_result, dict) else None,
        insights_reason=insights_result.get("reason") if isinstance(insights_result, dict) else None,
        created_at=entry.created_at
    )


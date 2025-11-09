from textblob import TextBlob
from typing import Dict

def analyze_sentiment(text: str) -> Dict[str, any]:
    """Analyze sentiment of text using TextBlob."""
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    
    if sentiment > 0.1:
        label = "positive"
    elif sentiment < -0.1:
        label = "negative"
    else:
        label = "neutral"
    
    return {
        "sentiment": float(sentiment),
        "label": label
    }


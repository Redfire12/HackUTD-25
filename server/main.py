from fastapi import FastAPI
from database import insert_feedback
from pydantic import BaseModel
from textblob import TextBlob
import openai, os

app = FastAPI()

# load OpenAI key if provided (optional for now)
# openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------------
# Root check
# ------------------------------
@app.get("/")
def root():
    return {"text": "I love the new design but checkout is confusing."}


# ------------------------------
# Sentiment analysis endpoint
# ------------------------------
class Feedback(BaseModel):
    text: str

@app.post("/analyze")
def analyze_feedback(feedback: Feedback):
    sentiment = TextBlob(feedback.text).sentiment.polarity
    label = "positive" if sentiment > 0 else "negative" if sentiment < 0 else "neutral"
    return {"sentiment": sentiment, "label": label}  

# ------------------------------
# AI story generation endpoint
# ------------------------------
@app.post("/generate-story")
def generate_story(feedback: Feedback):
    prompt = f"Write a Jira-style user story and acceptance criteria for this feedback: {feedback.text}"

    # if no valid key, return a mock story instead of calling OpenAI
    if not openai.api_key or openai.api_key == "placeholder":
        return {
            "story": f"[mock story] As a user, I want to resolve: '{feedback.text}' so that customers are happier."
        }

    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {"story": completion.choices[0].message["content"]}  
@app.post("/ingest")
def ingest_feedback(feedback: dict):
    insert_feedback(feedback)
    return {"status": "success"}

# ------------------------------
# Mock insights for dashboard
# ------------------------------
@app.get("/insights/current")
def insights():
    return {
        "themes": [
            {"name": "Billing", "sentiment": -0.6, "count": 14},
            {"name": "Login", "sentiment": 0.4, "count": 9},
            {"name": "Performance", "sentiment": -0.1, "count": 6}
        ],
        "anomalies": ["Billing spike detected"],
        "timestamp": "2025-11-08T15:30:00Z"
    }

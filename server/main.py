from fastapi import FastAPI, Request
from pydantic import BaseModel
from textblob import TextBlob
from fastapi.middleware.cors import CORSMiddleware
import openai, os, logging
from datetime import datetime

# ------------------------------------------------
# app initialization
# ------------------------------------------------
app = FastAPI(title="HackUTD Backend", version="1.1.0")

# ------------------------------------------------
# enable CORS for frontend integration
# ------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins (safe for demo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# logging configuration
# ------------------------------------------------
LOG_FILE = "server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    logging.info(f"{request.method} {request.url.path} -> {response.status_code} [{process_time:.3f}s]")
    return response

# ------------------------------------------------
# load OpenAI key (optional for now)
# ------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------
# root route
# ------------------------------------------------
@app.get("/")
def root():
    logging.info("Root endpoint accessed")
    return {
        "status": "ok",
        "message": "Backend is running. Go to /docs to test endpoints."
    }

# ------------------------------------------------
# sentiment analysis endpoint
# ------------------------------------------------
class Feedback(BaseModel):
    text: str

@app.post("/analyze")
def analyze_feedback(feedback: Feedback):
    sentiment = TextBlob(feedback.text).sentiment.polarity
    label = "positive" if sentiment > 0 else "negative" if sentiment < 0 else "neutral"
    logging.info(f"/analyze: text='{feedback.text[:40]}...' | sentiment={sentiment} | label={label}")
    return {"sentiment": sentiment, "label": label}

# ------------------------------------------------
# AI story generation endpoint
# ------------------------------------------------
@app.post("/generate-story")
def generate_story(feedback: Feedback):
    prompt = f"Write a Jira-style user story and acceptance criteria for this feedback: {feedback.text}"

    # if no OpenAI key, return mock story
    if not openai.api_key or openai.api_key == "placeholder":
        story = f"[mock story] As a user, I want to resolve: '{feedback.text}' so that customers are happier."
        logging.info(f"/generate-story: mock story generated for text='{feedback.text[:40]}...'")
        return {"story": story}

    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    story = completion.choices[0].message["content"]
    logging.info(f"/generate-story: AI story generated for text='{feedback.text[:40]}...'")
    return {"story": story}

# ------------------------------------------------
# mock insights endpoint
# ------------------------------------------------
@app.get("/insights/current")
def insights():
    logging.info("/insights/current accessed")
    return {
        "themes": [
            {"name": "Billing", "sentiment": -0.6, "count": 14},
            {"name": "Login", "sentiment": 0.4, "count": 9},
            {"name": "Performance", "sentiment": -0.1, "count": 6}
        ],
        "anomalies": ["Billing spike detected"],
        "timestamp": "2025-11-08T15:30:00Z"
    }

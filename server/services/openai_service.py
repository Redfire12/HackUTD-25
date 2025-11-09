import os
import json
import re
import logging
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, AuthenticationError
from typing import Dict, Any, Optional
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Flags & configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
FORCE_FALLBACK = os.getenv("OPENAI_FORCE_FALLBACK", "").strip().lower() in ("1", "true", "yes", "on")

# Initialize OpenAI client if key is available and fallback not forced
client = None
if FORCE_FALLBACK:
    logger.warning("OPENAI_FORCE_FALLBACK is enabled. AI endpoints will use fallback data only.")
elif OPENAI_API_KEY and OPENAI_API_KEY not in ["", "placeholder", "your_openai_api_key_here"]:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        client = None
else:
    logger.warning("OpenAI API key not found or is placeholder. AI features will use fallbacks.")

def is_openai_available() -> bool:
    """Check if OpenAI API is available."""
    return client is not None and not FORCE_FALLBACK

def validate_openai_key() -> bool:
    """Validate OpenAI API key on startup."""
    if FORCE_FALLBACK:
        logger.info("Skipping OpenAI API key validation because OPENAI_FORCE_FALLBACK is enabled.")
        return False
    
    if not OPENAI_API_KEY or OPENAI_API_KEY in ["", "placeholder", "your_openai_api_key_here"]:
        logger.warning("OpenAI API key is missing or placeholder. AI features will use fallbacks.")
        return False
    
    if not client:
        logger.warning("OpenAI client not initialized. AI features will use fallbacks.")
        return False
    
    # Try a simple API call to validate the key
    try:
        # Quick validation call (uses minimal tokens)
        client.models.list()
        logger.info("OpenAI API key validated successfully")
        return True
    except AuthenticationError:
        logger.error("OpenAI API key is invalid or expired")
        return False
    except Exception as e:
        logger.warning(f"Could not validate OpenAI API key: {e}. Will attempt to use it anyway.")
        return True  # Return True to allow attempts, but log the warning

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text that might contain markdown code blocks."""
    if not text:
        return None
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Try to find JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Try parsing the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON from text: {text[:100]}")
        return None

def call_openai_with_fallback(
    messages: list,
    model_preferences: list = ["gpt-4o-mini", "gpt-3.5-turbo"],
    temperature: float = 0.7,
    max_retries: int = 3,
    use_json_mode: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Call OpenAI API with model fallback and retry logic.
    
    Args:
        messages: List of message dicts for the API
        model_preferences: List of models to try in order
        temperature: Temperature for the API call
        max_retries: Maximum number of retries per model
        use_json_mode: Whether to use JSON mode (if supported)
    
    Returns:
        Dict with 'content' and 'model' keys, or None if all attempts failed
    """
    if not is_openai_available():
        return None
    
    for model in model_preferences:
        for attempt in range(max_retries):
            try:
                # Prepare request parameters
                params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                
                # Add JSON mode if requested and supported
                # Note: JSON mode is available in gpt-4-turbo and newer models
                if use_json_mode and model in ["gpt-4o-mini", "gpt-4-turbo", "gpt-4"]:
                    params["response_format"] = {"type": "json_object"}
                
                completion = client.chat.completions.create(**params)
                
                content = completion.choices[0].message.content.strip()
                logger.info(f"OpenAI API call successful with model {model}")
                return {
                    "content": content,
                    "model": model
                }
            
            except RateLimitError as e:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit for {model}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limit exceeded for {model} after {max_retries} attempts")
                    break  # Try next model
            
            except AuthenticationError as e:
                logger.error(f"Authentication error with OpenAI API: {e}")
                return None  # Don't retry with other models if auth fails
            
            except APIError as e:
                error_message = str(e).lower()
                # Check for quota/billing errors
                if "quota" in error_message or "billing" in error_message or "insufficient" in error_message:
                    logger.error(f"OpenAI API quota/billing error: {e}")
                    return None  # Don't retry if quota is exceeded
                else:
                    logger.warning(f"OpenAI API error with {model}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        break  # Try next model
            
            except APIConnectionError as e:
                logger.warning(f"OpenAI API connection error with {model}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    break  # Try next model
            
            except Exception as e:
                logger.error(f"Unexpected error with OpenAI API ({model}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    break  # Try next model
    
    logger.error("All OpenAI API attempts failed")
    return None

def generate_story_with_retry(feedback_text: str) -> Dict[str, Any]:
    """Generate user story with retry logic and model fallback."""
    if not is_openai_available():
        return {
            "story": f"As a user, I want to address the feedback: '{feedback_text}' so that we can improve customer satisfaction.",
            "source": "fallback",
            "reason": "OpenAI API key not configured"
        }
    
    prompt = f"""Write a Jira-style user story and acceptance criteria based on this customer feedback:

"{feedback_text}"

Format your response as:
**User Story:**
As a [user type], I want [goal] so that [benefit].

**Acceptance Criteria:**
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

Keep it concise and actionable."""

    messages = [
        {
            "role": "system",
            "content": "You are a helpful product manager assistant that writes clear, actionable Jira-style user stories with acceptance criteria."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    result = call_openai_with_fallback(
        messages=messages,
        model_preferences=["gpt-4o-mini", "gpt-3.5-turbo"],
        temperature=0.7,
        max_retries=3,
        use_json_mode=False
    )
    
    if result:
        return {
            "story": result["content"],
            "source": "openai",
            "model": result["model"]
        }
    else:
        return {
            "story": f"As a user, I want to address the feedback: '{feedback_text}' so that we can improve customer satisfaction.",
            "source": "fallback",
            "reason": "OpenAI API request failed after all retries"
        }

def generate_insights_with_retry(feedback_text: str) -> Dict[str, Any]:
    """Generate insights with retry logic, model fallback, and structured JSON parsing."""
    if not is_openai_available():
        return {
            "themes": [
                {"name": "General Feedback", "sentiment": 0.0, "count": 1}
            ],
            "anomalies": [],
            "summary": "AI insights unavailable - using fallback data",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fallback",
            "reason": "OpenAI API key not configured"
        }
    
    insight_prompt = f"""Analyze the following customer feedback and extract structured insights.

Feedback: "{feedback_text}"

Return a valid JSON object with this exact structure:
{{
    "themes": [
        {{"name": "Theme Name", "sentiment": -1.0 to 1.0, "count": number}},
        ...
    ],
    "anomalies": ["anomaly1", "anomaly2", ...],
    "summary": "Brief summary of the feedback"
}}

Requirements:
- themes: Array of 3-5 key product themes with sentiment scores (-1.0 to 1.0) and count (integer)
- anomalies: Array of strings describing urgent issues or trends (can be empty)
- summary: A brief 1-2 sentence summary of the feedback
- Return ONLY valid JSON, no markdown, no additional text"""

    messages = [
        {
            "role": "system",
            "content": "You are an AI that analyzes customer feedback and returns structured JSON insights. Always return valid JSON only, no markdown or additional text. Ensure all numbers are proper JSON numbers (not strings)."
        },
        {
            "role": "user",
            "content": insight_prompt
        }
    ]
    
    # Try with JSON mode first (for supported models)
    result = call_openai_with_fallback(
        messages=messages,
        model_preferences=["gpt-4o-mini", "gpt-3.5-turbo"],
        temperature=0.5,
        max_retries=3,
        use_json_mode=True
    )
    
    if result:
        content = result["content"]
        insights_json = extract_json_from_text(content)
        
        if insights_json and isinstance(insights_json, dict):
            # Validate and clean the JSON
            if "themes" not in insights_json:
                insights_json["themes"] = []
            if "anomalies" not in insights_json:
                insights_json["anomalies"] = []
            if "summary" not in insights_json:
                insights_json["summary"] = "Analysis completed"
            
            # Ensure themes have required fields
            for theme in insights_json["themes"]:
                if "name" not in theme:
                    theme["name"] = "Unknown"
                if "sentiment" not in theme:
                    theme["sentiment"] = 0.0
                if "count" not in theme:
                    theme["count"] = 1
                # Ensure sentiment is a float
                try:
                    theme["sentiment"] = float(theme["sentiment"])
                except (ValueError, TypeError):
                    theme["sentiment"] = 0.0
                # Ensure count is an int
                try:
                    theme["count"] = int(theme["count"])
                except (ValueError, TypeError):
                    theme["count"] = 1
            
            insights_json["timestamp"] = datetime.utcnow().isoformat() + "Z"
            insights_json["source"] = "openai"
            insights_json["model"] = result["model"]
            
            logger.info("AI insights generated successfully")
            return insights_json
        else:
            logger.warning("Failed to parse JSON from OpenAI response")
    
    # Fallback if API call failed or JSON parsing failed
    return {
        "themes": [
            {"name": "General Feedback", "sentiment": 0.0, "count": 1}
        ],
        "anomalies": [],
        "summary": "AI insights unavailable - using fallback data",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "fallback",
        "reason": "OpenAI API request failed or JSON parsing failed"
    }

# Validate on import
validate_openai_key()

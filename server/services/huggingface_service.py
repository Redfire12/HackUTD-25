import os
import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time
from dotenv import load_dotenv
from pathlib import Path

# Try to import huggingface_hub (recommended) and requests (fallback)
try:
    from huggingface_hub import InferenceClient
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

# Always try to import requests as fallback (even if huggingface_hub is available)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

if not HF_HUB_AVAILABLE and not REQUESTS_AVAILABLE:
    logging.warning("Neither huggingface_hub nor requests available. Hugging Face API features will be disabled.")

# Load environment variables (try local server/.env first, fallback to defaults)
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path if dotenv_path.exists() else None)

logger = logging.getLogger(__name__)

# Flags & configuration
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
FORCE_FALLBACK = os.getenv("HUGGINGFACE_FORCE_FALLBACK", "").strip().lower() in ("1", "true", "yes", "on")
# Default model - google/flan-t5-base works for basic text generation
# For better results, consider using a model that requires an API key
# You can change this via HUGGINGFACE_MODEL env var
# Use a model that supports text-generation
# Mistral models require chat API, so we use google/flan-t5-base as default
# You can change this via HUGGINGFACE_MODEL env var
HF_MODEL = os.getenv("HUGGINGFACE_MODEL", "google/flan-t5-base").strip()

# Initialize Hugging Face client
is_available = False
client = None

if not HF_HUB_AVAILABLE and not REQUESTS_AVAILABLE:
    logger.warning("Neither huggingface_hub nor requests available. Hugging Face API features disabled.")
    is_available = False
elif FORCE_FALLBACK:
    logger.warning("HUGGINGFACE_FORCE_FALLBACK is enabled. AI endpoints will use fallback data only.")
    is_available = False
else:
    # Hugging Face Inference API can work without a key for public models
    # but having a key provides higher rate limits
    is_available = True
    if HF_HUB_AVAILABLE:
        # Use huggingface_hub library (recommended)
        try:
            # Check if we have a valid API key (not placeholder)
            has_valid_key = (
                HUGGINGFACE_API_KEY and 
                HUGGINGFACE_API_KEY not in ["", "placeholder", "your_huggingface_api_key_here"] and
                len(HUGGINGFACE_API_KEY) > 10 and
                not HUGGINGFACE_API_KEY.startswith("your_")
            )
            
            if has_valid_key:
                client = InferenceClient(token=HUGGINGFACE_API_KEY)
                logger.info(f"Hugging Face InferenceClient initialized with API key (key length: {len(HUGGINGFACE_API_KEY)})")
            else:
                client = InferenceClient()  # Works without key for public models
                logger.info("Hugging Face InferenceClient initialized without API key (using public models, may have rate limits)")
        except Exception as e:
            logger.warning(f"Failed to initialize Hugging Face InferenceClient: {e}")
            client = None
            is_available = False
    elif REQUESTS_AVAILABLE:
        # Fallback to requests library
        if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY not in ["", "placeholder", "your_huggingface_api_key_here"]:
            logger.info("Using requests library with Hugging Face API key.")
        else:
            logger.info("Using requests library without API key (may have rate limits).")

def is_huggingface_available() -> bool:
    """Check if Hugging Face API is available. Returns True if we can attempt API calls."""
    # Don't block if FORCE_FALLBACK is set
    if FORCE_FALLBACK:
        return False
    # Return True if we have the libraries, even if client initialization had issues
    # This allows retry attempts
    return (HF_HUB_AVAILABLE or REQUESTS_AVAILABLE)

def validate_huggingface_key() -> bool:
    """Validate Hugging Face API configuration on startup."""
    if not HF_HUB_AVAILABLE and not REQUESTS_AVAILABLE:
        logger.warning("Neither huggingface_hub nor requests available. Hugging Face API features disabled.")
        return False
    
    if FORCE_FALLBACK:
        logger.info("Skipping Hugging Face API validation because HUGGINGFACE_FORCE_FALLBACK is enabled.")
        return False
    
    if not is_available:
        logger.warning("Hugging Face API is not available. AI features will use fallbacks.")
        return False
    
    # Test API availability with a simple request (non-blocking, quick timeout)
    try:
        if HF_HUB_AVAILABLE and client:
            # Test with InferenceClient (don't block on validation)
            try:
                # Just check if client is initialized, don't make actual API call
                # Actual calls will be made when needed
                logger.info("Hugging Face InferenceClient initialized (using huggingface_hub)")
                return True
            except Exception as e:
                logger.warning(f"Hugging Face API test failed: {e}. Will attempt to use it anyway.")
                return True  # Allow attempts
        elif REQUESTS_AVAILABLE:
            # Fallback to requests (old method)
            headers = {}
            if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY not in ["", "placeholder", "your_huggingface_api_key_here"]:
                headers["Authorization"] = f"Bearer {HUGGINGFACE_API_KEY}"
            
            # Use the correct endpoint format
            test_url = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

            response = requests.post(
                test_url,
                headers=headers,
                json={"inputs": "test"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("Hugging Face API validated successfully (using requests)")
                return True
            elif response.status_code == 503:
                logger.warning("Hugging Face model is loading. It may take a moment to be ready.")
                return True
            else:
                logger.warning(f"Hugging Face API returned status {response.status_code}. Will attempt to use it anyway.")
                return True
    except Exception as e:
        logger.warning(f"Could not validate Hugging Face API: {e}. Will attempt to use it anyway.")
        return True  # Return True to allow attempts, but log the warning

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text that might contain markdown code blocks or extra text."""
    if not text:
        return None
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Remove common prefixes that models might add
    text = re.sub(r'^[^{]*', '', text)  # Remove everything before first {
    text = re.sub(r'[^}]*$', '', text)  # Remove everything after last }
    text = text.strip()
    
    # Try to find JSON object (more flexible matching)
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        try:
            parsed = json.loads(json_str)
            logger.info("Successfully extracted JSON from API response")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON match: {e}")
            # Try to fix common JSON issues
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
            json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # Try parsing the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON from text. First 200 chars: {text[:200]}")
        return None

def call_huggingface_with_fallback(
    prompt: str,
    max_retries: int = 3,
    max_length: int = 512
) -> Optional[Dict[str, Any]]:
    """
    Call Hugging Face Inference API with retry logic.
    
    Args:
        prompt: Input text prompt
        max_retries: Maximum number of retries
        max_length: Maximum length of generated text
    
    Returns:
        Dict with 'content' and 'model' keys, or None if all attempts failed
    """
    if not is_huggingface_available():
        return None
    
    # Reload API key from environment (in case it was updated)
    global HUGGINGFACE_API_KEY, client
    current_api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    if current_api_key and current_api_key != HUGGINGFACE_API_KEY:
        HUGGINGFACE_API_KEY = current_api_key
        logger.info("Reloaded Hugging Face API key from environment")
        client = None  # Force reinitialization
    
    # Use huggingface_hub InferenceClient (recommended)
    # But if it fails, fall back to requests library which is more reliable
    hf_hub_success = False
    if HF_HUB_AVAILABLE:
        # Reinitialize client if needed (in case API key was updated or not initialized)
        if not client:
            try:
                # Check if we have a valid API key (not placeholder)
                has_valid_key = (
                    HUGGINGFACE_API_KEY and 
                    HUGGINGFACE_API_KEY not in ["", "placeholder", "your_huggingface_api_key_here"] and
                    len(HUGGINGFACE_API_KEY) > 10 and
                    not HUGGINGFACE_API_KEY.startswith("your_")
                )
                
                if has_valid_key:
                    try:
                        client = InferenceClient(token=HUGGINGFACE_API_KEY)
                        logger.info(f"Hugging Face InferenceClient initialized with API key (key length: {len(HUGGINGFACE_API_KEY)})")
                    except Exception as e:
                        logger.warning(f"Failed to initialize with API key: {e}, trying without key")
                        client = InferenceClient()  # Try without key
                        logger.info("Hugging Face InferenceClient initialized without API key")
                else:
                    # Try without key for public models
                    client = InferenceClient()
                    logger.info("Hugging Face InferenceClient initialized without API key (using public models)")
            except Exception as e:
                logger.warning(f"Failed to initialize Hugging Face InferenceClient: {e}, will use requests library")
                client = None
        
        if client:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting Hugging Face API call (attempt {attempt + 1}/{max_retries}, model: {HF_MODEL})")
                    # Try the configured model first
                    try:
                        # text_generation may return a generator or string
                        result_gen = client.text_generation(
                            prompt,
                            model=HF_MODEL,
                            max_new_tokens=max_length,
                            temperature=0.7
                        )
                        # Handle different return types
                        if isinstance(result_gen, str):
                            result = result_gen
                        elif hasattr(result_gen, '__iter__'):
                            try:
                                result = ''.join(result_gen)
                            except (StopIteration, TypeError):
                                # If generator is empty or fails, try to get string representation
                                result = str(result_gen) if result_gen else ''
                        else:
                            result = str(result_gen) if result_gen else ''
                        
                        if result and len(result.strip()) > 0:
                            logger.info(f"✅ Hugging Face API call successful (using huggingface_hub, attempt {attempt + 1}, response length: {len(result)})")
                            hf_hub_success = True
                            return {
                                "content": result.strip(),
                                "model": HF_MODEL
                            }
                        else:
                            raise ValueError("Empty response from API")
                    except (StopIteration, ValueError, TypeError) as model_error:
                        # If model fails, try fallback model
                        error_str = str(model_error).lower()
                        if "mistral" in HF_MODEL.lower() or "not supported" in error_str or "conversational" in error_str or "empty" in error_str:
                            logger.warning(f"Model {HF_MODEL} failed ({model_error}), trying fallback model: google/flan-t5-base")
                            try:
                                result_gen = client.text_generation(
                                    prompt,
                                    model="google/flan-t5-base",
                                    max_new_tokens=max_length,
                                    temperature=0.7
                                )
                                if isinstance(result_gen, str):
                                    result = result_gen
                                elif hasattr(result_gen, '__iter__'):
                                    result = ''.join(result_gen)
                                else:
                                    result = str(result_gen)
                                
                                if result and len(result.strip()) > 0:
                                    logger.info("✅ Using fallback model: google/flan-t5-base")
                                    hf_hub_success = True
                                    return {
                                        "content": result.strip(),
                                        "model": "google/flan-t5-base"
                                    }
                                else:
                                    raise ValueError("Empty response from fallback model")
                            except Exception as fallback_error:
                                logger.warning(f"Fallback model also failed: {fallback_error}")
                                # Don't raise, let it fall through to requests library
                        else:
                            raise
                except Exception as e:
                    error_str = str(e).lower()
                    if "503" in error_str or "loading" in error_str:
                        wait_time = (2 ** attempt) * 5
                        if attempt < max_retries - 1:
                            logger.warning(f"Model is loading, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            logger.warning("Model is still loading after all retries, trying requests library")
                            break
                    elif "429" in error_str or "rate limit" in error_str:
                        wait_time = (2 ** attempt) * 2
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            logger.warning("Rate limit exceeded, trying requests library")
                            break
                    elif "403" in error_str or "permission" in error_str:
                        logger.warning(f"Permission error (403), trying requests library without API key")
                        break  # Skip to requests library, try without key
                    else:
                        logger.warning(f"Hugging Face InferenceClient error: {type(e).__name__}: {str(e)[:200]}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                        else:
                            logger.warning("All InferenceClient attempts failed, trying requests library")
                            break
    
    # Fallback to requests library (more reliable for public access)
    if not hf_hub_success and REQUESTS_AVAILABLE:
        # Reload API key from environment
        current_api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
        
        # Try without API key first (public access, more reliable)
        # Only use API key if public access fails
        headers_list = []
        has_valid_key = (
            current_api_key and 
            current_api_key not in ["", "placeholder", "your_huggingface_api_key_here"] and
            len(current_api_key) > 10 and
            not current_api_key.startswith("your_")
        )
        
        # Try without key first, then with key if needed
        if has_valid_key:
            headers_list.append({"Authorization": f"Bearer {current_api_key}"})
        headers_list.append({})  # Try without key as fallback
        
        # Try multiple endpoints - some may work without special permissions
        # The router endpoint requires Inference Provider permissions
        # Try alternative endpoints that might work
        api_urls = [
            # Try the inference API endpoint (may work for some models)
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            # Router endpoint (requires permissions but try anyway)
            f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
        ]
        
        for api_url in api_urls:
            for headers in headers_list:
                logger.info(f"Using requests library with {'API key' if headers.get('Authorization') else 'public access'} to {api_url}")

                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            api_url,
                            headers=headers,
                            json={
                                "inputs": prompt,
                                "parameters": {
                                    "max_length": max_length,
                                    "temperature": 0.7,
                                    "do_sample": True,
                                }
                            },
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            # Parse response format
                            if isinstance(result, list) and len(result) > 0:
                                if isinstance(result[0], dict):
                                    content = result[0].get("generated_text", result[0].get("text", ""))
                                else:
                                    content = str(result[0])
                            elif isinstance(result, dict):
                                content = result.get("generated_text", result.get("text", str(result)))
                            else:
                                content = str(result)
                            
                            if content and len(content.strip()) > 0:
                                logger.info(f"✅ Hugging Face API call successful (using requests, {api_url})")
                                return {
                                    "content": content.strip(),
                                    "model": HF_MODEL
                                }
                            else:
                                logger.warning("Empty response content, trying next endpoint/key combination")
                                break  # Try next headers/URL
                        
                        elif response.status_code == 410:
                            # Endpoint deprecated, try next URL
                            logger.warning(f"Endpoint {api_url} is deprecated (410), trying next endpoint")
                            break  # Try next URL
                        
                        elif response.status_code == 401:
                            # Unauthorized - try with API key if we're not using one, or try next endpoint
                            if not headers.get('Authorization'):
                                logger.warning("Unauthorized (401) without API key, will try with API key")
                                break  # Try with API key
                            else:
                                logger.warning("Unauthorized (401) even with API key, trying next endpoint")
                                break  # Try next URL
                        
                        elif response.status_code == 503:
                            wait_time = (2 ** attempt) * 5
                            if attempt < max_retries - 1:
                                logger.warning(f"Model is loading, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                break  # Try next headers/URL
                        
                        elif response.status_code == 429:
                            wait_time = (2 ** attempt) * 2
                            if attempt < max_retries - 1:
                                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                break  # Try next headers/URL
                        
                        elif response.status_code == 403:
                            logger.warning(f"Permission denied (403) with {'API key' if headers.get('Authorization') else 'public access'}, trying next option")
                            break  # Try next headers/URL
                        
                        else:
                            logger.warning(f"Hugging Face API error: {response.status_code} - {response.text[:200]}")
                            if attempt < max_retries - 1:
                                time.sleep(2 ** attempt)
                            else:
                                break  # Try next headers/URL
                    
                    except requests.exceptions.Timeout:
                        logger.warning(f"Hugging Face API timeout (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                        else:
                            break  # Try next headers/URL
                    
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Hugging Face API connection error: {e}, trying next option")
                        break  # Try next headers/URL
                    
                    except Exception as e:
                        logger.warning(f"Unexpected error with Hugging Face API: {e}, trying next option")
                        break  # Try next headers/URL
    
    # If all API attempts failed, try one more time with a simpler model and request
    if REQUESTS_AVAILABLE:
        logger.info("All standard methods failed, trying simplified approach...")
        try:
            # Try with a very simple model that might work
            simple_url = "https://api-inference.huggingface.co/models/gpt2"
            response = requests.post(
                simple_url,
                json={"inputs": prompt[:100]},  # Truncate prompt for simpler models
                timeout=15
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    content = result[0].get("generated_text", "")
                    if content:
                        logger.info("✅ Simplified API call successful")
                        return {
                            "content": content.strip(),
                            "model": "gpt2"
                        }
        except Exception as e:
            logger.debug(f"Simplified approach also failed: {e}")
    
    logger.error("All Hugging Face API attempts failed")
    return None

def generate_story_with_retry(feedback_text: str) -> Dict[str, Any]:
    """Generate user story with retry logic. Uses real Hugging Face API, only falls back if absolutely necessary."""
    # Check if we should use API - be more lenient, allow attempts even if not perfectly configured
    if FORCE_FALLBACK:
        logger.warning("FORCE_FALLBACK is enabled - using fallback data for user story")
        return {
            "story": f"As a user, I want to address the feedback: '{feedback_text}' so that we can improve customer satisfaction.",
            "source": "fallback",
            "reason": "HUGGINGFACE_FORCE_FALLBACK is enabled"
        }
    
    # Try to use API even if not perfectly configured (might work without key for public models)
    if not HF_HUB_AVAILABLE and not REQUESTS_AVAILABLE:
        logger.error("Neither huggingface_hub nor requests available - cannot use Hugging Face API")
        return {
            "story": f"As a user, I want to address the feedback: '{feedback_text}' so that we can improve customer satisfaction.",
            "source": "fallback",
            "reason": "Required libraries not installed"
        }
    
    prompt = f"""Task: Convert customer feedback into a detailed user story with acceptance criteria.

Customer Feedback: "{feedback_text}"

Instructions:
1. Identify the user persona (who is giving this feedback)
2. Extract the core need or goal
3. Determine the business value or benefit
4. Create specific, testable acceptance criteria

Format your response EXACTLY as follows:

**User Story:**
As a [specific user type/persona], I want [specific feature/functionality/goal] so that [clear business value/benefit].

**Acceptance Criteria:**
1. [Specific, testable criterion related to the feedback]
2. [Another specific, testable criterion]
3. [Third specific, testable criterion]

**Context:**
[Brief explanation of why this story addresses the customer feedback]

Make it detailed, specific, and actionable. Base everything on the actual customer feedback provided."""
    
    # Increase retries and be more aggressive about using the API
    logger.info("Attempting to generate user story using Hugging Face API...")
    result = call_huggingface_with_fallback(
        prompt=prompt,
        max_retries=5,  # Increased from 3 to 5
        max_length=1024  # Increased for more detailed responses
    )
    
    if result and result.get("content"):
        logger.info(f"Successfully generated user story using Hugging Face API (model: {result.get('model', 'unknown')})")
        return {
            "story": result["content"],
            "source": "huggingface",
            "model": result["model"]
        }
    else:
        # Only use fallback if all API attempts truly failed
        logger.error("All Hugging Face API attempts failed - using enhanced fallback data")
    
    # Generate better fallback story based on feedback content
    feedback_lower = feedback_text.lower()
    user_type = "customer"
    goal = "improve the product"
    benefit = "enhance user experience"
    
    # Extract key themes from feedback for better fallback
    if "crash" in feedback_lower or "error" in feedback_lower or "bug" in feedback_lower:
        goal = "fix stability issues"
        benefit = "ensure reliable app performance"
    elif "slow" in feedback_lower or "performance" in feedback_lower:
        goal = "optimize performance"
        benefit = "provide faster response times"
    elif "feature" in feedback_lower or "add" in feedback_lower or "need" in feedback_lower:
        goal = "add requested features"
        benefit = "meet user needs and expectations"
    elif "ui" in feedback_lower or "interface" in feedback_lower or "design" in feedback_lower:
        goal = "improve user interface"
        benefit = "create a more intuitive user experience"
    
    fallback_story = f"""**User Story:**
As a {user_type}, I want {goal} so that {benefit}.

**Acceptance Criteria:**
1. The system addresses the core issue mentioned in the feedback
2. Changes are tested and verified before deployment
3. User experience is improved based on the feedback provided

**Context:**
This story addresses the customer feedback: "{feedback_text[:100]}{'...' if len(feedback_text) > 100 else ''}"
"""
    
    return {
        "story": fallback_story,
        "source": "fallback",
        "reason": "Hugging Face API unavailable. Please ensure your API key has 'Write' permissions at https://huggingface.co/settings/tokens"
    }

def generate_insights_with_retry(feedback_text: str) -> Dict[str, Any]:
    """Generate insights with retry logic and structured JSON parsing. Uses real Hugging Face API, only falls back if absolutely necessary."""
    # Check if we should use API - be more lenient, allow attempts even if not perfectly configured
    if FORCE_FALLBACK:
        logger.warning("FORCE_FALLBACK is enabled - using fallback data for insights")
        return {
            "themes": [
                {"name": "General Feedback", "sentiment": 0.0, "count": 1}
            ],
            "anomalies": [],
            "summary": "AI insights unavailable - using fallback data",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fallback",
            "reason": "HUGGINGFACE_FORCE_FALLBACK is enabled"
        }
    
    # Try to use API even if not perfectly configured (might work without key for public models)
    if not HF_HUB_AVAILABLE and not REQUESTS_AVAILABLE:
        logger.error("Neither huggingface_hub nor requests available - cannot use Hugging Face API")
        return {
            "themes": [
                {"name": "General Feedback", "sentiment": 0.0, "count": 1}
            ],
            "anomalies": [],
            "summary": "AI insights unavailable - using fallback data",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fallback",
            "reason": "Required libraries not installed"
        }
    
    insight_prompt = f"""Analyze this customer feedback and extract detailed insights in JSON format.

Customer Feedback: "{feedback_text}"

Task: Extract themes, sentiment, anomalies, and create a summary.

Return a valid JSON object with this EXACT structure (no markdown, no code blocks, just JSON):
{{
    "themes": [
        {{"name": "Theme Name (e.g., User Interface, Performance, Features)", "sentiment": -1.0, "count": 1}},
        {{"name": "Another Theme", "sentiment": 0.5, "count": 1}},
        {{"name": "Third Theme", "sentiment": 0.0, "count": 1}}
    ],
    "anomalies": ["Specific issue or concern mentioned", "Another concern if any"],
    "summary": "A comprehensive 2-3 sentence summary analyzing the feedback, key themes, sentiment, and actionable insights"
}}

Requirements:
- themes: Extract 3-5 distinct themes/topics from the feedback
  - sentiment: -1.0 (very negative) to 1.0 (very positive), 0.0 (neutral)
  - count: Number of times this theme appears (usually 1 for single feedback)
  - name: Specific theme name based on the feedback content
- anomalies: List any urgent issues, bugs, or critical concerns mentioned (can be empty array if none)
- summary: Detailed analysis including overall sentiment, main themes, and key takeaways
- Return ONLY valid JSON, no markdown formatting, no code blocks, no explanatory text

Example for feedback "The app crashes when I try to upload files":
{{
    "themes": [
        {{"name": "Stability & Reliability", "sentiment": -1.0, "count": 1}},
        {{"name": "File Upload Feature", "sentiment": -1.0, "count": 1}},
        {{"name": "User Experience", "sentiment": -0.5, "count": 1}}
    ],
    "anomalies": ["App crashes during file upload"],
    "summary": "Critical stability issue reported: the app crashes when users attempt to upload files. This indicates a serious bug in the file upload functionality that significantly impacts user experience and app reliability. Immediate investigation and fix required."
}}"""
    
    # Increase retries and be more aggressive about using the API
    logger.info("Attempting to generate insights using Hugging Face API...")
    result = call_huggingface_with_fallback(
        prompt=insight_prompt,
        max_retries=5,  # Increased from 3 to 5
        max_length=1024  # Increased for better JSON responses
    )
    
    if result and result.get("content"):
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
            insights_json["source"] = "huggingface"
            insights_json["model"] = result["model"]
            
            logger.info(f"Successfully generated insights using Hugging Face API (model: {result.get('model', 'unknown')})")
            return insights_json
        else:
            logger.warning("Failed to parse JSON from Hugging Face response - retrying with raw content")
            # Try to use raw content even if JSON parsing failed
            if content and len(content.strip()) > 10:
                return {
                    "themes": [
                        {"name": "Feedback Analysis", "sentiment": 0.0, "count": 1}
                    ],
                    "anomalies": [],
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "huggingface",
                    "model": result["model"],
                    "reason": "JSON parsing failed but using raw API response"
                }
    
    # Only use fallback if all API attempts truly failed
    logger.error("All Hugging Face API attempts failed - using enhanced fallback data")
    
    # Generate better fallback insights based on feedback content
    feedback_lower = feedback_text.lower()
    themes = []
    anomalies = []
    sentiment_score = 0.0
    
    # Analyze feedback for themes
    if "crash" in feedback_lower or "error" in feedback_lower or "bug" in feedback_lower:
        themes.append({"name": "Stability & Reliability", "sentiment": -0.8, "count": 1})
        anomalies.append("Critical stability issues reported")
        sentiment_score = -0.7
    if "slow" in feedback_lower or "performance" in feedback_lower or "lag" in feedback_lower:
        themes.append({"name": "Performance", "sentiment": -0.6, "count": 1})
        sentiment_score = min(sentiment_score, -0.5)
    if "ui" in feedback_lower or "interface" in feedback_lower or "design" in feedback_lower or "layout" in feedback_lower:
        themes.append({"name": "User Interface", "sentiment": -0.4, "count": 1})
    if "feature" in feedback_lower or "add" in feedback_lower or "missing" in feedback_lower:
        themes.append({"name": "Feature Requests", "sentiment": 0.0, "count": 1})
    if "great" in feedback_lower or "love" in feedback_lower or "excellent" in feedback_lower or "good" in feedback_lower:
        themes.append({"name": "Positive Feedback", "sentiment": 0.7, "count": 1})
        sentiment_score = 0.6
    
    # Default theme if none found
    if not themes:
        themes.append({"name": "General Feedback", "sentiment": sentiment_score, "count": 1})
    
    # Generate summary
    if anomalies:
        summary = f"Critical issues identified: {', '.join(anomalies)}. " + \
                 f"Key themes include {', '.join([t['name'] for t in themes[:3]])}. " + \
                 "Immediate attention required for stability concerns."
    else:
        summary = f"Feedback analysis identifies {len(themes)} key theme(s): {', '.join([t['name'] for t in themes])}. " + \
                 "Overall sentiment indicates areas for improvement."
    
    return {
        "themes": themes,
        "anomalies": anomalies,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "fallback",
        "reason": "Hugging Face API unavailable. Please ensure your API key has 'Write' permissions at https://huggingface.co/settings/tokens"
    }

# Note: Validation is called from main.py during startup, not at module import time
# This prevents blocking server startup if the API is slow or unavailable


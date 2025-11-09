#!/usr/bin/env python3
"""Script to check if Hugging Face API key is configured correctly."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
force_fallback = os.getenv("HUGGINGFACE_FORCE_FALLBACK", "").strip().lower() in ("1", "true", "yes", "on")

print("=" * 60)
print("Hugging Face API Key Configuration Check")
print("=" * 60)
print()

# Check API key
print(f"API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key length: {len(api_key)}")
    print(f"API Key starts with 'hf_': {api_key.startswith('hf_')}")
    print(f"API Key preview: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    
    # Check if it's a placeholder
    is_placeholder = (
        api_key.lower() in ["", "placeholder", "your_huggingface_api_key_here"] or
        len(api_key) < 10 or
        api_key.startswith("your_")
    )
    
    if is_placeholder:
        print("⚠️  WARNING: API key appears to be a placeholder!")
        print("   Please replace it with your actual Hugging Face API key.")
    else:
        print("✅ API key looks valid!")
else:
    print("⚠️  WARNING: No API key found!")

print()
print(f"FORCE_FALLBACK: {force_fallback}")
if force_fallback:
    print("⚠️  WARNING: FORCE_FALLBACK is enabled - API will not be used!")
else:
    print("✅ FORCE_FALLBACK is disabled - API will be used")

print()
print("=" * 60)
print("Next Steps:")
print("=" * 60)
if not api_key or is_placeholder:
    print("1. Get your API key from: https://huggingface.co/settings/tokens")
    print("2. Add it to server/.env: HUGGINGFACE_API_KEY=hf_your_key_here")
    print("3. Restart the backend server")
else:
    print("1. API key is configured ✅")
    print("2. Make sure backend server is restarted after adding the key")
    print("3. Test by submitting feedback in the frontend")
    print("4. Check backend logs for: '✅ Hugging Face API call successful'")
print()


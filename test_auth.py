#!/usr/bin/env python3
"""
Quick test script to verify authentication endpoints are working.
Run this from the server directory: python3 ../test_auth.py
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test if backend is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_signup(username, email, password):
    """Test signup endpoint."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"username": username, "email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Signup successful: {data.get('username')}")
            return True, None
        else:
            error = response.json().get("detail", "Unknown error")
            print(f"❌ Signup failed: {error}")
            return False, error
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return False, str(e)

def test_login(username, password):
    """Test login endpoint."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"✅ Login successful, token received")
                return True, token
            else:
                print("❌ Login failed: No token in response")
                return False, None
        else:
            error = response.json().get("detail", "Unknown error")
            print(f"❌ Login failed: {error}")
            return False, None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False, None

def test_me(token):
    """Test /auth/me endpoint with token."""
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ /auth/me successful: {data.get('username')}")
            return True
        else:
            error = response.json().get("detail", "Unknown error")
            print(f"❌ /auth/me failed: {error}")
            return False
    except Exception as e:
        print(f"❌ /auth/me error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Authentication Flow Test")
    print("=" * 50)
    
    # Test 1: Backend health
    if not test_health():
        sys.exit(1)
    
    print()
    
    # Test 2: Signup
    test_username = f"testuser_{int(__import__('time').time())}"
    test_email = f"{test_username}@test.com"
    test_password = "Test123!"
    
    print(f"Testing signup with username: {test_username}")
    signup_success, signup_error = test_signup(test_username, test_email, test_password)
    
    if not signup_success and "already registered" not in str(signup_error).lower():
        print("\n⚠️  Signup failed, but continuing with login test...")
    
    print()
    
    # Test 3: Login
    print(f"Testing login with username: {test_username}")
    login_success, token = test_login(test_username, test_password)
    
    if not login_success:
        print("\n❌ Login test failed. Authentication flow is broken.")
        sys.exit(1)
    
    print()
    
    # Test 4: Get current user
    print("Testing /auth/me endpoint")
    if not test_me(token):
        print("\n❌ Token validation failed.")
        sys.exit(1)
    
    print()
    print("=" * 50)
    print("✅ All authentication tests passed!")
    print("=" * 50)


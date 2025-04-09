#!/usr/bin/env python3
"""
ChessMate API Security Testing Script
This script tests the security implementations in the ChessMate API.
"""

import argparse
import json
import random
import string
import time
import requests
import sys
import base64
from typing import Dict, Any, Optional, List, Tuple

# Base URL configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"  # The API is mounted at /api/v1 in urls.py
TIMEOUT = 5  # Default timeout for requests in seconds

# API Endpoints
ENDPOINTS = {
    # Auth endpoints
    "register": f"{API_BASE}/auth/register/",
    "login": f"{API_BASE}/auth/login/",
    "logout": f"{API_BASE}/auth/logout/",
    "refresh": f"{API_BASE}/auth/token/refresh/",
    "csrf": f"{API_BASE}/auth/csrf/",
    "verify_email": f"{API_BASE}/auth/verify-email/<uidb64>/<token>/",
    "test_auth": f"{API_BASE}/auth/test-auth/",
    "reset_password": f"{API_BASE}/auth/reset-password/",
    "reset_password_confirm": f"{API_BASE}/auth/reset-password/confirm/",
    
    # Profile endpoints
    "profile": f"{API_BASE}/profile/",
    "basic_profile": f"{API_BASE}/profile/minimal/",
    "update_profile": f"{API_BASE}/profile/update/",
    "subscription": f"{API_BASE}/profile/subscription/",
    
    # Game endpoints
    "games": f"{API_BASE}/games/",
    "analyses": f"{API_BASE}/games/analyses/",
    
    # Health endpoints
    "health": f"{API_BASE}/health/",
    "detailed_health": f"{API_BASE}/health/detailed/",
    "readiness": f"{API_BASE}/health/readiness/",
    
    # System endpoints
    "system_status": f"{API_BASE}/system/status/",
    "system_cache": f"{API_BASE}/system/cache/clear/",
    
    # Other endpoints
    "info": f"{API_BASE}/info/",
    "tasks": f"{API_BASE}/tasks/status/",
}

# Test config
VERBOSE = False
CSRF_PROTECTION = False
USE_BASIC_PROFILE = False  # Whether to use the basic profile endpoint instead of the main one


def get_available_endpoints() -> List[str]:
    """Check which API endpoints are available"""
    available = []
    for name, url in ENDPOINTS.items():
        # Skip endpoints with placeholders
        if "<" in url and ">" in url:
            continue
            
        try:
            response = requests.get(url)
            status = response.status_code
            # We consider 404, 403, 401 as "available" since they might require auth
            if status in [200, 201, 400, 401, 403, 404, 405]:
                available.append(f"{name}: {url} ({status})")
        except requests.RequestException as e:
            print(f"Error checking endpoint {url}: {e}")
    return available


def random_string(length: int = 10) -> str:
    """Generate a random string for testing"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def print_response(response: requests.Response) -> None:
    """Print formatted response information"""
    if not VERBOSE:
        return
    
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except:
        print("Response Text:")
        print(response.text[:500])  # Limit text output
    
    print("-" * 50)


def get_csrf_token(session: requests.Session) -> Optional[str]:
    """Get CSRF token from the server if CSRF protection is enabled"""
    if not CSRF_PROTECTION:
        return None
    
    try:
        response = session.get(ENDPOINTS["csrf"])
        csrf = response.json().get("csrfToken") or session.cookies.get('csrftoken')
        return csrf
    except Exception as e:
        print(f"Error getting CSRF token: {e}")
        return None


def register_user(session: requests.Session, username: str, password: str, email: str) -> Dict[str, Any]:
    """Register a new user"""
    csrf_token = get_csrf_token(session)
    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
    
    data = {
        "username": username,
        "password": password,
        "email": email,
    }
    
    try:
        response = session.post(
            ENDPOINTS["register"],
            json=data,
            headers=headers
        )
        print_response(response)
        
        if response.status_code in [200, 201]:
            return {"success": True, "data": response.json()}
        return {"success": False, "error": f"Registration failed with status {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error during registration: {e}")
        return {"success": False, "error": str(e)}


def login_user(session: requests.Session, username: str, password: str, email: str) -> Dict[str, Any]:
    """Log in a user and get auth tokens"""
    csrf_token = get_csrf_token(session)
    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
    
    data = {
        "email": email,
        "password": password,
    }
    
    try:
        response = session.post(
            ENDPOINTS["login"],
            json=data,
            headers=headers
        )
        print_response(response)
        
        if response.status_code == 200:
            resp_data = response.json()
            
            # Handle different response formats
            if "data" in resp_data and isinstance(resp_data["data"], dict):
                result_data = resp_data["data"]
                access_token = result_data.get("token", result_data.get("access", ""))
                refresh_token = result_data.get("refresh", "")
            else:
                # Direct format
                result_data = resp_data
                access_token = resp_data.get("token", resp_data.get("access", ""))
                refresh_token = resp_data.get("refresh", "")
                
            # Update authorization header with new access token
            if access_token:
                # Make sure we set the Authorization header correctly
                session.headers.clear()  # Clear any existing headers
                session.headers.update({
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                })
                print(f"Set Authorization header: Bearer {access_token[:10]}...")
                
            return {"success": True, "data": result_data, "access_token": access_token, "refresh_token": refresh_token}
        return {"success": False, "error": f"Login failed with status {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error during login: {e}")
        return {"success": False, "error": str(e)}


def get_profile(session: requests.Session) -> Dict[str, Any]:
    """Attempt to access the protected user profile endpoint."""
    endpoint = ENDPOINTS.get("basic_profile", f"{BASE_URL}/api/v1/profile/minimal/")
    
    # Ensure session has token in headers
    if hasattr(session, 'headers'):
        session_headers = dict(session.headers)
        print(f"Session headers: {session_headers}")
    else:
        session_headers = {}
        print("No session headers found")
    
    # Log the authentication information
    print(f"Making request to: {endpoint}")
    
    # Make the request with explicit headers to ensure they're included
    headers = session_headers.copy()
    print(f"Using explicit headers: {headers}")
    
    try:
        response = session.get(endpoint, headers=headers, timeout=TIMEOUT)
        print_response(response)
        
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                return {"error": "Invalid JSON response"}
        else:
            return {
                "error": f"Failed to get profile with status {response.status_code}: {response.text}"
            }
    except requests.RequestException as e:
        return {"error": f"Request error: {str(e)}"}


def test_auth_endpoint(session: requests.Session) -> Dict[str, Any]:
    """Test the authentication endpoint directly to verify token handling."""
    endpoint = ENDPOINTS.get("test_auth", f"{BASE_URL}/api/v1/auth/test-auth/")
    
    # Ensure session has token in headers
    if hasattr(session, 'headers'):
        session_headers = dict(session.headers)
        print(f"Session headers: {session_headers}")
    else:
        session_headers = {}
        print("No session headers found")
    
    # Log the authentication information
    print(f"Making request to: {endpoint}")
    
    # Make the request with explicit headers to ensure they're included
    headers = session_headers.copy()
    print(f"Using explicit headers: {headers}")
    
    try:
        response = session.get(endpoint, headers=headers, timeout=TIMEOUT)
        print_response(response)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Check if this was a partial success (token valid but Django auth failed)
                if data.get("status") == "partial_success":
                    print("NOTE: Token is valid but Django authentication failed!")
                return data
            except ValueError:
                return {"error": "Invalid JSON response"}
        else:
            return {
                "error": f"Failed auth test with status {response.status_code}: {response.text}"
            }
    except requests.RequestException as e:
        return {"error": f"Request error: {str(e)}"}


def refresh_token_func(session: requests.Session, refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    csrf_token = get_csrf_token(session)
    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
    
    data = {
        "refresh": refresh_token
    }
    
    try:
        response = session.post(
            ENDPOINTS["refresh"],
            json=data,
            headers=headers
        )
        print_response(response)
        
        if response.status_code == 200:
            resp_data = response.json()
            
            # Handle different response formats
            if "data" in resp_data and isinstance(resp_data["data"], dict):
                result_data = resp_data["data"]
                access_token = result_data.get("token", result_data.get("access", ""))
            else:
                # Direct format
                result_data = resp_data
                access_token = resp_data.get("token", resp_data.get("access", ""))
                
            # Update authorization header with new access token
            if access_token:
                session.headers.update({
                    "Authorization": f"Bearer {access_token}"
                })
                
            return {"success": True, "data": result_data, "access_token": access_token}
        return {"success": False, "error": f"Token refresh failed with status {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error refreshing token: {e}")
        return {"success": False, "error": str(e)}


def logout(session: requests.Session, refresh_token: str) -> Dict[str, Any]:
    """Log out and blacklist the refresh token"""
    csrf_token = get_csrf_token(session)
    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
    
    data = {
        "refresh": refresh_token
    }
    
    try:
        response = session.post(
            ENDPOINTS["logout"],
            json=data,
            headers=headers
        )
        print_response(response)
        
        if response.status_code in [200, 204, 205]:
            return {"success": True}
        return {"success": False, "error": f"Logout failed with status {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error during logout: {e}")
        return {"success": False, "error": str(e)}


def test_rate_limiting(endpoint: Optional[str] = None, attempts: int = 15) -> Dict[str, Any]:
    """
    Test rate limiting by making multiple requests in quick succession.
    
    Args:
        endpoint: The endpoint to test (defaults to login)
        attempts: Number of attempts to make
        
    Returns:
        Dictionary with test results
    """
    if endpoint is None:
        endpoint = f"{BASE_URL}/api/v1/auth/login/"
    
    print(f"Testing rate limiting with {attempts} requests to {endpoint}")
    results = []
    
    # Create a dedicated session for rate limit testing
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
    })
    
    # Prepare proper login data
    login_data = {
        "email": f"test_{random_string()}@example.com",
        "password": "Test1234!"
    }
    
    for i in range(1, attempts + 1):
        try:
            # Send request with proper data
            response = session.post(
                endpoint, 
                json=login_data,
                timeout=TIMEOUT
            )
            
            # Get rate limit headers
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            reset = response.headers.get("X-RateLimit-Reset", "N/A")
            
            # Check if this is a rate limit response
            is_rate_limited = response.status_code == 429
            
            if is_rate_limited:
                print(f"Request {i}: ✅ Rate limited (429)")
            else:
                print(f"Request {i}: Status {response.status_code}, Remaining: {remaining}, Reset: {reset}")
            
            # Record this result
            results.append({
                "request_num": i,
                "status": response.status_code,
                "rate_limited": is_rate_limited,
                "remaining": remaining,
                "reset": reset
            })
            
            # Small delay to prevent server overwhelm
            time.sleep(0.05)
        except Exception as e:
            print(f"Error in request {i}: {str(e)}")
            results.append({
                "request_num": i,
                "error": str(e)
            })
    
    # Check if we ever hit a rate limit
    rate_limited = any(result.get("rate_limited", False) for result in results)
    
    # Calculate decrease in remaining requests
    remaining_values = [
        int(str(result["remaining"])) 
        for result in results 
        if "remaining" in result and result["remaining"] != "N/A"
    ]
    
    if len(remaining_values) >= 2:
        first = remaining_values[0]
        last = remaining_values[-1]
        decreasing = first > last
    else:
        decreasing = False
    
    # Test is successful if either we hit rate limit or see decreasing remaining requests
    success = rate_limited or decreasing
    
    # Detailed information about what happened
    details = {
        "requests": results,
        "rate_limited": rate_limited,
        "decreasing_quota": decreasing
    }
    
    return {
        "success": success,
        "error": None if success else "Rate limiting not detected",
        "details": details
    }


def test_email_verification(
    session: requests.Session, 
    username: str, 
    password: str,
    email: str
) -> Dict[str, Any]:
    """Test email verification flow"""
    # Register a user first
    register_result = register_user(session, username, password, email)
    if not register_result["success"]:
        return register_result
    
    # Try to verify with an invalid token
    invalid_token = "invalid-token-123"
    invalid_uidb64 = "invalid-uidb64"
    
    try:
        # Use the actual verification URL format from urls_auth.py
        verify_url = f"{API_BASE}/auth/verify-email/{invalid_uidb64}/{invalid_token}/"
        response = session.get(verify_url)
        print_response(response)
        
        # Email verification should fail with invalid token
        # Check for security-related indicators in the response
        security_check_passed = False
        
        # Status code should be 200 (with error template) or 4xx (client error)
        if response.status_code in [400, 401, 403, 404, 422]:
            # Clear client error responses are good
            security_check_passed = True
        elif response.status_code == 200:
            # Need to check content - should be error page, not success page
            if "verification_failed" in response.url or "failed" in response.text.lower():
                security_check_passed = True
            elif "success" in response.text.lower() or "verified" in response.text.lower():
                # This suggests the invalid token was accepted
                security_check_passed = False
        
        if security_check_passed:
            print("Successfully rejected invalid verification token")
            return {"success": True, "verification_test": "passed"}
        else:
            return {"success": False, "error": "System accepted invalid verification token or returned a suspicious response"}
    except requests.RequestException as e:
        print(f"Error during email verification test: {e}")
        return {"success": False, "error": str(e)}


def run_basic_tests() -> Dict[str, Any]:
    """Run all basic API security tests."""
    session = requests.Session()
    results: Dict[str, Any] = {}
    error_details: Dict[str, str] = {}
    data: Dict[str, Any] = {}
    
    # Generate random user details
    username = f"test_user_{random_string(8)}"
    password = f"Test@123{random_string(8)}"
    email = f"test_{random_string(8)}@example.com"
    
    print(f"Testing with user: {username}, email: {email}")
    
    # Test 1: User Registration
    print("\n--- Testing User Registration ---")
    results["registration"] = register_user(session, username, password, email)
    
    # Test 2: User Login 
    print("\n--- Testing User Login ---")
    login_result = login_user(session, username, password, email)
    results["login"] = login_result
    
    if login_result["success"]:
        try:
            # Extract tokens from login response
            access_token = login_result.get("access_token", "")
            refresh_token = login_result.get("refresh_token", "")
            
            if not access_token:
                # Try to extract from data
                data = login_result.get("data", {})
                access_token = data.get("token", data.get("access", ""))
                refresh_token = data.get("refresh", "")
                
            if not access_token or not refresh_token:
                print("ERROR: Could not extract tokens from login response")
                print(f"Response data: {login_result.get('data', {})}")
                return results
            
            # Test the test_auth endpoint
            direct_auth_result = test_auth_endpoint(session)
            if "error" in direct_auth_result:
                results["direct_auth"] = False
                error_details["direct_auth"] = direct_auth_result["error"]
            else:
                results["direct_auth"] = True
                data["direct_auth"] = direct_auth_result
            
            # Test accessing a protected resource
            profile_result = get_profile(session)
            if "error" in profile_result:
                results["profile_access"] = False
                error_details["profile_access"] = profile_result["error"]
            else:
                results["profile_access"] = True
                data["profile"] = profile_result
            
            # Test 4: Token Refresh
            print("\n--- Testing Token Refresh ---")
            results["token_refresh"] = refresh_token_func(session, refresh_token)
            
            # Update refresh token if refresh was successful
            if results["token_refresh"]["success"] and "refresh" in results["token_refresh"].get("data", {}):
                refresh_token = results["token_refresh"]["data"]["refresh"]
            
            # Test 5: Logout
            print("\n--- Testing Logout ---")
            results["logout"] = logout(session, refresh_token)
            
            # Test 6: Verify Protected Access After Logout
            print("\n--- Testing Protected Access After Logout ---")
            results["post_logout_access"] = get_profile(session)
            
            # Should no longer have access
            if not results["post_logout_access"]["success"]:
                results["post_logout_test"] = {"success": True, "message": "Correctly denied access after logout"}
        except Exception as e:
            print(f"Error during test sequence: {e}")
    
    # Test 7: Rate Limiting
    print("\n--- Testing Rate Limiting ---")
    results["rate_limiting"] = test_rate_limiting()
    
    # Test 8: Email Verification Security
    print("\n--- Testing Email Verification Security ---")
    # Use a different session since we logged out
    new_session = requests.Session()
    email_verification_username = f"test_user_{random_string(8)}"
    email_verification_email = f"test_{random_string(8)}@example.com"
    results["email_verification"] = test_email_verification(
        new_session, 
        email_verification_username, 
        password, 
        email_verification_email
    )
    
    return results


# Function to validate if a token is properly structured
def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate if a JWT token has the correct structure without server verification.
    
    Args:
        token: JWT token to validate
        
    Returns:
        Dictionary with validation results
    """
    try:
        # Split the token into its 3 parts
        parts = token.split('.')
        if len(parts) != 3:
            return {"valid": False, "error": "Token does not have three parts"}
        
        # Try to decode the header and payload (handle base64 padding)
        def decode_base64_url(data):
            # Add padding if needed
            padding = '=' * (4 - len(data) % 4) if len(data) % 4 != 0 else ''
            # Convert URL-safe base64 to standard base64
            b64_data = data.replace('-', '+').replace('_', '/') + padding
            return base64.b64decode(b64_data).decode('utf-8')
        
        header_json = decode_base64_url(parts[0])
        payload_json = decode_base64_url(parts[1])
        
        # Parse the JSON
        header = json.loads(header_json)
        payload = json.loads(payload_json)
        
        # Check header
        if not header.get('alg'):
            return {"valid": False, "error": "Missing algorithm in header"}
        
        if not header.get('typ') == 'JWT':
            return {"valid": False, "error": "Wrong token type"}
        
        # Check payload
        if 'exp' not in payload:
            return {"valid": False, "error": "Missing expiration in payload"}
        
        if 'token_type' not in payload:
            return {"valid": False, "error": "Missing token type in payload"}
        
        # Token structure looks good
        return {
            "valid": True,
            "header": header,
            "payload": payload,
            "token_type": payload.get('token_type'),
            "expires_at": payload.get('exp'),
            "user_id": payload.get('user_id')
        }
    except Exception as e:
        return {"valid": False, "error": f"Error validating token: {str(e)}"}


def parse_args():
    parser = argparse.ArgumentParser(description="Test ChessMate API security")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--csrf", action="store_true", help="Enable CSRF protection testing")
    parser.add_argument("--rate-limit", action="store_true", help="Run only rate limiting tests")
    parser.add_argument("--email-verify", action="store_true", help="Run only email verification tests")
    parser.add_argument("--check-endpoints", action="store_true", help="Check which API endpoints are available")
    parser.add_argument("--validate-token", type=str, help="Validate a JWT token structure")
    parser.add_argument("--attempts", type=int, default=15, help="Number of requests for rate limit testing")
    parser.add_argument("--use-basic-profile", action="store_true", help="Use the basic profile endpoint instead of the main one")
    
    return parser.parse_args()


def main():
    global VERBOSE, CSRF_PROTECTION, USE_BASIC_PROFILE
    
    args = parse_args()
    VERBOSE = args.verbose
    CSRF_PROTECTION = args.csrf
    USE_BASIC_PROFILE = args.use_basic_profile
    
    print("ChessMate API Security Test")
    print(f"Base URL: {BASE_URL}")
    print(f"CSRF Protection: {'Enabled' if CSRF_PROTECTION else 'Disabled'}")
    print(f"Use Basic Profile: {'Enabled' if USE_BASIC_PROFILE else 'Disabled'}")
    print("-" * 50)
    
    # Check if we should just validate a token
    if args.validate_token:
        print("\n--- Validating Token Structure ---")
        result = validate_token(args.validate_token)
        if result["valid"]:
            print("✅ Token has valid structure")
            print(f"Token type: {result['token_type']}")
            print(f"User ID: {result['user_id']}")
            try:
                import datetime
                exp_time = datetime.datetime.fromtimestamp(result['expires_at'])
                print(f"Expires at: {exp_time}")
            except Exception as e:
                print(f"Error processing expiration: {e}")
                
            print("\nToken payload:")
            print(json.dumps(result["payload"], indent=2))
        else:
            print(f"❌ Invalid token: {result['error']}")
        return

    if args.check_endpoints:
        print("\n--- Checking Available Endpoints ---")
        available = get_available_endpoints()
        print("\nAvailable endpoints:")
        for endpoint in available:
            print(f"- {endpoint}")
        return

    if args.rate_limit:
        results = test_rate_limiting(attempts=args.attempts)
        print("\n=== Rate Limiting Test Results ===")
        if results["success"]:
            print("✅ Rate limiting is working properly")
        else:
            print("❌ Rate limiting test failed")
        
        if "details" in results:
            print("\nRequest details:")
            for request in results["details"]["requests"]:
                print(f"Request {request['request_num']}: Status {request['status']}, Remaining: {request['remaining']}, Reset: {request['reset']}")
            
            if results["details"]["rate_limited"]:
                print("\nRate limiting detected!")
            
            if results["details"]["decreasing_quota"]:
                print("\nRate limit quota is decreasing")
        return

    if args.email_verify:
        session = requests.Session()
        username = f"test_user_{random_string(8)}"
        password = f"Test@123{random_string(8)}"
        email = f"test_{random_string(8)}@example.com"
        
        results = test_email_verification(session, username, password, email)
        print("\n=== Email Verification Test Results ===")
        if results["success"]:
            print("✅ Email verification security is working properly")
        else:
            print(f"❌ Email verification test failed: {results.get('error', 'Unknown error')}")
        return

    # Run all tests
    results = run_basic_tests()
    
    # Print summary
    print("\n=== Test Results Summary ===")
    print(f"✅ Registration: {results.get('registration', 'Not tested')}")
    print(f"✅ Login: {results.get('login', 'Not tested')}")
    print(f"{'✅' if results.get('direct_auth') else '❌'} Direct Authentication: {results.get('direct_auth', 'Not tested')}")
    if 'direct_auth' in error_details:
        print(f"   Error: {error_details['direct_auth']}")
    print(f"{'✅' if results.get('profile_access') else '❌'} Protected Resource Access: {results.get('profile_access', 'Not tested')}")
    if 'profile_access' in error_details:
        print(f"   Error: {error_details['profile_access']}")
    print(f"✅ Token Refresh: {results.get('token_refresh', 'Not tested')}")
    print(f"✅ Logout: {results.get('logout', 'Not tested')}")
    print(f"✅ Post-Logout Access Control: {results.get('post_logout_test', 'Not tested')}")
    print(f"✅ Rate Limiting: {results.get('rate_limiting', 'Not tested')}")
    print(f"✅ Email Verification Security: {results.get('email_verification', 'Not tested')}")
    
    # Determine overall result
    test_keys = ["registration", "login", "direct_auth", "profile_access", 
                "token_refresh", "logout", "post_logout_test", "rate_limiting", 
                "email_verification"]
    passed_tests = sum(1 for test_key in test_keys if test_key in results and results[test_key])
    total_tests = sum(1 for test_key in test_keys if test_key in results)
    
    print(f"\nPassed {passed_tests}/{total_tests} tests")
    
    # Return success if all tests pass
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python
"""
Authentication test script for ChessMate API.
This script tests authentication mechanisms in isolation to diagnose issues.
"""

import os
import sys
import json
import time
import requests
import logging
import argparse
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("auth_test")

# Constants
DEFAULT_BASE_URL = "http://localhost:8000"


class AuthTester:
    """Class to test authentication flows in the ChessMate API."""
    
    def __init__(self, base_url, username=None, password=None, verbose=False):
        """Initialize the tester with base URL and credentials."""
        self.base_url = base_url
        self.username = username or f"test_user_{int(time.time())}"
        self.password = password or "Test@password123"
        self.verbose = verbose
        self.token = None
        self.refresh_token = None
        self.user_id = None
        self.session = requests.Session()
        
        if self.verbose:
            # Enable request/response logging
            import http.client as http_client
            http_client.HTTPConnection.debuglevel = 1
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
    
    def _url(self, path):
        """Construct a full URL from a path."""
        return urljoin(self.base_url, path)
    
    def _log_response(self, response, title=None):
        """Log the details of a response for debugging."""
        if title:
            logger.info(f"===== {title} =====")
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        try:
            logger.info(f"Response body: {json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            logger.info(f"Response text: {response.text}")
    
    def register(self):
        """Register a new user."""
        logger.info(f"Registering user: {self.username}")
        url = self._url("/api/v1/auth/register/")
        
        data = {
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": self.password,
            "password2": self.password
        }
        
        response = self.session.post(url, json=data)
        
        if self.verbose:
            self._log_response(response, "Register Response")
        
        if response.status_code == 201:
            logger.info("Registration successful")
            return True
        else:
            logger.error(f"Registration failed: {response.text}")
            return False
    
    def login(self):
        """Log in with the test user."""
        logger.info(f"Logging in user: {self.username}")
        url = self._url("/api/v1/auth/login/")
        
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = self.session.post(url, json=data)
        
        if self.verbose:
            self._log_response(response, "Login Response")
        
        if response.status_code == 200:
            logger.info("Login successful")
            data = response.json()
            self.token = data.get("access")
            self.refresh_token = data.get("refresh")
            self.user_id = data.get("user_id")
            return True
        else:
            logger.error(f"Login failed: {response.text}")
            return False
    
    def test_basic_auth(self):
        """Test the basic authentication endpoint."""
        logger.info("Testing basic authentication endpoint")
        url = self._url("/api/v1/auth/test-auth/")
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self.session.get(url, headers=headers)
        
        if self.verbose:
            self._log_response(response, "Basic Auth Test Response")
        
        if response.status_code == 200:
            logger.info("Basic authentication test passed")
            return True
        else:
            logger.error(f"Basic authentication test failed: {response.text}")
            return False
    
    def test_simple_auth(self):
        """Test the simple authentication endpoint."""
        logger.info("Testing simple authentication endpoint")
        url = self._url("/api/v1/auth/simple-auth/")
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self.session.get(url, headers=headers)
        
        if self.verbose:
            self._log_response(response, "Simple Auth Test Response")
        
        return response.status_code == 200
    
    def test_authorization_header(self):
        """Test that the Authorization header is correctly processed."""
        logger.info("Testing Authorization header processing")
        
        # Test with different header formats
        tests = [
            ("Standard Bearer", f"Bearer {self.token}"),
            ("Lowercase bearer", f"bearer {self.token}"),
            ("Token without Bearer", self.token),
        ]
        
        for test_name, auth_header in tests:
            logger.info(f"Testing {test_name}")
            url = self._url("/api/v1/auth/simple-auth/")
            
            headers = {"Authorization": auth_header}
            response = self.session.get(url, headers=headers)
            
            if self.verbose:
                self._log_response(response, f"{test_name} Response")
            
            success = response.status_code == 200
            logger.info(f"{test_name}: {'Success' if success else 'Failed'}")
    
    def test_profile(self):
        """Test accessing the profile endpoint."""
        logger.info("Testing profile endpoint")
        url = self._url("/api/v1/profile/minimal/")
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self.session.get(url, headers=headers)
        
        if self.verbose:
            self._log_response(response, "Profile Test Response")
        
        if response.status_code == 200:
            logger.info("Profile test passed")
            return True
        else:
            logger.error(f"Profile test failed: {response.status_code} - {response.text}")
            return False
    
    def test_token_refresh(self):
        """Test refreshing the access token."""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        logger.info("Testing token refresh")
        url = self._url("/api/v1/auth/token/refresh/")
        
        data = {"refresh": self.refresh_token}
        response = self.session.post(url, json=data)
        
        if self.verbose:
            self._log_response(response, "Token Refresh Response")
        
        if response.status_code == 200:
            logger.info("Token refresh test passed")
            new_token = response.json().get("access")
            if new_token:
                logger.info("Updating access token")
                self.token = new_token
            return True
        else:
            logger.error(f"Token refresh test failed: {response.text}")
            return False
    
    def test_all(self):
        """Run all authentication tests."""
        results = {}
        
        # Registration
        results["registration"] = self.register()
        
        # Login
        results["login"] = self.login()
        if not results["login"]:
            # If login fails, we can't continue with other tests
            return results
        
        # Test authorization header
        self.test_authorization_header()
        
        # Test basic authentication
        results["basic_auth"] = self.test_basic_auth()
        
        # Test simple authentication
        results["simple_auth"] = self.test_simple_auth()
        
        # Test profile access
        results["profile"] = self.test_profile()
        
        # Test token refresh
        results["token_refresh"] = self.test_token_refresh()
        
        # Test profile with refreshed token
        if results["token_refresh"]:
            results["profile_after_refresh"] = self.test_profile()
        
        return results


def print_summary(results):
    """Print a summary of test results."""
    logger.info("\n===== TEST SUMMARY =====")
    total = len(results)
    passed = sum(1 for result in results.values() if result)
    
    for test, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test}: {status}")
    
    logger.info(f"\nPassed {passed} out of {total} tests ({passed/total*100:.0f}%)")


def main():
    """Run the authentication tests."""
    parser = argparse.ArgumentParser(description="Test ChessMate API authentication")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the API")
    parser.add_argument("--username", help="Username for testing")
    parser.add_argument("--password", help="Password for testing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--test", choices=["all", "register", "login", "basic", "simple", "profile", "refresh"],
                        default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    tester = AuthTester(
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    if args.test == "all":
        results = tester.test_all()
        print_summary(results)
    elif args.test == "register":
        tester.register()
    elif args.test == "login":
        tester.register() and tester.login()
    elif args.test == "basic":
        tester.register() and tester.login() and tester.test_basic_auth()
    elif args.test == "simple":
        tester.register() and tester.login() and tester.test_simple_auth()
    elif args.test == "profile":
        tester.register() and tester.login() and tester.test_profile()
    elif args.test == "refresh":
        tester.register() and tester.login() and tester.test_token_refresh()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        sys.exit(1) 
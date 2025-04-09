#!/usr/bin/env python
"""
Test script for ChessMate health check endpoints.

This script sends requests to all health check endpoints and verifies that
they return the expected responses.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

import requests

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"


class HealthCheckTester:
    """Test health check endpoints."""

    def __init__(self, base_url: str, admin_user: str = None, admin_password: str = None):
        """
        Initialize the tester.

        Args:
            base_url: Base URL of the ChessMate application
            admin_user: Admin username for protected endpoints
            admin_password: Admin password for protected endpoints
        """
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.session = requests.Session()
        self.auth_token = None
        self.results = []

    def log(self, message: str, level: str = "info"):
        """
        Log a message with color-coded level.

        Args:
            message: Message to log
            level: Log level (info, success, warning, error)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if level == "success":
            prefix = f"{GREEN}[SUCCESS]{ENDC}"
        elif level == "warning":
            prefix = f"{YELLOW}[WARNING]{ENDC}"
        elif level == "error":
            prefix = f"{RED}[ERROR]{ENDC}"
        else:
            prefix = f"{BLUE}[INFO]{ENDC}"

        print(f"{prefix} {timestamp} - {message}")

    def authenticate(self) -> bool:
        """
        Authenticate as an admin user.

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self.admin_user or not self.admin_password:
            self.log("No admin credentials provided, skipping authentication", "warning")
            return False

        try:
            login_url = f"{self.base_url}/api/v1/user/login/"
            response = self.session.post(login_url, json={"username": self.admin_user, "password": self.admin_password})

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                if self.auth_token:
                    self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    self.log(f"Successfully authenticated as {self.admin_user}", "success")
                    return True
                else:
                    self.log("Authentication response did not contain a token", "error")
                    return False
            else:
                self.log(f"Authentication failed with status code {response.status_code}", "error")
                return False

        except Exception as e:
            self.log(f"Authentication error: {str(e)}", "error")
            return False

    def test_endpoint(
        self,
        endpoint: str,
        expected_status: int = 200,
        method: str = "GET",
        data: Dict[str, Any] = None,
        require_auth: bool = False,
    ) -> Dict[str, Any]:
        """
        Test a health check endpoint.

        Args:
            endpoint: Endpoint path
            expected_status: Expected HTTP status code
            method: HTTP method to use
            data: Data to send with the request
            require_auth: Whether the endpoint requires authentication

        Returns:
            Dict with test results
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        success = False
        status_code = None
        response_data = None
        error = None

        try:
            if require_auth and not self.auth_token:
                if not self.authenticate():
                    return {
                        "endpoint": endpoint,
                        "success": False,
                        "status_code": None,
                        "response_time": 0,
                        "error": "Authentication required but failed",
                    }

            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            status_code = response.status_code
            response_time = time.time() - start_time

            try:
                response_data = response.json()
            except:
                response_data = response.text

            success = status_code == expected_status

            if success:
                self.log(f"Endpoint {endpoint} returned {status_code} in {response_time:.2f}s", "success")
            else:
                self.log(f"Endpoint {endpoint} returned {status_code}, expected {expected_status}", "error")

        except requests.exceptions.ConnectionError:
            error = f"Could not connect to {url}"
            self.log(error, "error")
        except Exception as e:
            error = str(e)
            self.log(f"Error testing {endpoint}: {error}", "error")

        result = {
            "endpoint": endpoint,
            "success": success,
            "status_code": status_code,
            "response_time": time.time() - start_time,
            "response_data": response_data,
            "error": error,
        }

        self.results.append(result)
        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all health check tests.

        Returns:
            Dict with test summary
        """
        self.log("Starting health check tests...")

        # Basic health check (unauthenticated)
        self.test_endpoint("/health/")

        # Readiness check (unauthenticated)
        self.test_endpoint("/readiness/")

        # API health check (unauthenticated)
        self.test_endpoint("/api/v1/health/")

        # API detailed health check (unauthenticated)
        self.test_endpoint("/api/v1/health/detailed/")

        # API system status (authenticated admin only)
        self.test_endpoint("/api/v1/system/status/", require_auth=True)

        # Run Celery health check task (authenticated admin only)
        self.test_endpoint("/api/v1/health/run-check-task/", method="POST", require_auth=True)

        # Application info (unauthenticated)
        self.test_endpoint("/api/v1/info/")

        # Calculate summary
        success_count = sum(1 for r in self.results if r["success"])

        summary = {
            "total_tests": len(self.results),
            "successful_tests": success_count,
            "failed_tests": len(self.results) - success_count,
            "results": self.results,
        }

        # Log summary
        self.log("\nTest Summary:", "info")
        self.log(f"Total tests: {summary['total_tests']}", "info")
        self.log(f"Successful: {summary['successful_tests']}", "success" if summary["failed_tests"] == 0 else "info")
        self.log(f"Failed: {summary['failed_tests']}", "error" if summary["failed_tests"] > 0 else "info")

        return summary


def main():
    """Run the health check tests."""
    parser = argparse.ArgumentParser(description="Test ChessMate health check endpoints")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the ChessMate application")
    parser.add_argument("--admin-user", help="Admin username for protected endpoints")
    parser.add_argument("--admin-password", help="Admin password for protected endpoints")
    parser.add_argument("--output", help="Output file for test results (JSON)")

    args = parser.parse_args()

    tester = HealthCheckTester(args.url, args.admin_user, args.admin_password)
    summary = tester.run_all_tests()

    if args.output:
        with open(args.output, "w") as f:
            # Remove response_data for cleaner output
            for result in summary["results"]:
                result.pop("response_data", None)
            json.dump(summary, f, indent=2)
            print(f"\nSaved test results to {args.output}")

    # Return non-zero exit code if any tests failed
    if summary["failed_tests"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

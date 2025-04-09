#!/usr/bin/env python
"""
Test script for ChessMate cache invalidation system.

This script tests the tag-based cache invalidation system using
direct Redis commands and API calls.
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

import redis
import requests

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"


class CacheInvalidationTester:
    """Test cache invalidation functionality."""

    def __init__(self, base_url: str, redis_url: str, admin_user: str = None, admin_password: str = None):
        """
        Initialize the tester.

        Args:
            base_url: Base URL of the ChessMate application
            redis_url: Redis URL for direct cache inspection
            admin_user: Admin username for protected endpoints
            admin_password: Admin password for protected endpoints
        """
        self.base_url = base_url.rstrip("/")
        self.redis_url = redis_url
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.session = requests.Session()
        self.auth_token = None
        self.redis_client = None
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

    def setup(self) -> bool:
        """
        Set up connections and authenticate.

        Returns:
            True if setup succeeded, False otherwise
        """
        # Connect to Redis
        try:
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            self.log("Connected to Redis", "success")
        except Exception as e:
            self.log(f"Failed to connect to Redis: {str(e)}", "error")
            return False

        # Authenticate if credentials provided
        if self.admin_user and self.admin_password:
            try:
                login_url = f"{self.base_url}/api/v1/user/login/"
                response = self.session.post(
                    login_url, json={"username": self.admin_user, "password": self.admin_password}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data.get("token")
                    if self.auth_token:
                        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                        self.log(f"Successfully authenticated as {self.admin_user}", "success")
                    else:
                        self.log("Authentication response did not contain a token", "error")
                        return False
                else:
                    self.log(f"Authentication failed with status code {response.status_code}", "error")
                    return False

            except Exception as e:
                self.log(f"Authentication error: {str(e)}", "error")
                return False

        return True

    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any] = None) -> None:
        """
        Add a test result.

        Args:
            test_name: Name of the test
            success: Whether the test succeeded
            details: Additional details about the test
        """
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }

        self.results.append(result)

        if success:
            self.log(f"Test '{test_name}' passed", "success")
        else:
            self.log(f"Test '{test_name}' failed", "error")
            if details:
                self.log(f"Details: {json.dumps(details, indent=2)}")

    def setup_test_cache_entries(self, count: int = 5, tag: str = "test") -> List[str]:
        """
        Set up test cache entries with a specific tag.

        Args:
            count: Number of test entries to create
            tag: Tag to use for the entries

        Returns:
            List of cache keys created
        """
        keys = []
        tag_separator = "::tag::"

        for i in range(count):
            # Create a unique key with the tag
            test_id = str(uuid.uuid4())
            key = f"chessmate:test:{test_id}"
            tag_key = f"{key}{tag_separator}{tag}"

            # Store a value in the main key
            self.redis_client.set(key, f"test-value-{i}")

            # Store a reference in the tag key (dummy value)
            self.redis_client.set(tag_key, "1")

            keys.append(key)

        return keys

    def get_cache_size(self) -> int:
        """
        Get the number of keys in the Redis database.

        Returns:
            Number of keys
        """
        return self.redis_client.dbsize()

    def test_direct_invalidation(self) -> None:
        """Test direct invalidation through Redis."""
        tag = "test_direct"

        # Get initial cache size
        initial_size = self.get_cache_size()
        self.log(f"Initial cache size: {initial_size}")

        # Create test entries
        keys = self.setup_test_cache_entries(5, tag)

        # Verify the keys exist
        after_setup_size = self.get_cache_size()
        self.log(f"Cache size after setup: {after_setup_size}")

        # Count keys with the test tag
        keys_with_tag = len(self.redis_client.keys(f"*::tag::{tag}"))

        # Test if the expected number of keys were created
        # We expect 5 main keys and 5 tag keys
        success = len(keys) == 5 and keys_with_tag == 5

        if success:
            # Now invalidate using direct pattern delete on the tag
            pattern = f"*::tag::{tag}*"
            deleted = self.redis_client.delete(*self.redis_client.keys(pattern))

            # Check if all tag keys were deleted
            remaining_tag_keys = len(self.redis_client.keys(pattern))

            self.add_test_result(
                "direct_invalidation",
                deleted == 5 and remaining_tag_keys == 0,
                {
                    "keys_created": len(keys),
                    "tag_keys_created": keys_with_tag,
                    "keys_deleted": deleted,
                    "remaining_tag_keys": remaining_tag_keys,
                },
            )
        else:
            self.add_test_result(
                "direct_invalidation",
                False,
                {
                    "keys_created": len(keys),
                    "tag_keys_created": keys_with_tag,
                    "expected_keys": 5,
                    "expected_tag_keys": 5,
                },
            )

    def test_api_invalidation(self) -> None:
        """Test invalidation through the API."""
        if not self.auth_token:
            self.log("API invalidation test requires authentication. Skipping.", "warning")
            self.add_test_result("api_invalidation", False, {"reason": "Authentication required"})
            return

        tag = "test_api"

        # Create test entries
        keys = self.setup_test_cache_entries(5, tag)

        # Count keys with the test tag
        keys_with_tag = len(self.redis_client.keys(f"*::tag::{tag}"))

        # Verify the keys exist
        self.log(f"Created {len(keys)} test keys and {keys_with_tag} tag keys")

        try:
            # Call the API to invalidate the tag
            url = f"{self.base_url}/api/v1/system/cache/clear/"
            response = self.session.post(url, json={"tags": [tag]})

            response_data = response.json() if response.status_code == 200 else None

            # Check if all tag keys were deleted
            remaining_tag_keys = len(self.redis_client.keys(f"*::tag::{tag}*"))

            self.add_test_result(
                "api_invalidation",
                response.status_code == 200 and remaining_tag_keys == 0,
                {
                    "status_code": response.status_code,
                    "response": response_data,
                    "keys_created": len(keys),
                    "tag_keys_created": keys_with_tag,
                    "remaining_tag_keys": remaining_tag_keys,
                },
            )
        except Exception as e:
            self.add_test_result("api_invalidation", False, {"error": str(e)})

    def test_global_invalidation(self) -> None:
        """Test global cache invalidation."""
        if not self.auth_token:
            self.log("Global invalidation test requires authentication. Skipping.", "warning")
            self.add_test_result("global_invalidation", False, {"reason": "Authentication required"})
            return

        # Create test entries with different tags
        tags = ["test1", "test2", "test3"]
        all_keys = []

        for tag in tags:
            keys = self.setup_test_cache_entries(3, tag)
            all_keys.extend(keys)

        # Store the initial cache size
        initial_size = self.get_cache_size()
        self.log(f"Cache size before global invalidation: {initial_size}")

        try:
            # Call the API to invalidate all cache
            url = f"{self.base_url}/api/v1/system/cache/clear/"
            response = self.session.post(url, json={})

            response_data = response.json() if response.status_code == 200 else None

            # Check the cache size after invalidation
            # Note: It might not be zero since other processes might be using the cache
            after_size = self.get_cache_size()

            # Check if our test keys were deleted
            remaining_test_keys = 0
            for key in all_keys:
                if self.redis_client.exists(key):
                    remaining_test_keys += 1

            self.add_test_result(
                "global_invalidation",
                response.status_code == 200 and remaining_test_keys == 0,
                {
                    "status_code": response.status_code,
                    "response": response_data,
                    "total_keys_created": len(all_keys),
                    "cache_size_before": initial_size,
                    "cache_size_after": after_size,
                    "remaining_test_keys": remaining_test_keys,
                },
            )
        except Exception as e:
            self.add_test_result("global_invalidation", False, {"error": str(e)})

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all cache invalidation tests.

        Returns:
            Dict with test summary
        """
        self.log("Starting cache invalidation tests...")

        # Setup connections
        if not self.setup():
            self.log("Setup failed. Exiting.", "error")
            return {"success": False, "error": "Setup failed"}

        # Run tests
        self.test_direct_invalidation()
        self.test_api_invalidation()
        self.test_global_invalidation()

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
    """Run the cache invalidation tests."""
    parser = argparse.ArgumentParser(description="Test ChessMate cache invalidation system")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the ChessMate application")
    parser.add_argument("--redis", default="redis://localhost:6379/0", help="Redis URL")
    parser.add_argument("--admin-user", help="Admin username for protected endpoints")
    parser.add_argument("--admin-password", help="Admin password for protected endpoints")
    parser.add_argument("--output", help="Output file for test results (JSON)")

    args = parser.parse_args()

    tester = CacheInvalidationTester(args.url, args.redis, args.admin_user, args.admin_password)
    summary = tester.run_all_tests()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
            print(f"\nSaved test results to {args.output}")

    # Return non-zero exit code if any tests failed
    if summary.get("failed_tests", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

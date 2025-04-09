#!/usr/bin/env python
"""
Unified test runner for ChessMate project.

This script provides a simple command-line interface for running tests with various options:
- Standalone tests (no Django dependencies)
- Django-integrated tests
- All tests together
- Coverage reporting
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests for ChessMate project", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--standalone", action="store_true", help="Run standalone tests only")
    test_group.add_argument("--django", action="store_true", help="Run Django tests only")
    test_group.add_argument("--path", type=str, help="Run tests in specific path")

    # Test execution options
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase verbosity (can use multiple times)"
    )
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--fail-under", type=float, default=80.0, help="Fail if coverage is under given percentage")
    parser.add_argument("--keep-db", action="store_true", help="Keep test database between runs")

    return parser.parse_args()


def setup_environment():
    """Set up the environment for testing."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()

    # Make sure we're in the right directory
    os.chdir(script_dir)

    # Add the project root to PYTHONPATH
    sys.path.insert(0, str(script_dir))
    os.environ["PYTHONPATH"] = str(script_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Set testing flag
    os.environ["TESTING"] = "True"

    # Return the script directory
    return script_dir


def build_command(args):
    """Build the pytest command based on arguments."""
    cmd = [sys.executable, "-m", "pytest"]

    # Handle verbosity
    if args.verbose > 0:
        cmd.append("-" + "v" * args.verbose)

    # Handle coverage
    if args.coverage:
        coverage_args = ["--cov=chess_mate"]
        if args.html:
            coverage_args.append("--cov-report=html")
        coverage_args.append("--cov-report=term")
        if args.fail_under:
            coverage_args.append(f"--cov-fail-under={args.fail_under}")
        cmd.extend(coverage_args)

    # Handle test database
    if args.keep_db:
        cmd.append("--reuse-db")

    # Determine test paths
    if args.standalone:
        cmd.extend(["-p", "no:django", "standalone_tests/"])
    elif args.django:
        cmd.extend(["--ds=chess_mate.test_settings", "chess_mate/core/tests/"])
    elif args.path:
        # User specified a custom path
        if args.path.startswith("standalone_tests"):
            cmd.extend(["-p", "no:django", args.path])
        else:
            # Assume Django tests if not in standalone_tests
            cmd.extend(["--ds=chess_mate.test_settings", args.path])
    else:
        # Run all tests by default
        cmd.extend(["--ds=chess_mate.test_settings", "chess_mate/core/tests/", "standalone_tests/"])

    return cmd


def run_tests(cmd):
    """Run the tests with the given command."""
    print("\n" + "=" * 80)
    print(f"Running: {' '.join(cmd)}")
    print("=" * 80 + "\n")

    # Set the environment
    env = os.environ.copy()

    # Run the command
    return subprocess.run(cmd, env=env)


def main():
    """Main entry point."""
    args = parse_args()
    script_dir = setup_environment()

    # Build the command
    cmd = build_command(args)

    # Run the tests
    result = run_tests(cmd)

    # Return the exit code
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

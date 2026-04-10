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
import re
import subprocess
import sys
import threading
import time
from queue import Empty, Queue
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

    # Add project paths to PYTHONPATH.
    # Keep repository root first so `chess_mate.core` resolves correctly
    # instead of being shadowed by the nested `chess_mate/chess_mate` package.
    app_dir = script_dir / "chess_mate"
    sys.path.insert(0, str(app_dir))
    sys.path.insert(0, str(script_dir))

    os.environ["PYTHONPATH"] = (
        str(script_dir) + os.pathsep + str(app_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")
    )

    # Set testing flag
    os.environ["TESTING"] = "True"

    # Return the script directory
    return script_dir


def build_command(args):
    """Build the pytest command based on arguments."""
    cmd = [sys.executable, "-m", "pytest"]
    django_settings = "chess_mate.test_settings"

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
        cmd.extend([f"--ds={django_settings}", "core/tests/"])
    elif args.path:
        # User specified a custom path
        if args.path.startswith("standalone_tests"):
            cmd.extend(["-p", "no:django", args.path])
        else:
            # Assume Django tests if not in standalone_tests
            cmd.extend([f"--ds={django_settings}", args.path])
    else:
        # Run all tests by default
        cmd.extend([f"--ds={django_settings}", "chess_mate/core/tests/", "standalone_tests/"])

    return cmd


def run_tests(cmd):
    """Run the tests with the given command."""
    print("\n" + "=" * 80, flush=True)
    print(f"Running: {' '.join(cmd)}", flush=True)
    print("=" * 80 + "\n", flush=True)

    # Set the environment
    env = os.environ.copy()

    # Run Django tests from app root to preserve historical import behavior.
    django_cwd = None
    if any(arg.startswith("--ds=") for arg in cmd):
        django_cwd = str(Path(__file__).parent.absolute() / "chess_mate")

    # Stream output while guarding against CI hangs that occasionally occur
    # after pytest prints the final summary but before process termination.
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=django_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    summary_seen = False
    success_summary = False
    last_output = time.time()
    start_time = time.time()
    last_heartbeat = start_time
    summary_pattern = re.compile(r"=+\s+\d+\s+passed(?:,\s+\d+\s+skipped)?")
    line_queue: Queue = Queue()

    assert process.stdout is not None

    def _reader_thread(stdout, output_queue):
        """Read subprocess output lines without blocking the main watchdog loop."""
        try:
            for out_line in iter(stdout.readline, ""):
                output_queue.put(out_line)
        finally:
            output_queue.put(None)

    reader = threading.Thread(target=_reader_thread, args=(process.stdout, line_queue), daemon=True)
    reader.start()

    while True:
        try:
            line = line_queue.get(timeout=1)
        except Empty:
            line = None

        if line is None:
            if process.poll() is not None:
                break

            now = time.time()
            if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and (now - last_heartbeat) >= 30:
                elapsed = int(now - start_time)
                print(f"[run_tests] Still running... {elapsed}s elapsed, waiting for pytest output", flush=True)
                last_heartbeat = now

            # CI-only safety valve: if startup emits no output for too long,
            # terminate to avoid a deadlocked job that never progresses.
            if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and (now - last_output) > 240:
                print("\n[run_tests] No pytest output for 240s in CI; terminating as hung process.", flush=True)
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                return subprocess.CompletedProcess(cmd, 1)

            continue

        if line:
            print(line, end="", flush=True)
            last_output = time.time()

            lower_line = line.lower()
            if summary_pattern.search(line):
                summary_seen = True
                success_summary = ("failed" not in lower_line) and ("error" not in lower_line)

        if process.poll() is not None:
            break

        # CI-only safety valve: if pytest printed a success summary and then
        # emits no more output for a minute, treat it as a shutdown hang.
        if (
            os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
            and summary_seen
            and success_summary
            and (time.time() - last_output) > 60
        ):
            print("\nDetected post-summary pytest shutdown hang in CI; terminating process.", flush=True)
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            return subprocess.CompletedProcess(cmd, 0)

    reader.join(timeout=1)

    return subprocess.CompletedProcess(cmd, process.returncode)


def main():
    """Main entry point."""
    args = parse_args()
    setup_environment()

    # Build the command
    cmd = build_command(args)

    # Run the tests
    result = run_tests(cmd)

    # Return the exit code
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

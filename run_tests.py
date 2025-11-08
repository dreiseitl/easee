#!/usr/bin/env python
"""
Simple test runner script
"""
import sys
import subprocess

def run_tests():
    """Run pytest with appropriate options"""
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "tests/"
    ]
    
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)


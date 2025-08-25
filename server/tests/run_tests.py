#!/usr/bin/env python3
"""
Test runner script for the server application.
Run this script to execute all tests using pytest.
"""

import sys
import os
import subprocess
import pytest

def run_tests():
    """Run all tests in the tests directory"""
    # Get the directory where this script is located
    test_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(test_dir)
    
    # Change to server directory
    os.chdir(server_dir)
    
    # Run pytest with verbose output and proper configuration
    args = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes",
        "--strict-markers",
        "--disable-warnings"
    ]
    
    print("Running tests with pytest...")
    print(f"Test directory: {test_dir}")
    print(f"Server directory: {server_dir}")
    print(f"Command: {' '.join(args)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(args, check=True)
        print("-" * 50)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

def run_specific_test(test_file):
    """Run a specific test file"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(test_dir)
    
    os.chdir(server_dir)
    
    args = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}",
        "-v",
        "--tb=short",
        "--color=yes",
        "--strict-markers",
        "--disable-warnings"
    ]
    
    print(f"Running specific test: {test_file}")
    print(f"Command: {' '.join(args)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(args, check=True)
        print("-" * 50)
        print("✅ Test passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Test failed with exit code: {e.returncode}")
        return e.returncode

def run_tests_with_coverage():
    """Run tests with coverage report"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(test_dir)
    
    os.chdir(server_dir)
    
    args = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes",
        "--strict-markers",
        "--disable-warnings",
        "--cov=main",
        "--cov=scripts",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ]
    
    print("Running tests with coverage...")
    print(f"Command: {' '.join(args)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(args, check=True)
        print("-" * 50)
        print("✅ Tests with coverage completed!")
        print("📊 Coverage report generated in htmlcov/")
        return 0
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--coverage":
            # Run tests with coverage
            exit_code = run_tests_with_coverage()
        else:
            # Run specific test file
            test_file = sys.argv[1]
            exit_code = run_specific_test(test_file)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code) 
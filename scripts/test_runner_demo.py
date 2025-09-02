#!/usr/bin/env python3

"""
Simple demo script to test if the test runner is working properly
Run this with: python test_runner_demo.py
"""

import subprocess
import sys
import os

def main():
    print("🧪 Testing the OmniPDF test runner...")
    print("=" * 50)
    
    # Change to the project directory (parent of scripts directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    os.chdir(project_dir)
    
    # Test with a single service first (chat_service is likely to work)
    print("\n1️⃣ Testing with a single service (chat_service)...")
    try:
        result = subprocess.run(
            ["./scripts/run_tests.sh", "chat_service"], 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ Single service test passed!")
        else:
            print("❌ Single service test failed!")
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running test: {e}")

if __name__ == "__main__":
    main()
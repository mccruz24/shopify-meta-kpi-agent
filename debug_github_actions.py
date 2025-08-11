#!/usr/bin/env python3
"""
Debug script to understand GitHub Actions environment
"""

import os
import sys

print("=== GitHub Actions Debug Info ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {os.path.abspath(__file__)}")
print(f"Directory contents:")
for item in sorted(os.listdir(".")):
    print(f"  - {item}")

print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path (first 5):")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i+1}. {path}")

print(f"\nEnvironment variables (relevant):")
env_vars = ['NOTION_TOKEN', 'PRINTIFY_API_TOKEN', 'PRINTIFY_ANALYTICS_DB_ID', 'PYTHONPATH']
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"  {var}: {'***' if 'TOKEN' in var or 'ID' in var else value}")
    else:
        print(f"  {var}: (not set)")

# Test if we can import required modules
print(f"\nTesting imports:")
try:
    import requests
    print("  ✅ requests")
except ImportError as e:
    print(f"  ❌ requests: {e}")

try:
    from datetime import datetime
    print("  ✅ datetime")
except ImportError as e:
    print(f"  ❌ datetime: {e}")

print(f"\nLooking for scheduler files:")
scheduler_files = [
    "printify_analytics_scheduler.py",
    "schedulers/printify_analytics_scheduler.py",
    "printify_analytics_sync.py"
]

for file in scheduler_files:
    if os.path.exists(file):
        print(f"  ✅ {file} exists")
    else:
        print(f"  ❌ {file} missing")

print("\n=== End Debug Info ===")
#!/usr/bin/env python3
"""
Robust wrapper for Printify Analytics Scheduler
Handles path resolution for GitHub Actions
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🔍 Starting Printify Analytics wrapper")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    print(f"📁 Script directory: {script_dir}")
    print(f"📁 Current working directory: {Path.cwd()}")
    
    # Look for the scheduler in multiple locations
    scheduler_locations = [
        script_dir / "printify_analytics_scheduler.py",
        script_dir / "schedulers" / "printify_analytics_scheduler.py",
    ]
    
    scheduler_path = None
    for location in scheduler_locations:
        if location.exists():
            scheduler_path = location
            print(f"✅ Found scheduler at: {scheduler_path}")
            break
    
    if not scheduler_path:
        print("❌ Could not find printify_analytics_scheduler.py")
        print("Available files:")
        for item in sorted(script_dir.iterdir()):
            print(f"  - {item.name}")
        sys.exit(1)
    
    # Pass through all command line arguments
    cmd = [sys.executable, str(scheduler_path)] + sys.argv[1:]
    print(f"🚀 Executing: {' '.join(cmd)}")
    
    # Execute the scheduler
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"❌ Failed to execute scheduler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
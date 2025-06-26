#!/usr/bin/env python3
"""
Shopify + Meta Ads KPI Agent
Main entry point for the application
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Config

def test_google_sheets_oauth():
    """Test Google Sheets connection with OAuth"""
    try:
        from src.loaders.sheets_loader import SheetsLoader
        
        print("🔍 Testing Google Sheets OAuth connection...")
        
        # Check if OAuth credentials file exists
        if not os.path.exists(Config.GOOGLE_OAUTH_CREDENTIALS_FILE):
            print(f"❌ OAuth credentials file not found: {Config.GOOGLE_OAUTH_CREDENTIALS_FILE}")
            return False
            
        # Check if Sheet ID is configured
        if not Config.GOOGLE_SHEET_ID:
            print("❌ Google Sheet ID not configured in .env file")
            return False
        
        # Test connection
        loader = SheetsLoader()
        success, message = loader.test_connection()
        
        if success:
            print("✅ Google Sheets OAuth connection successful!")
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ Google Sheets connection failed: {message}")
            return False
        
    except Exception as e:
        print(f"❌ Google Sheets OAuth connection failed: {e}")
        return False

def main():
    """Main function to test setup"""
    print("🚀 Shopify-Meta KPI Agent")
    print(f"📅 Current time: {datetime.now()}")
    print("✅ Python environment is working!")
    
    # Test imports
    try:
        import requests
        import pandas as pd
        import gspread
        from google.oauth2.credentials import Credentials
        print("✅ All required packages imported successfully!")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test Google Sheets OAuth connection
    if test_google_sheets_oauth():
        print("🎉 Google Sheets OAuth setup complete!")
    else:
        print("⚠️  Google Sheets OAuth setup needs attention")
    
    print("\n📋 Next steps:")
    print("1. Set up Shopify API credentials")
    print("2. Set up Meta Ads API credentials")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
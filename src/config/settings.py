import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the KPI Agent"""
    
    # Shopify Configuration
    SHOPIFY_SHOP_URL = os.getenv('SHOPIFY_SHOP_URL')
    SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
    
    # Meta Ads Configuration
    META_ACCESS_TOKEN = os.getenv('META_ACCESS_TOKEN')
    META_AD_ACCOUNT_ID = os.getenv('META_AD_ACCOUNT_ID')
    META_APP_ID = os.getenv('META_APP_ID')
    META_APP_SECRET = os.getenv('META_APP_SECRET')
    
    # Google Sheets Configuration (OAuth)
    GOOGLE_OAUTH_CREDENTIALS_FILE = os.getenv('GOOGLE_OAUTH_CREDENTIALS_FILE')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_google_config(cls):
        """Validate Google Sheets configuration"""
        if not cls.GOOGLE_OAUTH_CREDENTIALS_FILE:
            return False, "GOOGLE_OAUTH_CREDENTIALS_FILE not set in .env"
        
        if not cls.GOOGLE_SHEET_ID:
            return False, "GOOGLE_SHEET_ID not set in .env"
        
        if not os.path.exists(cls.GOOGLE_OAUTH_CREDENTIALS_FILE):
            return False, f"OAuth credentials file not found: {cls.GOOGLE_OAUTH_CREDENTIALS_FILE}"
        
        return True, "Google configuration valid"
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("📋 Current Configuration:")
        print(f"  Shopify URL: {'✅ Set' if cls.SHOPIFY_SHOP_URL else '❌ Not set'}")
        print(f"  Shopify Token: {'✅ Set' if cls.SHOPIFY_ACCESS_TOKEN else '❌ Not set'}")
        print(f"  Meta Token: {'✅ Set' if cls.META_ACCESS_TOKEN else '❌ Not set'}")
        print(f"  Meta Account: {'✅ Set' if cls.META_AD_ACCOUNT_ID else '❌ Not set'}")
        print(f"  Google Creds: {'✅ Set' if cls.GOOGLE_OAUTH_CREDENTIALS_FILE else '❌ Not set'}")
        print(f"  Google Sheet: {'✅ Set' if cls.GOOGLE_SHEET_ID else '❌ Not set'}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
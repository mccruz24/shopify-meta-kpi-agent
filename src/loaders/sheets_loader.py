import os
import sys
import gspread
from datetime import datetime
from dotenv import load_dotenv

# Simple path handling
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

load_dotenv()

try:
    from src.utils.google_auth import GoogleAuthenticator
except ImportError:
    print("❌ Could not import GoogleAuthenticator")
    # Fallback - we'll handle this in the class

class SheetsLoader:
    """Handle Google Sheets operations"""
    
    def __init__(self):
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self._client = None
        self._sheet = None
        
        # Try to import and use GoogleAuthenticator
        try:
            from src.utils.google_auth import GoogleAuthenticator
            self.authenticator = GoogleAuthenticator()
        except ImportError:
            print("⚠️  GoogleAuthenticator not available, using fallback")
            self.authenticator = None
    
    @property
    def client(self):
        """Get authenticated gspread client"""
        if self._client is None:
            if self.authenticator:
                creds = self.authenticator.get_credentials()
                self._client = gspread.authorize(creds)
            else:
                # Fallback authentication (you might need to adjust this)
                print("❌ No authentication method available")
                return None
        return self._client
    
    @property
    def sheet(self):
        """Get the Google Sheet"""
        if self._sheet is None and self.client:
            self._sheet = self.client.open_by_key(self.sheet_id)
        return self._sheet
    
    def test_connection(self):
        """Test the connection to Google Sheets"""
        try:
            if not self.sheet:
                return False, "Could not connect to Google Sheets"
            
            worksheet = self.sheet.sheet1
            test_message = f'Connection test: {datetime.now()}'
            # Don't actually update during test
            return True, f"Successfully connected to sheet: {self.sheet.title}"
        except Exception as e:
            return False, str(e)
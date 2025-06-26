#!/usr/bin/env python3
"""
Simple test to update one cell in Google Sheets
"""

import os
import sys
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.loaders.sheets_loader import SheetsLoader

def test_single_cell_update():
    """Test updating a single cell"""
    try:
        sheets = SheetsLoader()
        
        print("🔍 Testing single cell update...")
        
        # Get the worksheet
        worksheet = sheets.sheet.sheet1
        
        # Test different update methods
        test_value = 31.90
        test_cell = 'B4'
        
        print(f"📝 Attempting to update {test_cell} with value: {test_value}")
        
        # Method 1: Using update with 2D array
        try:
            worksheet.update(test_cell, [[test_value]])
            print("✅ Method 1 (2D array) successful!")
            return True
        except Exception as e1:
            print(f"❌ Method 1 failed: {e1}")
        
        # Method 2: Using update_acell
        try:
            worksheet.update_acell(test_cell, test_value)
            print("✅ Method 2 (update_acell) successful!")
            return True
        except Exception as e2:
            print(f"❌ Method 2 failed: {e2}")
        
        # Method 3: Using batch update
        try:
            worksheet.batch_update([{
                'range': test_cell,
                'values': [[test_value]]
            }])
            print("✅ Method 3 (batch_update) successful!")
            return True
        except Exception as e3:
            print(f"❌ Method 3 failed: {e3}")
        
        print("❌ All update methods failed")
        return False
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

def main():
    print("🧪 Simple Google Sheets Update Test")
    print("=" * 40)
    
    test_single_cell_update()

if __name__ == "__main__":
    main()
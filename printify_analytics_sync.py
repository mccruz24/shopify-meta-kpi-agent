#!/usr/bin/env python3
"""
Printify Analytics Sync - Core Printify analytics collection logic
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import time
import random
from typing import Dict, List, Optional

# Add project root and src directory to path for GitHub Actions compatibility  
# Force refresh for GitHub Actions
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from src.extractors.printify_extractor import PrintifyAnalyticsExtractor
from src.loaders.printify_notion_loader import PrintifyNotionLoader


class PrintifyAnalyticsSync:
    """Printify analytics collection and sync system"""
    
    def __init__(self, database_id: str):
        self.database_id = database_id
        self.extractor = PrintifyAnalyticsExtractor()
        self.loader = PrintifyNotionLoader()
        self.loader.set_database_id(database_id)
    
    def sync_single_date(self, target_date: datetime) -> bool:
        """Sync Printify analytics for a single date"""
        
        date_str = target_date.strftime('%Y-%m-%d')
        print(f"🖨️ [PRINTIFY] Collecting Printify analytics for {date_str}")
        
        try:
            # Extract Printify data
            print(f"   📊 Extracting Printify data...")
            printify_data = self.extractor.extract_single_date(target_date)
            
            if not printify_data:
                print(f"   ℹ️  No Printify data found for {date_str}")
                return True
            
            print(f"   ✅ Extracted {len(printify_data)} Printify records")
            
            # Load into Notion
            print(f"   📝 Loading Printify data into Notion...")
            results = self.loader.load_orders_batch(printify_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"✅ Successfully synced Printify analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing Printify analytics for {date_str}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connections to all required services"""
        try:
            # Test extractor
            if not self.extractor.test_connection():
                print("❌ Printify extractor connection failed")
                return False
            
            # Test loader
            if not self.loader.test_connection():
                print("❌ Printify loader connection failed")
                return False
            
            print("✅ All Printify analytics connections successful")
            return True
            
        except Exception as e:
            print(f"❌ Printify analytics connection test failed: {e}")
            return False 
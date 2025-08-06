#!/usr/bin/env python3
"""
Traffic Analytics Sync - Core traffic analytics collection logic
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import time
import random
from typing import Dict, List, Optional

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.traffic_analytics_extractor import TrafficAnalyticsExtractor
from src.loaders.traffic_notion_loader import TrafficNotionLoader


class TrafficAnalyticsSync:
    """Traffic analytics collection and sync system"""
    
    def __init__(self):
        self.extractor = TrafficAnalyticsExtractor()
        self.loader = TrafficNotionLoader()
    
    def sync_single_date(self, target_date: datetime) -> bool:
        """Sync traffic analytics for a single date"""
        
        date_str = target_date.strftime('%Y-%m-%d')
        print(f"🚗 [TRAFFIC] Collecting traffic analytics for {date_str}")
        
        try:
            # Extract traffic data
            print(f"   📊 Extracting traffic data...")
            traffic_data = self.extractor.extract_single_date(target_date)
            
            if not traffic_data:
                print(f"   ℹ️  No traffic data found for {date_str}")
                return True
            
            print(f"   ✅ Extracted {len(traffic_data)} traffic records")
            
            # Load into Notion
            print(f"   📝 Loading traffic data into Notion...")
            results = self.loader.load_traffic_batch(traffic_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"✅ Successfully synced traffic analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing traffic analytics for {date_str}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connections to all required services"""
        try:
            # Test extractor
            if not self.extractor.test_connection():
                print("❌ Traffic extractor connection failed")
                return False
            
            # Test loader
            if not self.loader.test_connection():
                print("❌ Traffic loader connection failed")
                return False
            
            print("✅ All traffic analytics connections successful")
            return True
            
        except Exception as e:
            print(f"❌ Traffic analytics connection test failed: {e}")
            return False 
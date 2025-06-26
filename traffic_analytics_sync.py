#!/usr/bin/env python3
"""
Traffic Analytics Sync - Traffic and conversion analytics extraction and Notion integration
Syncs traffic session data and conversion metrics to Notion database
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.traffic_analytics_extractor import TrafficAnalyticsExtractor
from src.loaders.traffic_notion_loader import TrafficNotionLoader

class TrafficAnalyticsSync:
    """Sync traffic analytics data from available sources to Notion"""
    
    def __init__(self):
        self.extractor = TrafficAnalyticsExtractor()
        self.loader = TrafficNotionLoader()
    
    def sync_single_date(self, date: datetime = None) -> bool:
        """Sync traffic sessions for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"🚗 Syncing traffic analytics for {date_str}")
        
        try:
            # Extract traffic session data
            print("🔍 Extracting traffic sessions from order data...")
            sessions_data = self.extractor.extract_single_date(date)
            
            if not sessions_data:
                print(f"ℹ️  No traffic sessions found for {date_str}")
                return True
            
            print(f"✅ Extracted {len(sessions_data)} traffic sessions")
            
            # Load into Notion
            print("📝 Loading traffic sessions into Notion...")
            results = self.loader.load_sessions_batch(sessions_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate traffic summary metrics
            total_sessions = len(sessions_data)
            converted_sessions = sum(1 for session in sessions_data if session.get('converted'))
            conversion_rate = (converted_sessions / total_sessions * 100) if total_sessions > 0 else 0
            total_revenue = sum(session.get('order_value', 0) for session in sessions_data)
            avg_order_value = total_revenue / converted_sessions if converted_sessions > 0 else 0
            
            # Traffic source breakdown
            sources = {}
            for session in sessions_data:
                source = session.get('traffic_source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            # Device breakdown  
            devices = {}
            for session in sessions_data:
                device = session.get('device_type', 'unknown')
                devices[device] = devices.get(device, 0) + 1
            
            print(f"   📊 Traffic Summary:")
            print(f"        Total Sessions: {total_sessions}")
            print(f"        Converted: {converted_sessions} ({conversion_rate:.1f}%)")
            print(f"        Revenue: ${total_revenue:.2f}")
            print(f"        AOV: ${avg_order_value:.2f}")
            print(f"        Top Sources: {dict(list(sources.items())[:3])}")
            print(f"        Devices: {devices}")
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"🎉 Successfully synced traffic analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing traffic analytics for {date_str}: {e}")
            return False
    
    def sync_date_range(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Sync traffic sessions for a date range"""
        if end_date is None:
            end_date = start_date
        
        print(f"🚗 Syncing traffic analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\n📅 Processing {date_str}")
            
            try:
                # Extract sessions for this date
                sessions_data = self.extractor.extract_single_date(current_date)
                
                if sessions_data:
                    # Load into Notion
                    results = self.loader.load_sessions_batch(sessions_data, skip_if_exists=True)
                    total_successful += results['successful']
                    total_failed += results['failed']
                    total_skipped += results['skipped']
                else:
                    print(f"ℹ️  No traffic sessions found for {date_str}")
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing {date_str}: {e}")
                total_failed += 1
            
            current_date += timedelta(days=1)
        
        print(f"\n🎉 Date range sync completed!")
        print(f"   ✅ Total successful: {total_successful}")
        print(f"   ⏭️  Total skipped: {total_skipped}")
        print(f"   ❌ Total failed: {total_failed}")
        
        return {
            'successful': total_successful,
            'failed': total_failed,
            'skipped': total_skipped
        }
    
    def backfill_traffic(self, days_back: int = 30) -> Dict:
        """Backfill traffic sessions for the last N days"""
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back - 1)
        
        print(f"🔄 Backfilling traffic analytics for last {days_back} days")
        return self.sync_date_range(start_date, end_date)
    
    def test_system(self) -> bool:
        """Test the entire traffic analytics system"""
        print("🧪 Testing Traffic Analytics System")
        print("=" * 50)
        
        # Test Shopify connection
        print("1️⃣ Testing Shopify connection...")
        if self.extractor.test_connection():
            print("   ✅ Shopify connection successful")
        else:
            print("   ❌ Shopify connection failed")
            return False
        
        # Test Notion connection
        print("2️⃣ Testing Notion Traffic Analytics database...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing traffic data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        sessions_data = self.extractor.extract_single_date(test_date)
        
        if sessions_data:
            print(f"   ✅ Successfully extracted {len(sessions_data)} traffic sessions")
            
            # Show sample data
            if sessions_data:
                sample = sessions_data[0]
                print(f"   🚗 Sample session:")
                print(f"        Source: {sample.get('traffic_source', 'unknown')}")
                print(f"        Device: {sample.get('device_type', 'unknown')}")
                print(f"        Duration: {sample.get('session_duration', 0)}s")
                print(f"        Pages: {sample.get('pages_viewed', 0)}")
                print(f"        Converted: {'Yes' if sample.get('converted') else 'No'}")
                if sample.get('converted'):
                    print(f"        Order Value: ${sample.get('order_value', 0):.2f}")
        else:
            print(f"   ℹ️  No traffic sessions found for test date {test_date.strftime('%Y-%m-%d')}")
            print(f"   ⚠️  Note: Traffic data is derived from order data. No orders = No sessions.")
        
        print("✅ System test completed successfully")
        return True

def main():
    """Main function"""
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        sys.exit(1)
    
    sync = TrafficAnalyticsSync()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = sync.test_system()
            sys.exit(0 if success else 1)
        
        elif command == 'backfill':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            results = sync.backfill_traffic(days)
            sys.exit(0 if results['failed'] == 0 else 1)
        
        elif command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                success = sync.sync_single_date(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python traffic_analytics_sync.py                # Yesterday's traffic")
            print("   python traffic_analytics_sync.py test           # Test system")
            print("   python traffic_analytics_sync.py 2025-06-25     # Specific date")
            print("   python traffic_analytics_sync.py backfill [30]  # Backfill last N days")
            sys.exit(1)
    
    else:
        # Default: sync yesterday's traffic
        success = sync.sync_single_date()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
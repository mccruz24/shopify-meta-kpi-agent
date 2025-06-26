#!/usr/bin/env python3
"""
Orders Analytics Sync - Comprehensive order data extraction and Notion integration
Syncs detailed order analytics data to Notion database
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.orders_analytics_extractor import OrdersAnalyticsExtractor
from src.loaders.orders_notion_loader import OrdersNotionLoader

class OrdersAnalyticsSync:
    """Sync orders analytics data from Shopify to Notion"""
    
    def __init__(self):
        self.extractor = OrdersAnalyticsExtractor()
        self.loader = OrdersNotionLoader()
    
    def sync_single_date(self, date: datetime = None) -> bool:
        """Sync orders for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"📊 Syncing orders analytics for {date_str}")
        
        try:
            # Extract orders data
            print("🔍 Extracting orders from Shopify...")
            orders_data = self.extractor.extract_single_date(date)
            
            if not orders_data:
                print(f"ℹ️  No orders found for {date_str}")
                return True
            
            print(f"✅ Extracted {len(orders_data)} orders")
            
            # Load into Notion
            print("📝 Loading orders into Notion...")
            results = self.loader.load_orders_batch(orders_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            if failed == 0:
                print(f"🎉 Successfully synced {date_str}: {successful} new, {skipped} existing")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing orders for {date_str}: {e}")
            return False
    
    def sync_date_range(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Sync orders for a date range"""
        if end_date is None:
            end_date = start_date
        
        print(f"📊 Syncing orders analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\n📅 Processing {date_str}")
            
            try:
                # Extract orders for this date
                orders_data = self.extractor.extract_single_date(current_date)
                
                if orders_data:
                    # Load into Notion
                    results = self.loader.load_orders_batch(orders_data, skip_if_exists=True)
                    total_successful += results['successful']
                    total_failed += results['failed']
                    total_skipped += results['skipped']
                else:
                    print(f"ℹ️  No orders found for {date_str}")
                
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
    
    def backfill_orders(self, days_back: int = 30) -> Dict:
        """Backfill orders for the last N days"""
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back - 1)
        
        print(f"🔄 Backfilling orders for last {days_back} days")
        return self.sync_date_range(start_date, end_date)
    
    def test_system(self) -> bool:
        """Test the entire system"""
        print("🧪 Testing Orders Analytics System")
        print("=" * 50)
        
        # Test Shopify connection
        print("1️⃣ Testing Shopify connection...")
        if self.extractor.test_connection():
            print("   ✅ Shopify connection successful")
        else:
            print("   ❌ Shopify connection failed")
            return False
        
        # Test Notion connection
        print("2️⃣ Testing Notion connection...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        orders_data = self.extractor.extract_single_date(test_date)
        
        if orders_data:
            print(f"   ✅ Successfully extracted {len(orders_data)} orders")
            
            # Show sample data
            if orders_data:
                sample = orders_data[0]
                print(f"   📊 Sample order: #{sample.get('order_number')} - ${sample.get('total_revenue', 0):.2f}")
        else:
            print(f"   ℹ️  No orders found for test date {test_date.strftime('%Y-%m-%d')}")
        
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
    
    sync = OrdersAnalyticsSync()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = sync.test_system()
            sys.exit(0 if success else 1)
        
        elif command == 'backfill':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            results = sync.backfill_orders(days)
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
            print("   python orders_analytics_sync.py                # Yesterday's orders")
            print("   python orders_analytics_sync.py test           # Test system")
            print("   python orders_analytics_sync.py 2025-06-25     # Specific date")
            print("   python orders_analytics_sync.py backfill [30]  # Backfill last N days")
            sys.exit(1)
    
    else:
        # Default: sync yesterday's orders
        success = sync.sync_single_date()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
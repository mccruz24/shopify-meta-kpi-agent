#!/usr/bin/env python3
"""
Printify Analytics Sync - Comprehensive Printify analytics extraction and Notion integration
Syncs cash flow, order management, and product performance data to Notion database
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.printify_analytics_extractor import PrintifyAnalyticsExtractor
from src.loaders.printify_notion_loader import PrintifyNotionLoader

class PrintifyAnalyticsSync:
    """Sync comprehensive Printify analytics data to Notion"""
    
    def __init__(self, database_id: str = None):
        self.extractor = PrintifyAnalyticsExtractor()
        self.loader = PrintifyNotionLoader()
        
        if database_id:
            self.loader.set_database_id(database_id)
    
    def set_database_id(self, database_id: str):
        """Set the Notion database ID for Printify Analytics"""
        self.loader.set_database_id(database_id)
    
    def sync_single_date(self, date: datetime = None) -> bool:
        """Sync Printify analytics for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"🖨️  Syncing Printify analytics for {date_str}")
        
        try:
            # Extract analytics data
            print("🔍 Extracting Printify analytics data...")
            analytics_data = self.extractor.extract_single_date(date)
            
            if not analytics_data:
                print(f"ℹ️  No Printify orders found for {date_str}")
                return True
            
            print(f"✅ Extracted {len(analytics_data)} Printify orders")
            
            # Load into Notion
            print("📝 Loading analytics data into Notion...")
            results = self.loader.load_orders_batch(analytics_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate analytics summary
            total_orders = len(analytics_data)
            total_revenue = sum(order.get('total_revenue', 0) for order in analytics_data)
            total_cogs = sum(order.get('total_cogs', 0) for order in analytics_data)
            total_profit = sum(order.get('net_profit', 0) for order in analytics_data)
            avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Status breakdown
            status_counts = {}
            provider_counts = {}
            category_counts = {}
            
            for order in analytics_data:
                status = order.get('status', 'unknown')
                provider = order.get('provider_name', 'unknown')
                category = order.get('primary_category', 'unknown')
                
                status_counts[status] = status_counts.get(status, 0) + 1
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
                category_counts[category] = category_counts.get(category, 0) + 1
            
            print(f"   📊 Analytics Summary:")
            print(f"        Total Orders: {total_orders}")
            print(f"        Total Revenue: ${total_revenue:.2f}")
            print(f"        Total COGS: ${total_cogs:.2f}")
            print(f"        Net Profit: ${total_profit:.2f}")
            print(f"        Avg Margin: {avg_margin:.1f}%")
            print(f"        Order Status: {dict(list(status_counts.items())[:3])}")
            print(f"        Top Providers: {dict(list(provider_counts.items())[:3])}")
            print(f"        Categories: {dict(list(category_counts.items())[:3])}")
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"🎉 Successfully synced Printify analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing Printify analytics for {date_str}: {e}")
            return False
    
    def sync_date_range(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Sync Printify analytics for a date range"""
        if end_date is None:
            end_date = start_date
        
        print(f"🖨️  Syncing Printify analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\\n📅 Processing {date_str}")
            
            try:
                # Extract analytics for this date
                analytics_data = self.extractor.extract_single_date(current_date)
                
                if analytics_data:
                    # Load into Notion
                    results = self.loader.load_orders_batch(analytics_data, skip_if_exists=True)
                    total_successful += results['successful']
                    total_failed += results['failed']
                    total_skipped += results['skipped']
                else:
                    print(f"ℹ️  No Printify orders found for {date_str}")
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing {date_str}: {e}")
                total_failed += 1
            
            current_date += timedelta(days=1)
        
        print(f"\\n🎉 Date range sync completed!")
        print(f"   ✅ Total successful: {total_successful}")
        print(f"   ⏭️  Total skipped: {total_skipped}")
        print(f"   ❌ Total failed: {total_failed}")
        
        return {
            'successful': total_successful,
            'failed': total_failed,
            'skipped': total_skipped
        }
    
    def backfill_analytics(self, days_back: int = 30) -> Dict:
        """Backfill Printify analytics for the last N days"""
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back - 1)
        
        print(f"🔄 Backfilling Printify analytics for last {days_back} days")
        return self.sync_date_range(start_date, end_date)
    
    def test_system(self) -> bool:
        """Test the entire Printify analytics system"""
        print("🧪 Testing Printify Analytics System")
        print("=" * 50)
        
        # Test Printify connection
        print("1️⃣ Testing Printify connection...")
        if self.extractor.test_connection():
            print("   ✅ Printify connection successful")
        else:
            print("   ❌ Printify connection failed")
            return False
        
        # Test Notion connection
        print("2️⃣ Testing Notion Printify Analytics database...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            print("   💡 Make sure to set database ID first")
            return False
        
        # Test data extraction
        print("3️⃣ Testing Printify data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        analytics_data = self.extractor.extract_single_date(test_date)
        
        if analytics_data:
            print(f"   ✅ Successfully extracted {len(analytics_data)} analytics records")
            
            # Show sample data
            if analytics_data:
                sample = analytics_data[0]
                print(f"   🖨️  Sample order:")
                print(f"        Order ID: {sample.get('order_id', 'unknown')}")
                print(f"        Status: {sample.get('status', 'unknown')}")
                print(f"        Revenue: ${sample.get('total_revenue', 0):.2f}")
                print(f"        COGS: ${sample.get('total_cogs', 0):.2f}")
                print(f"        Profit: ${sample.get('net_profit', 0):.2f}")
                print(f"        Margin: {sample.get('net_margin', 0):.1f}%")
                print(f"        Provider: {sample.get('provider_name', 'unknown')}")
                print(f"        Category: {sample.get('primary_category', 'unknown')}")
        else:
            print(f"   ℹ️  No Printify orders found for test date {test_date.strftime('%Y-%m-%d')}")
            print(f"   ⚠️  Note: This is normal if no orders were placed on that date")
        
        print("✅ System test completed successfully")
        return True

def main():
    """Main function"""
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('PRINTIFY_API_TOKEN'):
        print("❌ PRINTIFY_API_TOKEN not found in environment")
        sys.exit(1)
    
    # Get database ID from environment
    database_id = os.getenv('PRINTIFY_ANALYTICS_DB_ID')
    sync = PrintifyAnalyticsSync(database_id)
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = sync.test_system()
            sys.exit(0 if success else 1)
        
        elif command == 'set-db':
            if len(sys.argv) > 2:
                database_id = sys.argv[2]
                sync.set_database_id(database_id)
                print(f"✅ Database ID set to: {database_id}")
                print("💡 Now you can run: python printify_analytics_sync.py test")
                sys.exit(0)
            else:
                print("❌ Please provide database ID")
                print("💡 Usage: python printify_analytics_sync.py set-db YOUR_DATABASE_ID")
                sys.exit(1)
        
        elif command == 'backfill':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            database_id = sys.argv[3] if len(sys.argv) > 3 else None
            
            if database_id:
                sync.set_database_id(database_id)
            
            results = sync.backfill_analytics(days)
            sys.exit(0 if results['failed'] == 0 else 1)
        
        elif command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                database_id = sys.argv[2] if len(sys.argv) > 2 else None
                
                if database_id:
                    sync.set_database_id(database_id)
                
                success = sync.sync_single_date(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python printify_analytics_sync.py set-db DATABASE_ID     # Set database ID")
            print("   python printify_analytics_sync.py test                    # Test system")
            print("   python printify_analytics_sync.py 2025-06-25 DATABASE_ID # Specific date")
            print("   python printify_analytics_sync.py backfill [30] DB_ID    # Backfill last N days")
            sys.exit(1)
    
    else:
        print("💡 Printify Analytics Sync")
        print("   First, set your database ID:")
        print("   python printify_analytics_sync.py set-db YOUR_DATABASE_ID")
        print("   Then test the system:")
        print("   python printify_analytics_sync.py test")
        sys.exit(0)

if __name__ == "__main__":
    main()
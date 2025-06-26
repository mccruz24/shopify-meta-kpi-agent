#!/usr/bin/env python3
"""
Orders Analytics Scheduler - Automated daily order analytics collection
Designed to run on a schedule (cron job) to automatically collect detailed order analytics
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

class OrdersAnalyticsScheduler:
    """Automated daily order analytics collection for scheduled runs"""
    
    def __init__(self):
        # Initialize extractors and loaders
        self.extractor = OrdersAnalyticsExtractor()
        self.loader = OrdersNotionLoader()
    
    def collect_daily_orders(self, target_date: datetime = None) -> bool:
        """Collect and store daily order analytics for the target date"""
        
        # Default to yesterday if no date specified
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        print(f"🤖 [SCHEDULED] Collecting Order Analytics for {date_str}")
        
        try:
            # Extract orders data from Shopify
            print(f"   🛍️  Extracting orders from Shopify...")
            orders_data = self.extractor.extract_single_date(target_date)
            
            if not orders_data:
                print(f"   ℹ️  No orders found for {date_str}")
                return True
            
            print(f"   ✅ Extracted {len(orders_data)} orders")
            
            # Load into Notion Orders Analytics database
            print(f"   📝 Loading orders into Notion...")
            results = self.loader.load_orders_batch(orders_data, skip_if_exists=True)
            
            # Summary for logs
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate summary metrics
            total_revenue = sum(order.get('total_revenue', 0) for order in orders_data)
            total_orders = len(orders_data)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            print(f"   📊 Summary: {total_orders} orders, ${total_revenue:.2f} revenue, ${avg_order_value:.2f} AOV")
            print(f"   💾 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"✅ Successfully synced orders analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error collecting orders analytics for {date_str}: {e}")
            return False
    
    def test_system(self) -> bool:
        """Test the entire orders analytics system"""
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
        print("2️⃣ Testing Notion Orders Analytics database...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing order data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        orders_data = self.extractor.extract_single_date(test_date)
        
        if orders_data:
            print(f"   ✅ Successfully extracted {len(orders_data)} orders")
            
            # Show sample data
            if orders_data:
                sample = orders_data[0]
                print(f"   📊 Sample: Order #{sample.get('order_number')} - ${sample.get('total_revenue', 0):.2f}")
                print(f"        Customer: {sample.get('customer_name', 'N/A')}")
                print(f"        Location: {sample.get('city', 'N/A')}, {sample.get('country', 'N/A')}")
        else:
            print(f"   ℹ️  No orders found for test date {test_date.strftime('%Y-%m-%d')}")
        
        print("✅ System test completed successfully")
        return True

def main():
    """Main function for scheduled execution"""
    
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        sys.exit(1)
    
    scheduler = OrdersAnalyticsScheduler()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = scheduler.test_system()
            sys.exit(0 if success else 1)
        
        elif command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                success = scheduler.collect_daily_orders(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                print("💡 Usage:")
                print("   python orders_analytics_scheduler.py           # Yesterday's orders")
                print("   python orders_analytics_scheduler.py test      # Test system")
                print("   python orders_analytics_scheduler.py 2025-06-25 # Specific date")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python orders_analytics_scheduler.py           # Yesterday's orders")
            print("   python orders_analytics_scheduler.py test      # Test system")
            print("   python orders_analytics_scheduler.py 2025-06-25 # Specific date")
            sys.exit(1)
    
    else:
        # Default: collect yesterday's orders
        success = scheduler.collect_daily_orders()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
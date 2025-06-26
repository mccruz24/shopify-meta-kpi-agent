#!/usr/bin/env python3
"""
Simple Notion integration - Daily KPIs only
Start with this, then expand to other databases
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.shopify_extractor import ShopifyExtractor
from src.extractors.meta_extractor import MetaExtractor
from src.extractors.printify_extractor import PrintifyExtractor

class SimpleNotionKPI:
    """Simple Notion integration for daily KPIs only"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.daily_kpis_db = os.getenv('NOTION_DAILY_KPIS_DB')
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # API extractors
        self.shopify = ShopifyExtractor()
        self.meta = MetaExtractor()
        self.printify = PrintifyExtractor()
    
    def check_date_exists(self, date: datetime) -> bool:
        """Check if date already exists in Notion database"""
        try:
            date_title = f"KPIs for {date.strftime('%B %d, %Y')}"
            url = f"https://api.notion.com/v1/databases/{self.daily_kpis_db}/query"
            data = {
                "filter": {
                    "property": "ID",
                    "title": {
                        "equals": date_title
                    }
                }
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code == 200:
                results = response.json().get('results', [])
                return len(results) > 0
            return False
        except Exception as e:
            print(f"⚠️  Could not check if date exists: {e}")
            return False

    def add_daily_kpis(self, date: datetime = None, delay_seconds: int = 2, skip_if_exists: bool = False):
        """Add daily KPIs to Notion database"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        print(f"📊 Processing KPIs for {date.strftime('%Y-%m-%d')}")
        
        # Check if date already exists
        if skip_if_exists and self.check_date_exists(date):
            print(f"⏭️  Skipping {date.strftime('%Y-%m-%d')} - already exists in Notion")
            return True
        
        # Extract data with delays between API calls
        print(f"   🛍️  Fetching Shopify data...")
        shopify_data = self.shopify.get_daily_sales_data(date)
        time.sleep(delay_seconds)  # Rate limiting delay
        
        print(f"   📱 Fetching Meta data...")
        meta_data = self.meta.get_daily_ad_data(date)
        time.sleep(delay_seconds)  # Rate limiting delay
        
        print(f"   🖨️  Fetching Printify data...")
        printify_data = self.printify.get_daily_costs(date)
        time.sleep(delay_seconds)  # Rate limiting delay
        
        # Prepare Notion page properties - using ACTUAL available fields
        properties = {
            "ID": {
                "title": [{"text": {"content": f"KPIs for {date.strftime('%B %d, %Y')}"}}]
            },
            "Shopify Sales": {
                "number": shopify_data.get('shopify_gross_sales', 0)  # ✅ Available
            },
            "Shopify Shipping": {
                "number": shopify_data.get('shopify_shipping', 0)  # ✅ Available
            },
            "Shopify Orders": {
                "number": shopify_data.get('total_orders', 0)  # ✅ Now available
            },
            "Shopify AOV": {
                "number": shopify_data.get('aov', 0)  # ✅ Now available
            },
            "New Customers": {
                "number": shopify_data.get('new_customers', 0)  # ✅ Now available
            },
            "Returning Customers": {
                "number": shopify_data.get('returning_customers', 0)  # ✅ Now available
            },
            "Meta Ad Spend": {
                "number": meta_data.get('meta_ad_spend', 0)  # ✅ Available
            },
            "Meta Impressions": {
                "number": meta_data.get('impressions', 0)  # ✅ Now available
            },
            "Meta Clicks": {
                "number": meta_data.get('clicks', 0)  # ✅ Now available
            },
            "Meta CTR": {
                "number": meta_data.get('ctr', 0)  # ✅ Now available
            },
            "Meta CPC": {
                "number": meta_data.get('cpc', 0)  # ✅ Now available
            },
            "Meta ROAS": {
                "number": meta_data.get('roas', 0)  # ✅ Now available
            },
            "Printify COGS": {
                "number": printify_data.get('printify_charge', 0)  # ✅ Available
            }
        }
        
        # Create page in Notion
        try:
            url = "https://api.notion.com/v1/pages"
            data = {
                "parent": {"database_id": self.daily_kpis_db},
                "properties": properties
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print("✅ Successfully added KPIs to Notion!")
                
                # Show summary of what was added
                print(f"\n📊 Added to Notion:")
                print(f"   🛍️  Shopify Sales: ${shopify_data.get('shopify_gross_sales', 0):.2f}")
                print(f"   🛍️  Shopify Orders: {shopify_data.get('total_orders', 0)}")
                print(f"   🛍️  Shopify AOV: ${shopify_data.get('aov', 0):.2f}")
                print(f"   🛍️  New Customers: {shopify_data.get('new_customers', 0)}")
                print(f"   🛍️  Returning Customers: {shopify_data.get('returning_customers', 0)}")
                print(f"   📱 Meta Ad Spend: €{meta_data.get('meta_ad_spend', 0):.2f}")
                print(f"   📱 Meta Impressions: {meta_data.get('impressions', 0):,}")
                print(f"   📱 Meta Clicks: {meta_data.get('clicks', 0):,}")
                print(f"   📱 Meta CTR: {meta_data.get('ctr', 0):.2f}%")
                print(f"   📱 Meta CPC: €{meta_data.get('cpc', 0):.2f}")
                print(f"   📱 Meta ROAS: {meta_data.get('roas', 0):.2f}")
                print(f"   🖨️  Printify COGS: ${printify_data.get('printify_charge', 0):.2f}")
                
                # Calculate and show profit
                profit = shopify_data.get('shopify_gross_sales', 0) - meta_data.get('meta_ad_spend', 0) - printify_data.get('printify_charge', 0)
                print(f"   💰 Calculated Profit: ${profit:.2f}")
                
                return True
            else:
                print(f"❌ Notion API error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding to Notion: {e}")
            return False
    
    def backfill_kpis(self, start_date: datetime, end_date: datetime, delay_seconds: int = 3, skip_existing: bool = True):
        """Backfill KPIs for a date range"""
        print(f"🔄 Starting backfill from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        successful = 0
        failed = 0
        skipped = 0
        
        print(f"📋 Total days to process: {total_days}")
        print(f"⚙️  Skip existing entries: {skip_existing}")
        print(f"⏱️  Delay between API calls: {delay_seconds}s")
        print(f"⏱️  Delay between days: {delay_seconds + 2}s")
        
        while current_date <= end_date:
            day_number = (current_date - start_date).days + 1
            print(f"\n📅 Day {day_number}/{total_days}: {current_date.strftime('%Y-%m-%d')}")
            
            try:
                # Check if already exists first
                if skip_existing and self.check_date_exists(current_date):
                    skipped += 1
                    print(f"⏭️  Already exists in Notion - skipping")
                else:
                    success = self.add_daily_kpis(current_date, delay_seconds, skip_if_exists=False)
                    if success:
                        successful += 1
                        print(f"✅ Successfully added to Notion")
                    else:
                        failed += 1
                        print(f"❌ Failed to add to Notion")
                
                # Extra delay between days to be extra safe with rate limits
                if current_date < end_date:  # Don't delay after the last day
                    print(f"⏳ Waiting {delay_seconds + 2} seconds before next day...")
                    time.sleep(delay_seconds + 2)
                    
            except Exception as e:
                failed += 1
                print(f"❌ Unexpected error: {str(e)}")
                print(f"⏳ Waiting {delay_seconds + 5} seconds after error...")
                time.sleep(delay_seconds + 5)
            
            current_date += timedelta(days=1)
        
        print(f"\n🎉 Backfill completed!")
        print(f"   ✅ Successfully added: {successful} days")
        print(f"   ⏭️  Skipped (already existed): {skipped} days") 
        print(f"   ❌ Failed: {failed} days")
        print(f"   📊 Total processed: {successful + skipped + failed}/{total_days} days")
        
        if failed > 0:
            print(f"\n⚠️  {failed} days failed. You may want to re-run the backfill to retry failed days.")
        
        return successful, failed, skipped

def test_api_filters():
    """Test different API filter combinations to find orders"""
    from src.extractors.shopify_extractor import ShopifyExtractor
    
    shopify = ShopifyExtractor()
    test_date = datetime(2024, 6, 25)  # Test June 25th since we know there should be data
    
    print("🧪 Testing different API filter combinations:")
    print("=" * 60)
    
    start_date = test_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    # Test 1: No filters (get ALL recent orders)
    print(f"\n1️⃣ Testing: NO FILTERS (recent orders)")
    orders_data = shopify._make_request('orders.json', {'limit': 10})
    if orders_data and orders_data.get('orders'):
        orders = orders_data['orders']
        print(f"   ✅ Found {len(orders)} recent orders")
        for i, order in enumerate(orders[:3]):
            created_at = order.get('created_at', 'Unknown')
            status = order.get('financial_status', 'Unknown')
            order_status = order.get('fulfillment_status', 'Unknown')
            total = order.get('total_price', '0')
            print(f"      Order {i+1}: Created={created_at}, Financial={status}, Status={order_status}, Total=${total}")
    else:
        print(f"   ❌ No orders found")
    
    # Test 2: Only date filter
    print(f"\n2️⃣ Testing: ONLY DATE FILTER")
    orders_data = shopify._make_request('orders.json', {
        'created_at_min': start_date.isoformat(),
        'created_at_max': end_date.isoformat(),
        'limit': 50
    })
    if orders_data and orders_data.get('orders'):
        orders = orders_data['orders']
        print(f"   ✅ Found {len(orders)} orders for date range")
        for i, order in enumerate(orders[:3]):
            created_at = order.get('created_at', 'Unknown')
            status = order.get('financial_status', 'Unknown')
            total = order.get('total_price', '0')
            print(f"      Order {i+1}: Created={created_at}, Financial={status}, Total=${total}")
    else:
        print(f"   ❌ No orders found for date range")
    
    # Test 3: Different financial status values
    print(f"\n3️⃣ Testing: DIFFERENT FINANCIAL STATUS")
    financial_statuses = ['paid', 'pending', 'authorized', 'partially_paid', 'refunded', 'voided']
    
    for financial_status in financial_statuses:
        orders_data = shopify._make_request('orders.json', {
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'financial_status': financial_status,
            'limit': 10
        })
        if orders_data and orders_data.get('orders'):
            count = len(orders_data['orders'])
            print(f"   ✅ Financial status '{financial_status}': {count} orders")
        else:
            print(f"   ❌ Financial status '{financial_status}': 0 orders")

def main():
    """Main function"""
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in .env")
        print("📋 Setup steps:")
        print("1. Go to https://www.notion.so/my-integrations")
        print("2. Create integration and copy token")
        print("3. Add to .env: NOTION_TOKEN=your_token")
        print("4. Create 'Daily KPIs' database in Notion")
        print("5. Share database with your integration") 
        print("6. Add database ID to .env: NOTION_DAILY_KPIS_DB=database_id")
        return
    
    if not os.getenv('NOTION_DAILY_KPIS_DB'):
        print("❌ NOTION_DAILY_KPIS_DB not found in .env")
        print("📋 Create the 'Daily KPIs' database first!")
        return
    
    # Check for test command
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_api_filters()
        return
    
    notion = SimpleNotionKPI()
    
    # Check for backfill command
    if len(sys.argv) > 1 and sys.argv[1] in ['backfill', 'backfill-force']:
        force_mode = sys.argv[1] == 'backfill-force'
        
        print("🔄 Starting backfill mode...")
        print("📅 Date range: May 1, 2025 to June 25, 2025")
        if force_mode:
            print("⚠️  FORCE MODE: Will overwrite existing entries")
        else:
            print("⚙️  SMART MODE: Will skip existing entries")
        
        # Define date range
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 6, 25)
        
        # Confirm with user (in a real scenario)
        print("⚠️  This will process 56 days of data with rate limiting delays.")
        print("⏱️  Estimated time: ~15-20 minutes")
        print("🚀 Starting backfill in 5 seconds... (Ctrl+C to cancel)")
        
        try:
            time.sleep(5)
            notion.backfill_kpis(start_date, end_date, delay_seconds=3, skip_existing=not force_mode)
        except KeyboardInterrupt:
            print("\n❌ Backfill cancelled by user")
            return
    
    # Run for specific date
    elif len(sys.argv) > 1:
        try:
            date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
            notion.add_daily_kpis(date)
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            print("💡 Usage:")
            print("   python simple_daily_kpi.py                    # Yesterday's data")
            print("   python simple_daily_kpi.py 2025-06-25         # Specific date")
            print("   python simple_daily_kpi.py backfill           # Backfill May 1-June 25 (skip existing)")
            print("   python simple_daily_kpi.py backfill-force     # Backfill May 1-June 25 (overwrite all)")
    
    # Run for yesterday (default)
    else:
        notion.add_daily_kpis()

if __name__ == "__main__":
    main()
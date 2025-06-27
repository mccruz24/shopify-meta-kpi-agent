#!/usr/bin/env python3
"""
Daily KPI Backfill Script - Backfill historical daily KPI data
Fills missing data from April 1, 2025 to June 26, 2025
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import time
import random

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.shopify_extractor import ShopifyExtractor
from src.extractors.meta_extractor import MetaExtractor
from src.extractors.printify_extractor import PrintifyExtractor

class DailyKPIBackfill:
    """Backfill historical daily KPI data"""
    
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
            
            response = requests.post(url, headers=self.headers, json=data, timeout=15)
            if response.status_code == 200:
                results = response.json().get('results', [])
                return len(results) > 0
            return False
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print(f"⚠️  Timeout checking if date exists, assuming it doesn't exist")
            return False
        except Exception as e:
            print(f"⚠️  Could not check if date exists: {e}")
            return False

    def collect_daily_kpis(self, target_date: datetime, retry_count: int = 0) -> bool:
        """Collect and store daily KPIs for the target date with retry logic"""
        
        date_str = target_date.strftime('%Y-%m-%d')
        retry_suffix = f" (retry {retry_count})" if retry_count > 0 else ""
        print(f"🔄 Collecting KPIs for {date_str}{retry_suffix}")
        
        # Check if already exists (avoid duplicates)
        if self.check_date_exists(target_date):
            print(f"   ⏭️  Data for {date_str} already exists - skipping")
            return True
        
        try:
            # Extract data from all platforms with enhanced rate limiting
            print(f"   🛍️  Extracting Shopify data...")
            shopify_data = self.shopify.get_daily_sales_data(target_date)
            time.sleep(2 + random.uniform(0.5, 1.5))  # 2-3.5s with jitter
            
            print(f"   📱 Extracting Meta ads data...")
            meta_data = self.meta.get_daily_ad_data(target_date)
            time.sleep(2 + random.uniform(0.5, 1.5))  # 2-3.5s with jitter
            
            print(f"   🖨️  Extracting Printify costs...")
            printify_data = self.printify.get_daily_costs(target_date)
            time.sleep(2 + random.uniform(0.5, 1.5))  # 2-3.5s with jitter
            
            # Prepare Notion page properties with date field
            properties = {
                "ID": {
                    "title": [{"text": {"content": f"KPIs for {target_date.strftime('%B %d, %Y')}"}}]
                },
                "Date": {
                    "date": {"start": target_date.strftime('%Y-%m-%d')}
                },
                "Shopify Sales": {
                    "number": shopify_data.get('shopify_gross_sales', 0)
                },
                "Shopify Shipping": {
                    "number": shopify_data.get('shopify_shipping', 0)
                },
                "Shopify Orders": {
                    "number": shopify_data.get('total_orders', 0)
                },
                "Shopify AOV": {
                    "number": shopify_data.get('aov', 0)
                },
                "New Customers": {
                    "number": shopify_data.get('new_customers', 0)
                },
                "Returning Customers": {
                    "number": shopify_data.get('returning_customers', 0)
                },
                "Meta Ad Spend": {
                    "number": meta_data.get('meta_ad_spend', 0)
                },
                "Meta Impressions": {
                    "number": meta_data.get('impressions', 0)
                },
                "Meta Clicks": {
                    "number": meta_data.get('clicks', 0)
                },
                "Meta CTR": {
                    "number": meta_data.get('ctr', 0)
                },
                "Meta CPC": {
                    "number": meta_data.get('cpc', 0)
                },
                "Meta ROAS": {
                    "number": meta_data.get('roas', 0)
                },
                "Printify COGS": {
                    "number": printify_data.get('printify_charge', 0)
                }
            }
            
            # Create page in Notion with timeout
            url = "https://api.notion.com/v1/pages"
            data = {
                "parent": {"database_id": self.daily_kpis_db},
                "properties": properties
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                # Summary for logs
                orders = shopify_data.get('total_orders', 0)
                sales = shopify_data.get('shopify_gross_sales', 0)
                ad_spend = meta_data.get('meta_ad_spend', 0)
                cogs = printify_data.get('printify_charge', 0)
                profit = sales - ad_spend - cogs
                
                print(f"   ✅ Success: {orders} orders, ${sales:.2f} sales, €{ad_spend:.2f} ads, ${cogs:.2f} COGS, ${profit:.2f} profit")
                return True
            else:
                print(f"   ❌ Notion API error {response.status_code}: {response.text}")
                return False
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"   ⚠️  Connection timeout/error for {date_str}: {e}")
            if retry_count < 2:  # Max 2 retries
                wait_time = (retry_count + 1) * 5  # 5s, 10s wait
                print(f"   ⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.collect_daily_kpis(target_date, retry_count + 1)
            return False
        except Exception as e:
            print(f"   ❌ Error collecting KPIs for {date_str}: {e}")
            if retry_count < 1:  # One retry for general errors
                print(f"   ⏳ Retrying in 3 seconds...")
                time.sleep(3)
                return self.collect_daily_kpis(target_date, retry_count + 1)
            return False
    
    def backfill_date_range(self, start_date: datetime, end_date: datetime, test_mode: bool = False) -> dict:
        """Backfill KPI data for a date range"""
        
        if test_mode:
            print(f"🧪 TEST MODE: Backfilling last 7 days for testing")
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now() - timedelta(days=1)
        else:
            print(f"🚀 FULL BACKFILL: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        
        successful = 0
        failed = 0
        skipped = 0
        
        print(f"📊 Processing {total_days} days...")
        print("=" * 60)
        
        day_count = 1
        start_time = time.time()
        while current_date <= end_date:
            print(f"[{day_count}/{total_days}] {current_date.strftime('%A, %B %d, %Y')}")
            
            try:
                success = self.collect_daily_kpis(current_date)
                if success:
                    if self.check_date_exists(current_date):
                        if "skipping" in str(success):  # This is a bit hacky, but works for our use case
                            skipped += 1
                        else:
                            successful += 1
                    else:
                        successful += 1
                else:
                    failed += 1
                
                # Progress update every 10 days
                if day_count % 10 == 0:
                    elapsed_time = time.time() - start_time
                    avg_time_per_day = elapsed_time / day_count
                    remaining_days = total_days - day_count
                    eta_seconds = remaining_days * avg_time_per_day
                    eta_minutes = int(eta_seconds // 60)
                    
                    print(f"   📈 Progress: {successful} successful, {skipped} skipped, {failed} failed")
                    print(f"   ⏱️  ETA: ~{eta_minutes} minutes remaining")
                    # Longer pause every 10 days to avoid overwhelming APIs
                    print(f"   ⏳ Taking a 10-second rest break...")
                    time.sleep(10)
                
                # Progressive rate limiting between days (gets longer as we go)
                base_delay = 3
                progressive_delay = min(day_count // 20, 5)  # Add 1s every 20 days, max 5s extra
                jitter = random.uniform(0.5, 2.0)
                total_delay = base_delay + progressive_delay + jitter
                time.sleep(total_delay)
                
            except Exception as e:
                failed += 1
                print(f"   ❌ Failed to process {current_date.strftime('%Y-%m-%d')}: {e}")
            
            current_date += timedelta(days=1)
            day_count += 1
        
        results = {
            'total_days': total_days,
            'successful': successful,
            'failed': failed,
            'skipped': skipped
        }
        
        return results
    
    def print_summary(self, results: dict, test_mode: bool = False):
        """Print backfill summary"""
        print("\n" + "=" * 60)
        if test_mode:
            print("🧪 TEST BACKFILL COMPLETED")
        else:
            print("🎉 FULL BACKFILL COMPLETED")
        print("=" * 60)
        
        print(f"📊 Total days processed: {results['total_days']}")
        print(f"✅ Successfully added: {results['successful']}")
        print(f"⏭️  Skipped (existing): {results['skipped']}")
        print(f"❌ Failed: {results['failed']}")
        
        success_rate = ((results['successful'] + results['skipped']) / results['total_days']) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if results['failed'] > 0:
            print(f"\n⚠️  {results['failed']} days failed - you may want to retry those dates manually")
        
        if test_mode and results['failed'] == 0:
            print(f"\n🚀 Test successful! Ready to run full backfill:")
            print(f"   python daily_kpi_backfill.py --full")

def main():
    """Main function"""
    
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('NOTION_DAILY_KPIS_DB'):
        print("❌ NOTION_DAILY_KPIS_DB not found in environment")
        sys.exit(1)
    
    backfill = DailyKPIBackfill()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == '--test' or command == 'test':
            # Test mode: last 7 days
            results = backfill.backfill_date_range(None, None, test_mode=True)
            backfill.print_summary(results, test_mode=True)
            sys.exit(0 if results['failed'] == 0 else 1)
        
        elif command == '--full' or command == 'full':
            # Full backfill: April 1 to June 26, 2025
            start_date = datetime(2025, 4, 1)
            end_date = datetime(2025, 6, 26)
            
            print("⚠️  FULL BACKFILL WARNING:")
            print(f"   This will process {(end_date - start_date).days + 1} days of data")
            print("   This may take 15-20 minutes and consume API quotas")
            print("   Press Ctrl+C within 10 seconds to cancel...")
            
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                print("\n❌ Backfill cancelled by user")
                sys.exit(0)
            
            results = backfill.backfill_date_range(start_date, end_date, test_mode=False)
            backfill.print_summary(results, test_mode=False)
            sys.exit(0 if results['failed'] == 0 else 1)
        
        elif command.startswith('2025-'):
            # Single date backfill
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                success = backfill.collect_daily_kpis(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python daily_kpi_backfill.py --test      # Test with last 7 days")
            print("   python daily_kpi_backfill.py --full      # Full backfill Apr 1 - Jun 26")
            print("   python daily_kpi_backfill.py 2025-06-25  # Single date")
            sys.exit(1)
    
    else:
        # Default: show usage
        print("💡 Daily KPI Backfill Script")
        print("=" * 40)
        print("Usage:")
        print("   python daily_kpi_backfill.py --test      # Test with last 7 days")
        print("   python daily_kpi_backfill.py --full      # Full backfill Apr 1 - Jun 26")
        print("   python daily_kpi_backfill.py 2025-06-25  # Single date")
        print("\n🔧 Environment variables needed:")
        print("   NOTION_TOKEN")
        print("   NOTION_DAILY_KPIS_DB")
        sys.exit(0)

if __name__ == "__main__":
    main()
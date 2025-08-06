#!/usr/bin/env python3
"""
Daily KPI Scheduler - Automated daily data collection
Designed to run on a schedule (cron job) to automatically collect daily KPIs
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import time
import random

# Add project root to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)

from src.extractors.shopify_extractor import ShopifyExtractor
from src.extractors.meta_extractor import MetaExtractor
from src.extractors.printify_analytics_extractor import PrintifyAnalyticsExtractor

class DailyKPIScheduler:
    """Automated daily KPI collection for scheduled runs"""
    
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
        self.printify = PrintifyAnalyticsExtractor()
    
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

    def collect_daily_kpis(self, target_date: datetime = None, retry_count: int = 0) -> bool:
        """Collect and store daily KPIs for the target date with retry logic"""
        
        # Default to yesterday if no date specified
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        retry_suffix = f" (retry {retry_count})" if retry_count > 0 else ""
        print(f"🤖 [SCHEDULED] Collecting KPIs for {date_str}{retry_suffix}")
        
        # Check if already exists (avoid duplicates)
        if self.check_date_exists(target_date):
            print(f"✅ Data for {date_str} already exists - skipping")
            return True
        
        try:
            # Extract data from all platforms with enhanced rate limiting
            print(f"   🛍️  Extracting Shopify data...")
            shopify_data = self.shopify.get_daily_sales_data(target_date)
            time.sleep(2 + random.uniform(0.5, 1.0))  # 2-3s with jitter
            
            print(f"   📱 Extracting Meta ads data...")
            meta_data = self.meta.get_daily_ad_data(target_date)
            time.sleep(2 + random.uniform(0.5, 1.0))  # 2-3s with jitter
            
            print(f"   🖨️  Extracting Printify costs...")
            printify_data = self.printify.get_daily_costs(target_date)
            time.sleep(2 + random.uniform(0.5, 1.0))  # 2-3s with jitter
            
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
                print(f"✅ Successfully added KPIs for {date_str} to Notion")
                
                # Summary for logs
                orders = shopify_data.get('total_orders', 0)
                sales = shopify_data.get('shopify_gross_sales', 0)
                ad_spend = meta_data.get('meta_ad_spend', 0)
                cogs = printify_data.get('printify_charge', 0)
                profit = sales - ad_spend - cogs
                
                print(f"   📊 Summary: {orders} orders, ${sales:.2f} sales, €{ad_spend:.2f} ads, ${cogs:.2f} COGS")
                print(f"   💰 Estimated profit: ${profit:.2f}")
                
                return True
            else:
                print(f"❌ Notion API error {response.status_code}: {response.text}")
                return False
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"⚠️  Connection timeout/error for {date_str}: {e}")
            if retry_count < 2:  # Max 2 retries
                wait_time = (retry_count + 1) * 5  # 5s, 10s wait
                print(f"   ⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.collect_daily_kpis(target_date, retry_count + 1)
            return False
        except Exception as e:
            print(f"❌ Error collecting KPIs for {date_str}: {e}")
            if retry_count < 1:  # One retry for general errors
                print(f"   ⏳ Retrying in 3 seconds...")
                time.sleep(3)
                return self.collect_daily_kpis(target_date, retry_count + 1)
            return False

def main():
    """Main function for scheduled execution"""
    
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('NOTION_DAILY_KPIS_DB'):
        print("❌ NOTION_DAILY_KPIS_DB not found in environment")
        sys.exit(1)
    
    scheduler = DailyKPIScheduler()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        # Specific date provided
        try:
            target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
            success = scheduler.collect_daily_kpis(target_date)
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            print("💡 Usage:")
            print("   python daily_kpi_scheduler.py           # Yesterday's data")
            print("   python daily_kpi_scheduler.py 2025-06-25  # Specific date")
            sys.exit(1)
    else:
        # Default: yesterday's data
        success = scheduler.collect_daily_kpis()
    
    # Exit with appropriate code for cron job monitoring
    if success:
        print("🎉 Daily KPI collection completed successfully")
        sys.exit(0)
    else:
        print("💥 Daily KPI collection failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
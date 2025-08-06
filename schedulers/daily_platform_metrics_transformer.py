#!/usr/bin/env python3
"""
Daily Platform Metrics Transformer

This script transforms the daily KPI data from wide format (1 row per day)
to long format (multiple rows per day, one per platform/metric).

Example transformation:
Wide:  Date | Shopify_Sales | Meta_Ad_Spend | Printify_COGS
       2024-01-01 | 1500 | 300 | 450

Long:  Date | Platform | Metric_Type | Amount | Category
       2024-01-01 | Shopify | Revenue | 1500 | Income
       2024-01-01 | Meta | Ad_Spend | 300 | Expense  
       2024-01-01 | Printify | COGS | 450 | Expense
"""

import os
import sys
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import json

# Add project root to path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

from extractors.notion_extractor import NotionExtractor
from loaders.notion_loader import NotionLoader


class DailyKPIDataFetcher:
    """Fetches daily KPI data from existing Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.daily_kpis_db = os.getenv('NOTION_DAILY_KPIS_DB')
        
        if not self.notion_token or not self.daily_kpis_db:
            raise ValueError("Missing required environment variables: NOTION_TOKEN, NOTION_DAILY_KPIS_DB")
    
    def fetch_daily_kpis(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Fetch daily KPI data from Notion database
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional, defaults to start_date)
        
        Returns:
            DataFrame with daily KPI data
        """
        if end_date is None:
            end_date = start_date
            
        headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        # Query to filter by date range
        query = {
            "filter": {
                "and": [
                    {
                        "property": "Date",
                        "date": {
                            "on_or_after": start_date
                        }
                    },
                    {
                        "property": "Date", 
                        "date": {
                            "on_or_before": end_date
                        }
                    }
                ]
            }
        }
        
        url = f"https://api.notion.com/v1/databases/{self.daily_kpis_db}/query"
        
        try:
            response = requests.post(url, headers=headers, json=query)
            response.raise_for_status()
            
            data = response.json()
            records = []
            
            for result in data.get('results', []):
                properties = result.get('properties', {})
                
                # Extract data with proper handling of None values
                record = {
                    'date': self._extract_date(properties.get('Date')),
                    'shopify_sales': self._extract_number(properties.get('Shopify Sales')),
                    'shopify_shipping': self._extract_number(properties.get('Shopify Shipping')),
                    'shopify_orders': self._extract_number(properties.get('Shopify Orders')),
                    'shopify_aov': self._extract_number(properties.get('Shopify AOV')),
                    'new_customers': self._extract_number(properties.get('New Customers')),
                    'returning_customers': self._extract_number(properties.get('Returning Customers')),
                    'meta_ad_spend': self._extract_number(properties.get('Meta Ad Spend')),
                    'meta_impressions': self._extract_number(properties.get('Meta Impressions')),
                    'meta_clicks': self._extract_number(properties.get('Meta Clicks')),
                    'meta_ctr': self._extract_number(properties.get('Meta CTR')),
                    'meta_cpc': self._extract_number(properties.get('Meta CPC')),
                    'meta_roas': self._extract_number(properties.get('Meta ROAS')),
                    'printify_cogs': self._extract_number(properties.get('Printify COGS'))
                }
                records.append(record)
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"❌ Error fetching daily KPIs: {e}")
            return pd.DataFrame()
    
    def _extract_date(self, date_prop) -> str:
        """Extract date from Notion date property"""
        if date_prop and date_prop.get('date') and date_prop['date'].get('start'):
            return date_prop['date']['start'][:10]  # YYYY-MM-DD
        return None
    
    def _extract_number(self, number_prop) -> float:
        """Extract number from Notion number property"""
        if number_prop and number_prop.get('number') is not None:
            return float(number_prop['number'])
        return 0.0


class PlatformMetricsTransformer:
    """Transforms daily KPI data to platform metrics format"""
    
    def __init__(self):
        pass
    
    def transform_to_platform_metrics(self, daily_kpis_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform daily KPI data to platform metrics format
        
        Args:
            daily_kpis_df: DataFrame with daily KPI data
            
        Returns:
            DataFrame in platform metrics format
        """
        if daily_kpis_df.empty:
            return pd.DataFrame()
        
        # Create platform metrics records
        platform_metrics = []
        
        for _, row in daily_kpis_df.iterrows():
            date = row['date']
            
            # Shopify metrics
            if row['shopify_sales'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'Revenue',
                    'amount': row['shopify_sales'],
                    'category': 'Income',
                    'subcategory': 'Sales',
                    'description': 'Gross sales from Shopify orders'
                })
            
            if row['shopify_shipping'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'Shipping',
                    'amount': row['shopify_shipping'],
                    'category': 'Income',
                    'subcategory': 'Shipping',
                    'description': 'Shipping revenue from Shopify orders'
                })
            
            if row['shopify_orders'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'Orders',
                    'amount': row['shopify_orders'],
                    'category': 'Volume',
                    'subcategory': 'Orders',
                    'description': 'Number of Shopify orders'
                })
            
            if row['shopify_aov'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'AOV',
                    'amount': row['shopify_aov'],
                    'category': 'Performance',
                    'subcategory': 'Average',
                    'description': 'Average order value'
                })
            
            # Customer metrics
            if row['new_customers'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'New Customers',
                    'amount': row['new_customers'],
                    'category': 'Customers',
                    'subcategory': 'New',
                    'description': 'Number of new customers'
                })
            
            if row['returning_customers'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Shopify',
                    'metric_type': 'Returning Customers',
                    'amount': row['returning_customers'],
                    'category': 'Customers',
                    'subcategory': 'Returning',
                    'description': 'Number of returning customers'
                })
            
            # Meta metrics
            if row['meta_ad_spend'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'Ad Spend',
                    'amount': row['meta_ad_spend'],
                    'category': 'Expense',
                    'subcategory': 'Advertising',
                    'description': 'Meta ads spending'
                })
            
            if row['meta_impressions'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'Impressions',
                    'amount': row['meta_impressions'],
                    'category': 'Performance',
                    'subcategory': 'Reach',
                    'description': 'Meta ads impressions'
                })
            
            if row['meta_clicks'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'Clicks',
                    'amount': row['meta_clicks'],
                    'category': 'Performance',
                    'subcategory': 'Engagement',
                    'description': 'Meta ads clicks'
                })
            
            if row['meta_ctr'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'CTR',
                    'amount': row['meta_ctr'],
                    'category': 'Performance',
                    'subcategory': 'Rate',
                    'description': 'Click-through rate'
                })
            
            if row['meta_cpc'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'CPC',
                    'amount': row['meta_cpc'],
                    'category': 'Performance',
                    'subcategory': 'Cost',
                    'description': 'Cost per click'
                })
            
            if row['meta_roas'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Meta',
                    'metric_type': 'ROAS',
                    'amount': row['meta_roas'],
                    'category': 'Performance',
                    'subcategory': 'ROI',
                    'description': 'Return on ad spend'
                })
            
            # Printify metrics
            if row['printify_cogs'] > 0:
                platform_metrics.append({
                    'date': date,
                    'platform': 'Printify',
                    'metric_type': 'COGS',
                    'amount': row['printify_cogs'],
                    'category': 'Expense',
                    'subcategory': 'Cost of Goods',
                    'description': 'Cost of goods sold from Printify'
                })
        
        return pd.DataFrame(platform_metrics)


class PlatformMetricsNotionLoader:
    """Loads platform metrics data into Notion database"""
    
    def __init__(self, database_id: str):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.database_id = database_id
        
        if not self.notion_token:
            raise ValueError("Missing required environment variable: NOTION_TOKEN")
        
        self.headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def create_database_if_not_exists(self, parent_page_id: str) -> str:
        """Create platform metrics database if it doesn't exist"""
        # Check if database exists
        try:
            response = requests.get(f"https://api.notion.com/v1/databases/{self.database_id}", headers=self.headers)
            if response.status_code == 200:
                print(f"✅ Platform metrics database already exists: {self.database_id}")
                return self.database_id
        except:
            pass
        
        # Create new database
        database_data = {
            "parent": {"page_id": parent_page_id},
            "title": [{"text": {"content": "Daily Platform Metrics"}}],
            "properties": {
                "Date": {"date": {}},
                "Platform": {"select": {}},
                "Metric Type": {"select": {}},
                "Amount": {"number": {}},
                "Category": {"select": {}},
                "Subcategory": {"select": {}},
                "Description": {"rich_text": {}}
            }
        }
        
        try:
            response = requests.post("https://api.notion.com/v1/databases", headers=self.headers, json=database_data)
            response.raise_for_status()
            
            new_database_id = response.json()['id']
            print(f"✅ Created new platform metrics database: {new_database_id}")
            return new_database_id
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return None
    
    def load_platform_metrics(self, metrics_df: pd.DataFrame) -> int:
        """Load platform metrics data into Notion database"""
        if metrics_df.empty:
            print("ℹ️  No platform metrics to load")
            return 0
        
        successful = 0
        failed = 0
        
        for _, row in metrics_df.iterrows():
            try:
                page_data = {
                    "parent": {"database_id": self.database_id},
                    "properties": {
                        "Date": {"date": {"start": row['date']}},
                        "Platform": {"select": {"name": row['platform']}},
                        "Metric Type": {"select": {"name": row['metric_type']}},
                        "Amount": {"number": row['amount']},
                        "Category": {"select": {"name": row['category']}},
                        "Subcategory": {"select": {"name": row['subcategory']}},
                        "Description": {"rich_text": [{"text": {"content": row['description']}}]}
                    }
                }
                
                response = requests.post("https://api.notion.com/v1/pages", headers=self.headers, json=page_data)
                response.raise_for_status()
                
                successful += 1
                
            except Exception as e:
                print(f"❌ Error loading metric {row['platform']} - {row['metric_type']}: {e}")
                failed += 1
        
        print(f"📊 Loaded {successful} platform metrics, {failed} failed")
        return successful


def main():
    """Main function for scheduled execution"""
    
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('NOTION_DAILY_KPIS_DB'):
        print("❌ NOTION_DAILY_KPIS_DB not found in environment")
        sys.exit(1)
    
    # Parse command line arguments
    target_date = None
    if len(sys.argv) > 1:
        try:
            date_str = sys.argv[1]
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            print(f"📅 Target date specified: {date_str}")
        except ValueError:
            print(f"❌ Invalid date format: {sys.argv[1]}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default to yesterday
        target_date = datetime.now() - timedelta(days=1)
        print(f"📅 Using default date (yesterday): {target_date.strftime('%Y-%m-%d')}")
    
    try:
        # Fetch daily KPIs
        print("📊 Fetching daily KPI data...")
        fetcher = DailyKPIDataFetcher()
        daily_kpis = fetcher.fetch_daily_kpis(target_date.strftime('%Y-%m-%d'))
        
        if daily_kpis.empty:
            print("ℹ️  No daily KPI data found for the specified date")
            sys.exit(0)
        
        print(f"✅ Fetched {len(daily_kpis)} daily KPI records")
        
        # Transform to platform metrics
        print("🔄 Transforming to platform metrics...")
        transformer = PlatformMetricsTransformer()
        platform_metrics = transformer.transform_to_platform_metrics(daily_kpis)
        
        if platform_metrics.empty:
            print("ℹ️  No platform metrics generated")
            sys.exit(0)
        
        print(f"✅ Generated {len(platform_metrics)} platform metrics")
        
        # Load into Notion (if database ID provided)
        platform_metrics_db = os.getenv('PLATFORM_METRICS_DB_ID')
        if platform_metrics_db:
            print("📝 Loading platform metrics into Notion...")
            loader = PlatformMetricsNotionLoader(platform_metrics_db)
            loaded_count = loader.load_platform_metrics(platform_metrics)
            print(f"✅ Successfully loaded {loaded_count} platform metrics")
        else:
            print("ℹ️  PLATFORM_METRICS_DB_ID not set, skipping Notion upload")
            print("📋 Platform metrics preview:")
            print(platform_metrics.head())
        
        print("🎉 Daily platform metrics transformation completed successfully")
        
    except Exception as e:
        print(f"❌ Error during platform metrics transformation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
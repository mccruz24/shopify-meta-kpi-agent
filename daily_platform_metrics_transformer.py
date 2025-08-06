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

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

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
            
            df = pd.DataFrame(records)
            print(f"✅ Fetched {len(df)} daily KPI records from {start_date} to {end_date}")
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data from Notion: {e}")
            raise
    
    def _extract_date(self, date_prop) -> str:
        """Extract date from Notion date property"""
        if date_prop and date_prop.get('date') and date_prop['date'].get('start'):
            return date_prop['date']['start']
        return None
    
    def _extract_number(self, number_prop) -> float:
        """Extract number from Notion number property"""
        if number_prop and number_prop.get('number') is not None:
            return float(number_prop['number'])
        return None


class PlatformMetricsTransformer:
    """Transforms daily KPI data into platform-specific metrics format"""
    
    def __init__(self):
        self.conn = duckdb.connect()
    
    def transform_to_platform_metrics(self, daily_kpis_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform wide-format daily KPIs into long-format platform metrics
        
        Args:
            daily_kpis_df: DataFrame with daily KPI data in wide format
        
        Returns:
            DataFrame with platform metrics in long format
        """
        if daily_kpis_df.empty:
            print("⚠️  No daily KPI data to transform")
            return pd.DataFrame()
        
        # Register DataFrame with DuckDB
        self.conn.register('daily_kpis', daily_kpis_df)
        
        # SQL transformation to convert wide to long format
        sql_query = """
        WITH platform_metrics AS (
            -- Shopify Revenue
            SELECT 
                date,
                'Shopify' as platform,
                'Revenue' as metric_type,
                shopify_sales as amount,
                'Income' as category,
                'USD' as currency,
                'Gross sales revenue' as description
            FROM daily_kpis
            WHERE shopify_sales IS NOT NULL
            
            UNION ALL
            
            -- Shopify Shipping Revenue
            SELECT 
                date,
                'Shopify' as platform,
                'Shipping_Revenue' as metric_type,
                shopify_shipping as amount,
                'Income' as category,
                'USD' as currency,
                'Shipping revenue' as description
            FROM daily_kpis
            WHERE shopify_shipping IS NOT NULL
            
            UNION ALL
            
            -- Shopify Orders (Volume)
            SELECT 
                date,
                'Shopify' as platform,
                'Orders' as metric_type,
                shopify_orders as amount,
                'Volume' as category,
                'Units' as currency,
                'Number of orders' as description
            FROM daily_kpis
            WHERE shopify_orders IS NOT NULL
            
            UNION ALL
            
            -- Shopify AOV
            SELECT 
                date,
                'Shopify' as platform,
                'AOV' as metric_type,
                shopify_aov as amount,
                'Performance' as category,
                'USD' as currency,
                'Average order value' as description
            FROM daily_kpis
            WHERE shopify_aov IS NOT NULL
            
            UNION ALL
            
            -- Meta Ad Spend
            SELECT 
                date,
                'Meta' as platform,
                'Ad_Spend' as metric_type,
                meta_ad_spend as amount,
                'Expense' as category,
                'EUR' as currency,
                'Total advertising spend' as description
            FROM daily_kpis
            WHERE meta_ad_spend IS NOT NULL
            
            UNION ALL
            
            -- Meta Impressions
            SELECT 
                date,
                'Meta' as platform,
                'Impressions' as metric_type,
                meta_impressions as amount,
                'Volume' as category,
                'Units' as currency,
                'Ad impressions' as description
            FROM daily_kpis
            WHERE meta_impressions IS NOT NULL
            
            UNION ALL
            
            -- Meta Clicks
            SELECT 
                date,
                'Meta' as platform,
                'Clicks' as metric_type,
                meta_clicks as amount,
                'Volume' as category,
                'Units' as currency,
                'Ad clicks' as description
            FROM daily_kpis
            WHERE meta_clicks IS NOT NULL
            
            UNION ALL
            
            -- Meta ROAS
            SELECT 
                date,
                'Meta' as platform,
                'ROAS' as metric_type,
                meta_roas as amount,
                'Performance' as category,
                'Ratio' as currency,
                'Return on ad spend' as description
            FROM daily_kpis
            WHERE meta_roas IS NOT NULL
            
            UNION ALL
            
            -- Printify COGS
            SELECT 
                date,
                'Printify' as platform,
                'COGS' as metric_type,
                printify_cogs as amount,
                'Expense' as category,
                'USD' as currency,
                'Cost of goods sold' as description
            FROM daily_kpis
            WHERE printify_cogs IS NOT NULL
            
            UNION ALL
            
            -- Calculated Net Profit (Shopify Revenue - Meta Spend - Printify COGS)
            SELECT 
                date,
                'Calculated' as platform,
                'Net_Profit' as metric_type,
                (COALESCE(shopify_sales, 0) - COALESCE(meta_ad_spend, 0) - COALESCE(printify_cogs, 0)) as amount,
                'Profit' as category,
                'Mixed' as currency,
                'Net profit (Revenue - Ad Spend - COGS)' as description
            FROM daily_kpis
            WHERE shopify_sales IS NOT NULL OR meta_ad_spend IS NOT NULL OR printify_cogs IS NOT NULL
        )
        SELECT 
            date,
            platform,
            metric_type,
            amount,
            category,
            currency,
            description
        FROM platform_metrics
        ORDER BY date DESC, platform, metric_type
        """
        
        try:
            result_df = self.conn.execute(sql_query).fetchdf()
            print(f"✅ Transformed {len(result_df)} platform metric records")
            return result_df
            
        except Exception as e:
            print(f"❌ Error during SQL transformation: {e}")
            raise


class PlatformMetricsNotionLoader:
    """Loads platform metrics data to new Notion database"""
    
    def __init__(self, database_id: str):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.database_id = database_id
        
        if not self.notion_token:
            raise ValueError("Missing NOTION_TOKEN environment variable")
        
        self.headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def create_database_if_not_exists(self, parent_page_id: str) -> str:
        """
        Create the Daily Platform Metrics database if it doesn't exist
        
        Args:
            parent_page_id: ID of the parent page to create database in
            
        Returns:
            Database ID of created or existing database
        """
        database_schema = {
            "parent": {"page_id": parent_page_id},
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Daily Platform Metrics"}
                }
            ],
            "properties": {
                "ID": {"title": {}},
                "Date": {"date": {}},
                "Platform": {
                    "select": {
                        "options": [
                            {"name": "Shopify", "color": "green"},
                            {"name": "Meta", "color": "blue"},
                            {"name": "Printify", "color": "orange"},
                            {"name": "Calculated", "color": "purple"}
                        ]
                    }
                },
                "Metric_Type": {
                    "select": {
                        "options": [
                            {"name": "Revenue", "color": "green"},
                            {"name": "Shipping_Revenue", "color": "green"},
                            {"name": "Orders", "color": "gray"},
                            {"name": "AOV", "color": "yellow"},
                            {"name": "Ad_Spend", "color": "red"},
                            {"name": "Impressions", "color": "gray"},
                            {"name": "Clicks", "color": "gray"},
                            {"name": "ROAS", "color": "yellow"},
                            {"name": "COGS", "color": "red"},
                            {"name": "Net_Profit", "color": "purple"}
                        ]
                    }
                },
                "Amount": {"number": {"format": "number_with_commas"}},
                "Category": {
                    "select": {
                        "options": [
                            {"name": "Income", "color": "green"},
                            {"name": "Expense", "color": "red"},
                            {"name": "Volume", "color": "gray"},
                            {"name": "Performance", "color": "yellow"},
                            {"name": "Profit", "color": "purple"}
                        ]
                    }
                },
                "Currency": {
                    "select": {
                        "options": [
                            {"name": "USD", "color": "blue"},
                            {"name": "EUR", "color": "orange"},
                            {"name": "Units", "color": "gray"},
                            {"name": "Ratio", "color": "yellow"},
                            {"name": "Mixed", "color": "purple"}
                        ]
                    }
                },
                "Description": {"rich_text": {}}
            }
        }
        
        try:
            url = "https://api.notion.com/v1/databases"
            response = requests.post(url, headers=self.headers, json=database_schema)
            
            if response.status_code == 200:
                database_id = response.json()['id']
                print(f"✅ Created Daily Platform Metrics database: {database_id}")
                return database_id
            else:
                print(f"❌ Error creating database: {response.text}")
                raise Exception(f"Failed to create database: {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            raise
    
    def load_platform_metrics(self, metrics_df: pd.DataFrame) -> int:
        """
        Load platform metrics data to Notion database
        
        Args:
            metrics_df: DataFrame with platform metrics data
            
        Returns:
            Number of records loaded
        """
        if metrics_df.empty:
            print("⚠️  No platform metrics to load")
            return 0
        
        loaded_count = 0
        
        for _, row in metrics_df.iterrows():
            try:
                # Create title for the record
                title = f"{row['platform']} - {row['metric_type']} - {row['date']}"
                
                # Prepare page properties
                properties = {
                    "ID": {
                        "title": [{"text": {"content": title}}]
                    },
                    "Date": {
                        "date": {"start": str(row['date'])}
                    },
                    "Platform": {
                        "select": {"name": str(row['platform'])}
                    },
                    "Metric_Type": {
                        "select": {"name": str(row['metric_type'])}
                    },
                    "Amount": {
                        "number": float(row['amount']) if pd.notna(row['amount']) else 0
                    },
                    "Category": {
                        "select": {"name": str(row['category'])}
                    },
                    "Currency": {
                        "select": {"name": str(row['currency'])}
                    },
                    "Description": {
                        "rich_text": [{"text": {"content": str(row['description'])}}]
                    }
                }
                
                # Create page in database
                page_data = {
                    "parent": {"database_id": self.database_id},
                    "properties": properties
                }
                
                url = "https://api.notion.com/v1/pages"
                response = requests.post(url, headers=self.headers, json=page_data)
                
                if response.status_code == 200:
                    loaded_count += 1
                else:
                    print(f"❌ Error creating page: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error loading record {title}: {e}")
                continue
        
        print(f"✅ Loaded {loaded_count} platform metric records to Notion")
        return loaded_count


def main():
    """Main function to run the daily platform metrics transformation"""
    
    # Get date parameter (defaults to yesterday)
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🚀 Starting Daily Platform Metrics Transformation for {target_date}")
    
    try:
        # Step 1: Fetch daily KPI data
        print("📥 Fetching daily KPI data...")
        fetcher = DailyKPIDataFetcher()
        daily_kpis_df = fetcher.fetch_daily_kpis(target_date)
        
        if daily_kpis_df.empty:
            print(f"⚠️  No daily KPI data found for {target_date}")
            return
        
        # Step 2: Transform to platform metrics
        print("🔄 Transforming to platform metrics format...")
        transformer = PlatformMetricsTransformer()
        platform_metrics_df = transformer.transform_to_platform_metrics(daily_kpis_df)
        
        if platform_metrics_df.empty:
            print("⚠️  No platform metrics generated")
            return
        
        # Step 3: Load to Notion (requires database ID)
        platform_metrics_db_id = os.getenv('NOTION_PLATFORM_METRICS_DB')
        if not platform_metrics_db_id:
            print("⚠️  NOTION_PLATFORM_METRICS_DB environment variable not set")
            print("💡 Please create the database first and set the environment variable")
            print("📊 Generated platform metrics summary:")
            print(platform_metrics_df.groupby(['platform', 'metric_type']).size().reset_index(name='count'))
            return
        
        print("📤 Loading platform metrics to Notion...")
        loader = PlatformMetricsNotionLoader(platform_metrics_db_id)
        loaded_count = loader.load_platform_metrics(platform_metrics_df)
        
        print(f"🎉 Daily Platform Metrics Transformation completed successfully!")
        print(f"📊 Processed {len(daily_kpis_df)} daily KPI records")
        print(f"📈 Generated {len(platform_metrics_df)} platform metric records")
        print(f"💾 Loaded {loaded_count} records to Notion")
        
    except Exception as e:
        print(f"❌ Daily Platform Metrics Transformation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
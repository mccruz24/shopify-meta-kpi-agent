#!/usr/bin/env python3
"""
Financial Analytics Scheduler - Automated daily payout collection
Now focuses on actual Shopify Payments payout data with daily granularity
Provides accurate gross/net amounts that hit your bank account
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import time

# Add project root to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)

from src.extractors.graphql_financial_analytics_extractor import GraphQLFinancialAnalyticsExtractor
from src.loaders.graphql_payout_notion_loader import GraphQLPayoutNotionLoader

class FinancialAnalyticsScheduler:
    """Automated daily payout analytics collection for scheduled runs"""
    
    def __init__(self):
        # Initialize extractors and loaders for payout data
        self.extractor = GraphQLFinancialAnalyticsExtractor()
        self.loader = GraphQLPayoutNotionLoader()
    
    def collect_daily_payouts(self, target_date: datetime = None) -> bool:
        """Collect and store daily payout data for the target date"""
        
        # Default to yesterday if no date specified
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        print(f"🤖 [SCHEDULED] Collecting Payout Analytics for {date_str}")
        
        try:
            # Extract payout data from Shopify (GraphQL)
            print(f"   💰 Extracting payouts from Shopify GraphQL...")
            payout_data = self.extractor.get_single_date_payouts(target_date)
            
            if not payout_data:
                print(f"   ℹ️  No payouts found for {date_str}")
                return True
            
            print(f"   ✅ Extracted {len(payout_data)} payouts")
            
            # Load into Notion Payout Analytics database
            print(f"   📝 Loading payouts into Notion...")
            results = self.loader.load_payouts_batch(payout_data, skip_if_exists=True)
            
            # Summary for logs
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate payout summary metrics
            total_gross = sum(po.get('gross_sales', 0) for po in payout_data)
            total_fees = sum(po.get('processing_fee', 0) for po in payout_data)
            total_net = sum(po.get('net_amount', 0) for po in payout_data)
            total_payouts = len(payout_data)
            
            # Get currency
            currency = payout_data[0].get('currency', 'EUR') if payout_data else 'EUR'
            
            print(f"   💰 Payout Summary:")
            print(f"        Gross Amount: {currency}{total_gross:.2f}")
            print(f"        Processing Fees: {currency}{total_fees:.2f}")
            print(f"        Net Amount (Bank): {currency}{total_net:.2f}")
            print(f"        Total Payouts: {total_payouts}")
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"✅ Successfully synced payout analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error collecting payout analytics for {date_str}: {e}")
            return False
    
    def test_system(self) -> bool:
        """Test the entire payout analytics system"""
        print("🧪 Testing Payout Analytics System")
        print("=" * 50)
        
        # Test Shopify GraphQL connection
        print("1️⃣ Testing Shopify GraphQL payout access...")
        if self.extractor.test_connection():
            print("   ✅ Shopify GraphQL payout connection successful")
        else:
            print("   ❌ Shopify GraphQL payout connection failed")
            return False
        
        # Test Notion connection
        print("2️⃣ Testing Notion Payout Analytics database...")
        if self.loader.test_connection():
            print("   ✅ Notion payout connection successful")
        else:
            print("   ❌ Notion payout connection failed")
            return False
        
        # Test payout data extraction
        print("3️⃣ Testing payout data extraction...")
        test_date = datetime.now() - timedelta(days=7)  # Look back further for payouts
        payout_data = self.extractor.get_single_date_payouts(test_date)
        
        if payout_data:
            print(f"   ✅ Successfully extracted {len(payout_data)} payouts")
            
            # Show sample payout data
            if payout_data:
                sample = payout_data[0]
                currency = sample.get('currency', 'EUR')
                print(f"   💰 Sample payout:")
                print(f"        Payout ID: {sample.get('payout_id', 'unknown')}")
                print(f"        Settlement Date: {sample.get('settlement_date', 'unknown')}")
                print(f"        Gross: {currency}{sample.get('gross_sales', 0):.2f}")
                print(f"        Fee: {currency}{sample.get('processing_fee', 0):.2f}")
                print(f"        Net (Bank): {currency}{sample.get('net_amount', 0):.2f}")
                print(f"        Status: {sample.get('payout_status', 'unknown')}")
        else:
            print(f"   ℹ️  No payouts found for test date {test_date.strftime('%Y-%m-%d')}")
            print(f"   💡 Try looking at recent payout dates or use specific payout ID")
        
        print("✅ Payout system test completed successfully")
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
    
    scheduler = FinancialAnalyticsScheduler()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = scheduler.test_system()
            sys.exit(0 if success else 1)
        
        elif command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                success = scheduler.collect_daily_payouts(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                print("💡 Usage:")
                print("   python financial_analytics_scheduler.py           # Yesterday's payouts")
                print("   python financial_analytics_scheduler.py test      # Test system")
                print("   python financial_analytics_scheduler.py 2025-06-25 # Specific date")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python financial_analytics_scheduler.py           # Yesterday's payouts")
            print("   python financial_analytics_scheduler.py test      # Test system")
            print("   python financial_analytics_scheduler.py 2025-06-25 # Specific date")
            sys.exit(1)
    
    else:
        # Default: collect yesterday's payouts
        success = scheduler.collect_daily_payouts()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
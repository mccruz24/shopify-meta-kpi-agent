#!/usr/bin/env python3
"""
Financial Analytics Scheduler - Automated daily financial transaction collection
Designed to run on a schedule (cron job) to automatically collect detailed financial analytics
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.financial_analytics_extractor import FinancialAnalyticsExtractor
from src.loaders.financial_notion_loader import FinancialNotionLoader

class FinancialAnalyticsScheduler:
    """Automated daily financial analytics collection for scheduled runs"""
    
    def __init__(self):
        # Initialize extractors and loaders
        self.extractor = FinancialAnalyticsExtractor()
        self.loader = FinancialNotionLoader()
    
    def collect_daily_transactions(self, target_date: datetime = None) -> bool:
        """Collect and store daily financial transactions for the target date"""
        
        # Default to yesterday if no date specified
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        print(f"🤖 [SCHEDULED] Collecting Financial Analytics for {date_str}")
        
        try:
            # Extract transaction data from Shopify
            print(f"   💰 Extracting transactions from Shopify...")
            transactions_data = self.extractor.extract_single_date(target_date)
            
            if not transactions_data:
                print(f"   ℹ️  No transactions found for {date_str}")
                return True
            
            print(f"   ✅ Extracted {len(transactions_data)} transactions")
            
            # Load into Notion Financial Analytics database
            print(f"   📝 Loading transactions into Notion...")
            results = self.loader.load_transactions_batch(transactions_data, skip_if_exists=True)
            
            # Summary for logs
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate financial summary metrics
            total_gross = sum(tx.get('gross_amount', 0) for tx in transactions_data)
            total_fees = sum(tx.get('processing_fee', 0) for tx in transactions_data)
            total_net = total_gross - total_fees
            total_transactions = len(transactions_data)
            
            # Categorize by transaction type
            sales = sum(1 for tx in transactions_data if tx.get('transaction_type') == 'sale')
            refunds = sum(1 for tx in transactions_data if tx.get('transaction_type') == 'refund')
            
            print(f"   💰 Financial Summary:")
            print(f"        Gross Revenue: ${total_gross:.2f}")
            print(f"        Processing Fees: ${total_fees:.2f}")
            print(f"        Net Revenue: ${total_net:.2f}")
            print(f"        Sales: {sales}, Refunds: {refunds}")
            print(f"   📊 Notion: {successful} new, {skipped} existing, {failed} failed")
            
            if failed == 0:
                print(f"✅ Successfully synced financial analytics for {date_str}")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error collecting financial analytics for {date_str}: {e}")
            return False
    
    def test_system(self) -> bool:
        """Test the entire financial analytics system"""
        print("🧪 Testing Financial Analytics System")
        print("=" * 50)
        
        # Test Shopify connection
        print("1️⃣ Testing Shopify connection...")
        if self.extractor.test_connection():
            print("   ✅ Shopify connection successful")
        else:
            print("   ❌ Shopify connection failed")
            return False
        
        # Test Notion connection
        print("2️⃣ Testing Notion Financial Analytics database...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing transaction data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        transactions_data = self.extractor.extract_single_date(test_date)
        
        if transactions_data:
            print(f"   ✅ Successfully extracted {len(transactions_data)} transactions")
            
            # Show sample data
            if transactions_data:
                sample = transactions_data[0]
                print(f"   💰 Sample transaction:")
                print(f"        Amount: ${sample.get('gross_amount', 0):.2f}")
                print(f"        Type: {sample.get('transaction_type', 'unknown')}")
                print(f"        Gateway: {sample.get('payment_gateway', 'unknown')}")
                print(f"        Fee: ${sample.get('processing_fee', 0):.2f}")
                print(f"        Net: ${sample.get('net_amount', 0):.2f}")
        else:
            print(f"   ℹ️  No transactions found for test date {test_date.strftime('%Y-%m-%d')}")
        
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
                success = scheduler.collect_daily_transactions(target_date)
                sys.exit(0 if success else 1)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                print("💡 Usage:")
                print("   python financial_analytics_scheduler.py           # Yesterday's transactions")
                print("   python financial_analytics_scheduler.py test      # Test system")
                print("   python financial_analytics_scheduler.py 2025-06-25 # Specific date")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python financial_analytics_scheduler.py           # Yesterday's transactions")
            print("   python financial_analytics_scheduler.py test      # Test system")
            print("   python financial_analytics_scheduler.py 2025-06-25 # Specific date")
            sys.exit(1)
    
    else:
        # Default: collect yesterday's transactions
        success = scheduler.collect_daily_transactions()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
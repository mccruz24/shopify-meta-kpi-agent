#!/usr/bin/env python3
"""
Financial Analytics Sync - Comprehensive financial data extraction and Notion integration
Syncs detailed transaction and financial analytics data to Notion database
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

class FinancialAnalyticsSync:
    """Sync financial analytics data from Shopify to Notion"""
    
    def __init__(self):
        self.extractor = FinancialAnalyticsExtractor()
        self.loader = FinancialNotionLoader()
    
    def sync_single_date(self, date: datetime = None) -> bool:
        """Sync financial transactions for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"💰 Syncing financial analytics for {date_str}")
        
        try:
            # Extract transaction data
            print("🔍 Extracting transactions from Shopify...")
            transactions_data = self.extractor.extract_single_date(date)
            
            if not transactions_data:
                print(f"ℹ️  No transactions found for {date_str}")
                return True
            
            print(f"✅ Extracted {len(transactions_data)} transactions")
            
            # Load into Notion
            print("📝 Loading transactions into Notion...")
            results = self.loader.load_transactions_batch(transactions_data, skip_if_exists=True)
            
            # Summary
            successful = results['successful']
            skipped = results['skipped']
            failed = results['failed']
            
            # Calculate financial summary
            total_amount = sum(tx.get('gross_amount', 0) for tx in transactions_data)
            total_fees = sum(tx.get('processing_fee', 0) for tx in transactions_data)
            net_amount = total_amount - total_fees
            
            print(f"   💰 Financial Summary:")
            print(f"     Gross: ${total_amount:.2f}")
            print(f"     Fees: ${total_fees:.2f}")
            print(f"     Net: ${net_amount:.2f}")
            
            if failed == 0:
                print(f"🎉 Successfully synced {date_str}: {successful} new, {skipped} existing")
                return True
            else:
                print(f"⚠️  Sync completed with errors: {successful} successful, {failed} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing financial data for {date_str}: {e}")
            return False
    
    def sync_date_range(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Sync financial transactions for a date range"""
        if end_date is None:
            end_date = start_date
        
        print(f"💰 Syncing financial analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\n📅 Processing {date_str}")
            
            try:
                # Extract transactions for this date
                transactions_data = self.extractor.extract_single_date(current_date)
                
                if transactions_data:
                    # Load into Notion
                    results = self.loader.load_transactions_batch(transactions_data, skip_if_exists=True)
                    total_successful += results['successful']
                    total_failed += results['failed']
                    total_skipped += results['skipped']
                else:
                    print(f"ℹ️  No transactions found for {date_str}")
                
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
    
    def backfill_transactions(self, days_back: int = 30) -> Dict:
        """Backfill financial transactions for the last N days"""
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back - 1)
        
        print(f"🔄 Backfilling financial transactions for last {days_back} days")
        return self.sync_date_range(start_date, end_date)
    
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
        print("2️⃣ Testing Notion connection...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing transaction extraction...")
        test_date = datetime.now() - timedelta(days=1)
        transactions_data = self.extractor.extract_single_date(test_date)
        
        if transactions_data:
            print(f"   ✅ Successfully extracted {len(transactions_data)} transactions")
            
            # Show sample data
            if transactions_data:
                sample = transactions_data[0]
                print(f"   💰 Sample transaction: ${sample.get('gross_amount', 0):.2f} {sample.get('transaction_type', 'unknown')}")
                print(f"        Gateway: {sample.get('payment_gateway', 'unknown')}")
                print(f"        Status: {sample.get('status', 'unknown')}")
        else:
            print(f"   ℹ️  No transactions found for test date {test_date.strftime('%Y-%m-%d')}")
        
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
    
    sync = FinancialAnalyticsSync()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = sync.test_system()
            sys.exit(0 if success else 1)
        
        elif command == 'backfill':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            results = sync.backfill_transactions(days)
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
            print("   python financial_analytics_sync.py                # Yesterday's transactions")
            print("   python financial_analytics_sync.py test           # Test system")
            print("   python financial_analytics_sync.py 2025-06-25     # Specific date")
            print("   python financial_analytics_sync.py backfill [30]  # Backfill last N days")
            sys.exit(1)
    
    else:
        # Default: sync yesterday's transactions
        success = sync.sync_single_date()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
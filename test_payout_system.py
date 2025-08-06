#!/usr/bin/env python3
"""
Test Payout Analytics System
Comprehensive test of the new payout-focused financial analytics system
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extractors.financial_analytics_extractor import FinancialAnalyticsExtractor
from src.loaders.payout_notion_loader import PayoutNotionLoader

load_dotenv()

class PayoutSystemTester:
    def __init__(self):
        self.extractor = FinancialAnalyticsExtractor()
        self.loader = PayoutNotionLoader()
        
    def test_full_system(self):
        """Test the complete payout analytics system"""
        print("🧪 COMPREHENSIVE PAYOUT SYSTEM TEST")
        print("=" * 60)
        print()
        
        # 1. Test GraphQL Connection
        print("1️⃣ Testing Shopify GraphQL Payout Access")
        print("-" * 40)
        if self.extractor.test_connection():
            print("✅ GraphQL payout connection successful")
            graphql_works = True
        else:
            print("❌ GraphQL payout connection failed")
            print("   💡 Check .env file for SHOPIFY_ACCESS_TOKEN")
            print("   💡 Ensure token has 'read_shopify_payments_payouts' permission")
            graphql_works = False
        
        print()
        
        # 2. Test Notion Connection
        print("2️⃣ Testing Notion Payout Database Access")
        print("-" * 40)
        if self.loader.test_connection():
            print("✅ Notion payout database connection successful")
            notion_works = True
        else:
            print("❌ Notion payout database connection failed")
            print("   💡 Check .env file for NOTION_TOKEN")
            print("   💡 Ensure database ID is correct")
            notion_works = False
        
        print()
        
        # 3. Test Payout Data Extraction (if GraphQL works)
        if graphql_works:
            print("3️⃣ Testing Payout Data Extraction")
            print("-" * 40)
            
            # Try multiple recent dates to find payouts
            test_dates = [
                datetime(2025, 6, 27),
                datetime(2025, 6, 26), 
                datetime(2025, 6, 25),
                datetime.now() - timedelta(days=1),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=3)
            ]
            
            payout_found = False
            for test_date in test_dates:
                print(f"   Checking {test_date.strftime('%Y-%m-%d')}...")
                payouts = self.extractor.extract_single_date(test_date)
                
                if payouts:
                    print(f"   ✅ Found {len(payouts)} payouts on {test_date.strftime('%Y-%m-%d')}")
                    
                    # Show detailed payout info
                    for payout in payouts:
                        currency = payout.get('currency', 'EUR')
                        print(f"      💰 Payout {payout.get('payout_id', 'unknown')}:")
                        print(f"         Gross: {currency}{payout.get('gross_amount', 0):.2f}")
                        print(f"         Fees: {currency}{payout.get('processing_fee', 0):.2f}")
                        print(f"         Net: {currency}{payout.get('net_amount', 0):.2f}")
                        print(f"         Status: {payout.get('payout_status', 'unknown')}")
                    
                    payout_found = True
                    
                    # 4. Test Notion Loading (if both systems work)
                    if notion_works:
                        print()
                        print("4️⃣ Testing Notion Payout Loading")
                        print("-" * 40)
                        
                        print(f"   Loading {len(payouts)} payouts into Notion...")
                        results = self.loader.load_payouts_batch(payouts, skip_if_exists=True)
                        
                        if results['successful'] > 0 or results['skipped'] > 0:
                            print("   ✅ Notion loading successful")
                            print(f"      New records: {results['successful']}")
                            print(f"      Existing records: {results['skipped']}")
                            print(f"      Failed: {results['failed']}")
                        else:
                            print("   ⚠️  Notion loading completed but no records processed")
                    
                    break
            
            if not payout_found:
                print("   ⚠️  No payouts found in recent dates")
                print("   💡 Payouts typically settle 1-3 days after orders")
                print("   💡 Try running on specific dates when you know payouts occurred")
        
        print()
        
        # Summary
        print("🎯 SYSTEM TEST SUMMARY")
        print("=" * 60)
        
        if graphql_works and notion_works:
            print("✅ Full system operational!")
            print()
            print("💡 USAGE INSTRUCTIONS:")
            print("   • Run daily: python3 financial_analytics_scheduler.py")
            print("   • Specific date: python3 financial_analytics_scheduler.py 2025-06-27") 
            print("   • Test system: python3 financial_analytics_scheduler.py test")
            print()
            print("📊 NOTION DATABASE FEATURES:")
            print("   • Daily payout granularity")
            print("   • Gross amount breakdown")
            print("   • Processing fee tracking")
            print("   • Net amount (actual bank deposits)")
            print("   • Settlement date accuracy")
            print("   • Currency support (EUR/USD)")
            print("   • Refund and adjustment tracking")
            
        elif graphql_works and not notion_works:
            print("⚠️  Shopify GraphQL working, Notion connection failed")
            print("   Fix Notion credentials to enable full system")
            
        elif not graphql_works and notion_works:
            print("⚠️  Notion working, Shopify GraphQL connection failed")
            print("   Fix Shopify credentials to enable data extraction")
            
        else:
            print("❌ Both connections failed")
            print("   Fix both Shopify and Notion credentials")
        
        print()
        return graphql_works and notion_works
    
    def demonstrate_payout_features(self):
        """Demonstrate key features of the payout system"""
        print("🚀 PAYOUT SYSTEM FEATURES DEMO")
        print("=" * 60)
        print()
        
        print("🔧 KEY IMPROVEMENTS OVER OLD SYSTEM:")
        print("   ✅ Real payout data (not transaction estimates)")
        print("   ✅ Actual settlement dates (not calculated)")
        print("   ✅ True processing fees (not 2.9% estimates)")
        print("   ✅ Net amounts that hit bank account")
        print("   ✅ Daily granularity for payouts")
        print("   ✅ Complete financial breakdown")
        print("   ✅ Currency conversion tracking")
        print("   ✅ Refund and adjustment handling")
        print()
        
        print("📊 NOTION DATABASE STRUCTURE:")
        print("   • Payout ID (Primary)")
        print("   • Settlement Date")
        print("   • Gross Amount (Total sales)")
        print("   • Processing Fee (Actual fees)")
        print("   • Net Amount (Bank deposit)")
        print("   • Fee Rate % (Calculated)")
        print("   • Currency (EUR/USD)")
        print("   • Payout Status")
        print("   • Refunds breakdown")
        print("   • Adjustments breakdown")
        print("   • Reserved funds tracking")
        print()
        
        print("⚡ AUTOMATION CAPABILITIES:")
        print("   • Daily scheduled collection")
        print("   • Duplicate detection")
        print("   • Error handling and retry")
        print("   • Comprehensive logging")
        print("   • Rate limit protection")
        print()

def main():
    print("💰 PAYOUT ANALYTICS SYSTEM TESTER")
    print("Testing the new payout-focused financial analytics")
    print("=" * 70)
    print()
    
    tester = PayoutSystemTester()
    
    # Show feature overview
    tester.demonstrate_payout_features()
    
    # Run comprehensive test
    success = tester.test_full_system()
    
    if success:
        print("🎉 SUCCESS! Payout analytics system is fully operational!")
    else:
        print("⚠️  System partially operational. Check credentials and retry.")
    
    print("\n💡 Next steps:")
    print("   1. Ensure Shopify API credentials have payout permissions")
    print("   2. Verify Notion database is accessible")
    print("   3. Run daily scheduler to collect payout data")
    print("   4. Set up automated scheduling (cron job)")

if __name__ == "__main__":
    main()
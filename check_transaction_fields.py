#!/usr/bin/env python3
"""
Check Transaction Fields
Inspect what fields are available in Shopify's Transaction API response
"""

import os
import sys
from datetime import datetime
from typing import Dict
import json
from dotenv import load_dotenv

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from enhanced_financial_analytics_extractor import EnhancedFinancialAnalyticsExtractor

def check_transaction_fields():
    """Check what fields are available in the Transaction API"""
    
    print("🔍 CHECKING SHOPIFY TRANSACTION API FIELDS")
    print("=" * 60)
    
    extractor = EnhancedFinancialAnalyticsExtractor()
    
    # Test connection
    if not extractor.test_connection():
        print("❌ Cannot connect to Shopify API")
        return
    
    print("✅ Connected to Shopify API")
    
    # Get order 1457 transactions
    order_id = "6891056169307"  # Order #1457 ID from your results
    
    print(f"📊 Fetching transaction details for order {order_id}...")
    
    transactions_data = extractor._make_request(f'orders/{order_id}/transactions.json')
    
    if not transactions_data or not transactions_data.get('transactions'):
        print("❌ No transactions found")
        return
    
    transactions = transactions_data['transactions']
    print(f"✅ Found {len(transactions)} transactions")
    
    # Analyze each transaction's available fields
    for i, transaction in enumerate(transactions, 1):
        print(f"\n{'='*50}")
        print(f"TRANSACTION {i} - AVAILABLE FIELDS")
        print(f"{'='*50}")
        
        # Print basic fields
        print(f"ID: {transaction.get('id')}")
        print(f"Kind: {transaction.get('kind')}")
        print(f"Status: {transaction.get('status')}")
        print(f"Amount: {transaction.get('amount')}")
        print(f"Currency: {transaction.get('currency')}")
        print(f"Gateway: {transaction.get('gateway')}")
        print(f"Created: {transaction.get('created_at')}")
        
        # Check for exchange rate fields
        print(f"\n💱 EXCHANGE RATE FIELDS:")
        potential_rate_fields = [
            'exchange_rate', 'currency_exchange_rate', 'rate', 
            'presentment_currency', 'shop_currency',
            'amount_set', 'presentment_money', 'shop_money'
        ]
        
        found_fields = []
        for field in potential_rate_fields:
            if field in transaction:
                found_fields.append(field)
                print(f"✅ {field}: {transaction[field]}")
        
        if not found_fields:
            print("❌ No exchange rate fields found")
        
        # Check for amount_set structure (multi-currency data)
        if 'amount_set' in transaction:
            amount_set = transaction['amount_set']
            print(f"\n💰 AMOUNT_SET STRUCTURE:")
            print(json.dumps(amount_set, indent=2))
        
        # Print all available fields for analysis
        print(f"\n📋 ALL AVAILABLE FIELDS:")
        all_fields = sorted(transaction.keys())
        for field in all_fields:
            value = transaction[field]
            # Truncate long values
            if isinstance(value, (dict, list)):
                value_str = f"{type(value).__name__} with {len(value) if hasattr(value, '__len__') else '?'} items"
            else:
                value_str = str(value)[:100]
            print(f"   {field}: {value_str}")
        
        # Export full transaction data
        filename = f"transaction_{transaction.get('id', i)}_full_data.json"
        with open(filename, 'w') as f:
            json.dump(transaction, f, indent=2, default=str)
        print(f"\n📄 Full transaction data exported to: {filename}")
    
    print(f"\n✅ Transaction field analysis completed!")

def main():
    """Main function"""
    
    # Validate environment
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        print("💡 This script needs to run with API credentials")
        sys.exit(1)
    
    check_transaction_fields()

if __name__ == "__main__":
    main()
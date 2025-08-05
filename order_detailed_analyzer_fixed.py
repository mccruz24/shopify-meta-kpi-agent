#!/usr/bin/env python3
"""
Order Detailed Analyzer - Fixed Version
Extract comprehensive data for a specific order to cross-check against Shopify app
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from enhanced_financial_analytics_extractor import EnhancedFinancialAnalyticsExtractor

class OrderDetailedAnalyzer:
    """Analyze specific orders in detail for cross-checking"""
    
    def __init__(self):
        self.extractor = EnhancedFinancialAnalyticsExtractor()
    
    def analyze_specific_order(self, order_number: str) -> Dict:
        """Analyze a specific order by order number"""
        
        print(f"🔍 DETAILED ORDER ANALYSIS")
        print(f"Order Number: #{order_number}")
        print("=" * 60)
        
        try:
            # Search for the order
            order_data = self._find_order_by_number(order_number)
            
            if not order_data:
                return {
                    'status': 'not_found',
                    'order_number': order_number,
                    'message': 'Order not found'
                }
            
            # Get detailed order information
            detailed_order = self._get_detailed_order_data(order_data['id'])
            
            # Get all transactions for this order
            transactions = self._get_order_transactions(order_data['id'])
            
            # Calculate detailed fees for each transaction
            enhanced_transactions = []
            for tx in transactions:
                try:
                    enhanced_tx = self.extractor._enhance_transaction_with_fees(tx, detailed_order)
                    enhanced_transactions.append(enhanced_tx)
                except Exception as e:
                    print(f"⚠️  Error enhancing transaction {tx.get('id', 'unknown')}: {e}")
                    # Add basic transaction data
                    basic_tx = self._create_basic_transaction(tx, detailed_order)
                    enhanced_transactions.append(basic_tx)
            
            # Create comprehensive analysis
            analysis = self._create_comprehensive_analysis(detailed_order, enhanced_transactions)
            
            # Print detailed results
            self._print_detailed_analysis(analysis)
            
            # Export to JSON for easy sharing
            filename = self._export_analysis(analysis, order_number)
            
            print(f"\n📄 Detailed analysis exported to: {filename}")
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing order: {e}")
            return {
                'status': 'error',
                'order_number': order_number,
                'error': str(e)
            }
    
    def _find_order_by_number(self, order_number: str) -> Optional[Dict]:
        """Find order by order number"""
        
        print(f"🔎 Searching for order #{order_number}...")
        
        # Clean order number
        clean_order_number = str(order_number).replace('#', '').strip()
        
        try:
            # Search orders
            orders_data = self.extractor._make_request('orders.json', {
                'limit': 250,
                'status': 'any',
                'fields': 'id,order_number,name'
            })
            
            if orders_data and orders_data.get('orders'):
                for order in orders_data['orders']:
                    try:
                        order_num = str(order.get('order_number', ''))
                        order_name = str(order.get('name', ''))
                        if order_num == clean_order_number or order_name == f"#{clean_order_number}":
                            print(f"✅ Found order #{order.get('order_number')} (ID: {order.get('id')})")
                            return order
                    except (TypeError, ValueError) as e:
                        continue
            
            print(f"❌ Order #{order_number} not found")
            return None
            
        except Exception as e:
            print(f"❌ Error searching for order: {e}")
            return None
    
    def _get_detailed_order_data(self, order_id: str) -> Dict:
        """Get detailed order data"""
        
        print(f"📊 Fetching detailed order data...")
        
        order_data = self.extractor._make_request(f'orders/{order_id}.json')
        
        if order_data and 'order' in order_data:
            return order_data['order']
        
        return {}
    
    def _get_order_transactions(self, order_id: str) -> List[Dict]:
        """Get all transactions for an order"""
        
        print(f"💳 Fetching order transactions...")
        
        transactions_data = self.extractor._make_request(f'orders/{order_id}/transactions.json')
        
        if transactions_data and transactions_data.get('transactions'):
            # Filter to only capture/sale transactions (not authorization)
            capture_transactions = []
            for tx in transactions_data['transactions']:
                if tx.get('kind') in ['capture', 'sale']:
                    capture_transactions.append(tx)
            
            print(f"✅ Found {len(transactions_data['transactions'])} total transactions, {len(capture_transactions)} capture/sale transactions")
            return capture_transactions
        
        print(f"⚠️  No transactions found for order")
        return []
    
    def _create_basic_transaction(self, tx: Dict, order: Dict) -> Dict:
        """Create basic transaction data when enhancement fails"""
        
        return {
            'transaction_id': str(tx.get('id', '')),
            'order_id': str(order.get('id', '')),
            'order_number': str(order.get('order_number', '')),
            'created_at': str(tx.get('created_at', '')),
            'kind': str(tx.get('kind', '')),
            'status': str(tx.get('status', '')),
            'gross_amount': float(tx.get('amount', 0)),
            'gross_amount_usd': float(tx.get('amount', 0)),
            'gross_amount_eur': float(tx.get('amount', 0)),
            'currency': str(tx.get('currency', 'USD')),
            'gateway': str(tx.get('gateway', 'unknown')),
            'exchange_rate': 1.0,
            'shopify_payment_fee': 0.0,
            'shopify_payment_vat': 0.0,
            'currency_conversion_fee': 0.0,
            'currency_conversion_vat': 0.0,
            'transaction_fee': 0.0,
            'total_fees': 0.0,
            'net_amount': float(tx.get('amount', 0))
        }
    
    def _create_comprehensive_analysis(self, order: Dict, transactions: List[Dict]) -> Dict:
        """Create comprehensive order analysis"""
        
        # Basic order information
        order_info = {
            'order_id': str(order.get('id', '')),
            'order_number': str(order.get('order_number', '')),
            'name': str(order.get('name', '')),
            'created_at': str(order.get('created_at', '')),
            'updated_at': str(order.get('updated_at', '')),
            'processed_at': str(order.get('processed_at', '')),
            'financial_status': str(order.get('financial_status', '')),
            'fulfillment_status': str(order.get('fulfillment_status', '')),
            'email': str(order.get('email', ''))
        }
        
        # Financial breakdown
        financial_info = {
            'currency': str(order.get('currency', 'USD')),
            'total_price': float(order.get('total_price', 0)),
            'subtotal_price': float(order.get('subtotal_price', 0)),
            'total_discounts': float(order.get('total_discounts', 0)),
            'total_tax': float(order.get('total_tax', 0)),
            'shipping_total': 0,
            'total_outstanding': float(order.get('total_outstanding', 0))
        }
        
        # Calculate shipping
        shipping_lines = order.get('shipping_lines', [])
        for shipping in shipping_lines:
            financial_info['shipping_total'] += float(shipping.get('price', 0))
        
        # Line items details
        line_items = []
        for item in order.get('line_items', []):
            line_item = {
                'title': str(item.get('title', '')),
                'variant_title': str(item.get('variant_title', '')),
                'sku': str(item.get('sku', '')),
                'quantity': int(item.get('quantity', 0)),
                'price': float(item.get('price', 0)),
                'total_discount': float(item.get('total_discount', 0))
            }
            line_items.append(line_item)
        
        # Transaction analysis
        transaction_summary = {
            'total_transactions': len(transactions),
            'total_amount_processed': 0.0,
            'total_fees': 0.0,
            'net_payout': 0.0
        }
        
        for tx in transactions:
            # Handle both old and new transaction formats
            gross_amount = float(tx.get('gross_amount_eur', tx.get('gross_amount', 0)))
            total_fees = float(tx.get('total_fees', 0))
            net_amount = float(tx.get('net_amount', 0))
            
            transaction_summary['total_amount_processed'] += gross_amount
            transaction_summary['total_fees'] += total_fees
            transaction_summary['net_payout'] += net_amount
        
        return {
            'status': 'success',
            'analysis_timestamp': datetime.now().isoformat(),
            'order_info': order_info,
            'financial_info': financial_info,
            'line_items': line_items,
            'transactions': transactions,
            'transaction_summary': transaction_summary,
            'raw_order_data': order
        }
    
    def _print_detailed_analysis(self, analysis: Dict):
        """Print detailed analysis results"""
        
        if analysis['status'] != 'success':
            print(f"❌ Analysis failed: {analysis.get('message', 'Unknown error')}")
            return
        
        order = analysis['order_info']
        financial = analysis['financial_info']
        transactions = analysis['transactions']
        summary = analysis['transaction_summary']
        
        print(f"\n📋 ORDER INFORMATION")
        print("=" * 40)
        print(f"Order ID: {order['order_id']}")
        print(f"Order Number: #{order['order_number']}")
        print(f"Order Name: {order['name']}")
        print(f"Created: {order['created_at']}")
        print(f"Processed: {order['processed_at']}")
        print(f"Financial Status: {order['financial_status']}")
        print(f"Fulfillment Status: {order['fulfillment_status']}")
        
        if order['email']:
            print(f"Customer Email: {order['email']}")
        
        print(f"\n💰 FINANCIAL BREAKDOWN")
        print("=" * 40)
        print(f"Currency: {financial['currency']}")
        print(f"Total Price: {financial['currency']} {financial['total_price']:.2f}")
        print(f"Subtotal: {financial['currency']} {financial['subtotal_price']:.2f}")
        print(f"Shipping: {financial['currency']} {financial['shipping_total']:.2f}")
        print(f"Tax: {financial['currency']} {financial['total_tax']:.2f}")
        print(f"Discounts: {financial['currency']} {financial['total_discounts']:.2f}")
        print(f"Outstanding: {financial['currency']} {financial['total_outstanding']:.2f}")
        
        print(f"\n🛍️  LINE ITEMS")
        print("=" * 40)
        for i, item in enumerate(analysis['line_items'], 1):
            print(f"{i}. {item['title']}")
            if item['variant_title']:
                print(f"   Variant: {item['variant_title']}")
            print(f"   SKU: {item['sku']}")
            print(f"   Quantity: {item['quantity']}")
            print(f"   Price: {financial['currency']} {item['price']:.2f}")
            if item['total_discount'] > 0:
                print(f"   Total Discount: {financial['currency']} {item['total_discount']:.2f}")
            print()
        
        print(f"💳 TRANSACTION DETAILS")
        print("=" * 40)
        print(f"Total Transactions: {summary['total_transactions']}")
        print(f"Total Amount Processed: €{summary['total_amount_processed']:.2f}")
        print(f"Total Fees: €{summary['total_fees']:.2f}")
        print(f"Net Payout: €{summary['net_payout']:.2f}")
        
        for i, tx in enumerate(transactions, 1):
            print(f"\nTransaction {i}:")
            print(f"  ID: {tx['transaction_id']}")
            print(f"  Type: {tx['kind']}")
            print(f"  Status: {tx['status']}")
            print(f"  Gateway: {tx['gateway']}")
            print(f"  Created: {tx['created_at']}")
            
            # Show both USD and EUR amounts if conversion happened
            if tx.get('gross_amount_usd') and tx.get('gross_amount_eur'):
                print(f"  Gross Amount USD: ${tx['gross_amount_usd']:.2f}")
                print(f"  Gross Amount EUR: €{tx['gross_amount_eur']:.2f}")
                print(f"  Exchange Rate: {tx.get('exchange_rate', 0):.6f}")
            else:
                print(f"  Gross Amount: {tx.get('currency', 'USD')} {tx.get('gross_amount', 0):.2f}")
            
            # Fee breakdown matching Shopify's structure
            if tx.get('shopify_payment_fee', 0) > 0:
                print(f"  Shopify Payment Fee: €{tx['shopify_payment_fee']:.2f}")
            if tx.get('shopify_payment_vat', 0) > 0:
                print(f"  Shopify Payment VAT: €{tx['shopify_payment_vat']:.2f}")
            if tx.get('currency_conversion_fee', 0) > 0:
                print(f"  Currency Conversion Fee: €{tx['currency_conversion_fee']:.2f}")
            if tx.get('currency_conversion_vat', 0) > 0:
                print(f"  Currency Conversion VAT: €{tx['currency_conversion_vat']:.2f}")
            if tx.get('transaction_fee', 0) > 0:
                print(f"  Transaction Fee: €{tx['transaction_fee']:.2f}")
            if tx.get('total_fees', 0) > 0:
                print(f"  Total Fees: €{tx['total_fees']:.2f}")
            if tx.get('net_amount', 0) > 0:
                print(f"  Net Amount: €{tx['net_amount']:.2f}")
        
        print(f"\n✅ CROSS-CHECK THIS DATA WITH SHOPIFY APP:")
        print("=" * 50)
        print("1. Go to Orders → Search for order #" + order['order_number'])
        print("2. Verify order total matches: " + f"{financial['currency']} {financial['total_price']:.2f}")
        print("3. Check transaction details in the Timeline section")
        print("4. Verify payment gateway and fees")
        print("5. Compare customer email and shipping address")
    
    def _export_analysis(self, analysis: Dict, order_number: str) -> str:
        """Export analysis to JSON file"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"order_analysis_{order_number.replace('#', '')}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        return filename

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("❌ Please provide an order number")
        print("💡 Usage: python order_detailed_analyzer_fixed.py 1457")
        sys.exit(1)
    
    order_number = sys.argv[1]
    
    # Validate environment
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        sys.exit(1)
    
    analyzer = OrderDetailedAnalyzer()
    
    # Test connection first
    if not analyzer.extractor.test_connection():
        print("❌ Cannot connect to Shopify API")
        sys.exit(1)
    
    # Analyze the specific order
    result = analyzer.analyze_specific_order(order_number)
    
    if result['status'] in ['error', 'not_found']:
        sys.exit(1)
    
    print("\n🎯 Ready for cross-check with Shopify app!")

if __name__ == "__main__":
    main()
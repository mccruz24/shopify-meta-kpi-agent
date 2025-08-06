#!/usr/bin/env python3
"""
Order Detailed Analyzer
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
                                                              # Add basic transaction data without enhancements
                     basic_tx = {
                         'transaction_id': str(tx.get('id', '')),
                         'order_id': str(detailed_order.get('id', '')),
                         'order_number': str(detailed_order.get('order_number', '')),
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
        
        # Clean order number (remove # if present)
        clean_order_number = str(order_number).replace('#', '').strip()
        
        try:
            # Search orders by order number
            orders_data = self.extractor._make_request('orders.json', {
                'name': clean_order_number,
                'limit': 1,
                'status': 'any'
            })
            
            if orders_data and orders_data.get('orders'):
                order = orders_data['orders'][0]
                print(f"✅ Found order #{order.get('order_number')} (ID: {order.get('id')})")
                return order
            
            # Try searching with different parameters
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
                        print(f"⚠️  Skipping malformed order data: {e}")
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
    
    def _create_comprehensive_analysis(self, order: Dict, transactions: List[Dict]) -> Dict:
        """Create comprehensive order analysis"""
        
        # Basic order information
        order_info = {
            'order_id': str(order.get('id', '')),
            'order_number': order.get('order_number', ''),
            'name': order.get('name', ''),
            'created_at': order.get('created_at', ''),
            'updated_at': order.get('updated_at', ''),
            'processed_at': order.get('processed_at', ''),
            'financial_status': order.get('financial_status', ''),
            'fulfillment_status': order.get('fulfillment_status', ''),
            'tags': order.get('tags', ''),
            'note': order.get('note', ''),
            'email': order.get('email', ''),
            'phone': order.get('phone', '')
        }
        
        # Financial breakdown
        financial_info = {
            'currency': order.get('currency', 'USD'),
            'total_price': float(order.get('total_price', 0)),
            'subtotal_price': float(order.get('subtotal_price', 0)),
            'total_discounts': float(order.get('total_discounts', 0)),
            'total_tax': float(order.get('total_tax', 0)),
            'shipping_total': 0,
            'total_outstanding': float(order.get('total_outstanding', 0)),
            'total_line_items_price': float(order.get('total_line_items_price', 0))
        }
        
        # Calculate shipping
        shipping_lines = order.get('shipping_lines', [])
        for shipping in shipping_lines:
            financial_info['shipping_total'] += float(shipping.get('price', 0))
        
        # Line items details
        line_items = []
        for item in order.get('line_items', []):
            line_item = {
                'id': item.get('id'),
                'product_id': item.get('product_id'),
                'variant_id': item.get('variant_id'),
                'title': item.get('title'),
                'variant_title': item.get('variant_title'),
                'sku': item.get('sku'),
                'quantity': item.get('quantity'),
                'price': float(item.get('price', 0)),
                'total_discount': float(item.get('total_discount', 0)),
                'fulfillable_quantity': item.get('fulfillable_quantity'),
                'fulfillment_status': item.get('fulfillment_status')
            }
            line_items.append(line_item)
        
        # Customer information
        customer_info = {}
        if order.get('customer'):
            customer = order['customer']
            customer_info = {
                'id': customer.get('id'),
                'email': customer.get('email'),
                'first_name': customer.get('first_name'),
                'last_name': customer.get('last_name'),
                'orders_count': customer.get('orders_count'),
                'total_spent': customer.get('total_spent'),
                'created_at': customer.get('created_at')
            }
        
        # Shipping address
        shipping_address = order.get('shipping_address', {})
        
        # Billing address
        billing_address = order.get('billing_address', {})
        
        # Transaction analysis
        transaction_summary = {
            'total_transactions': len(transactions),
            'total_amount_processed': 0,
            'total_fees': 0,
            'net_payout': 0,
            'currency_conversions': []
        }
        
        for tx in transactions:
            # Handle both old and new transaction formats
            gross_amount = tx.get('gross_amount_eur', tx.get('gross_amount', 0))
            total_fees = tx.get('total_fees', 0)
            net_amount = tx.get('net_amount', 0)
            
            transaction_summary['total_amount_processed'] += float(gross_amount) if gross_amount else 0
            transaction_summary['total_fees'] += float(total_fees) if total_fees else 0
            transaction_summary['net_payout'] += float(net_amount) if net_amount else 0
            
            if tx.get('original_currency') and tx.get('converted_currency'):
                transaction_summary['currency_conversions'].append({
                    'from': tx.get('original_currency'),
                    'to': tx.get('converted_currency'),
                    'original_amount': tx.get('original_amount'),
                    'converted_amount': tx.get('converted_amount'),
                    'exchange_rate': tx.get('exchange_rate')
                })
        
        return {
            'status': 'success',
            'analysis_timestamp': datetime.now().isoformat(),
            'order_info': order_info,
            'financial_info': financial_info,
            'line_items': line_items,
            'customer_info': customer_info,
            'shipping_address': shipping_address,
            'billing_address': billing_address,
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
            print(f"   SKU: {item.get('sku', 'N/A')}")
            print(f"   Quantity: {item['quantity']}")
            print(f"   Price: {financial['currency']} {item['price']:.2f}")
            print(f"   Total Discount: {financial['currency']} {item['total_discount']:.2f}")
            print()
        
        print(f"💳 TRANSACTION DETAILS")
        print("=" * 40)
        print(f"Total Transactions: {summary['total_transactions']}")
        print(f"Total Amount Processed: {summary['total_amount_processed']:.2f}")
        print(f"Total Fees: {summary['total_fees']:.2f}")
        print(f"Net Payout: {summary['net_payout']:.2f}")
        
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
                 print(f"  Gross Amount: {tx['currency']} {tx.get('gross_amount', 0):.2f}")
             
             # Fee breakdown matching Shopify's structure
             if tx.get('shopify_payment_fee'):
                 print(f"  Shopify Payment Fee: €{tx['shopify_payment_fee']:.2f}")
             if tx.get('shopify_payment_vat'):
                 print(f"  Shopify Payment VAT: €{tx['shopify_payment_vat']:.2f}")
             if tx.get('currency_conversion_fee'):
                 print(f"  Currency Conversion Fee: €{tx['currency_conversion_fee']:.2f}")
             if tx.get('currency_conversion_vat'):
                 print(f"  Currency Conversion VAT: €{tx['currency_conversion_vat']:.2f}")
             if tx.get('transaction_fee'):
                 print(f"  Transaction Fee: €{tx['transaction_fee']:.2f}")
             if tx.get('total_fees'):
                 print(f"  Total Fees: €{tx['total_fees']:.2f}")
             if tx.get('net_amount'):
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
        print("💡 Usage: python order_detailed_analyzer.py 1457")
        print("💡 Usage: python order_detailed_analyzer.py #1457")
        sys.exit(1)
    
    order_number = sys.argv[1]
    
    # Validate environment
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        print("💡 Please set SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN")
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
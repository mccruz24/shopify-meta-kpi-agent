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

# Load environment variables
load_dotenv()

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from enhanced_financial_analytics_extractor import EnhancedFinancialAnalyticsExtractor

class OrderDetailedAnalyzer:
    """Analyze specific orders in detail for cross-checking"""
    
    def __init__(self):
        # Debug environment variables
        shop_url = os.getenv('SHOPIFY_SHOP_URL')
        access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        print(f"🔍 Debug: SHOPIFY_SHOP_URL = {shop_url}")
        print(f"🔍 Debug: SHOPIFY_ACCESS_TOKEN = {'***' + access_token[-4:] if access_token else 'None'}")
        
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
            
            # Get all transactions for this order (pass detailed_order for GraphQL data)
            transactions = self._get_order_transactions(order_data['id'], detailed_order)
            
            # Calculate detailed fees for each transaction
            enhanced_transactions = []
            for tx in transactions:
                try:
                    # Use GraphQL exchange rate data if available, otherwise use enhanced transaction processing
                    if tx.get('_graphql_order_data'):
                        enhanced_tx = self._process_transaction_with_graphql_exchange_rate(tx, detailed_order)
                    else:
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
        """Get detailed order data using GraphQL for accurate financial information"""
        
        print(f"📊 Fetching detailed order data using GraphQL...")
        
        # Use GraphQL to get order with multi-currency data for exchange rate
        query = """
        query getOrderDetails($id: ID!) {
          order(id: $id) {
            id
            name
            createdAt
            totalPriceSet {
              shopMoney {
                amount
                currencyCode
              }
              presentmentMoney {
                amount
                currencyCode
              }
            }
            netPaymentSet {
              shopMoney {
                amount
                currencyCode
              }
              presentmentMoney {
                amount
                currencyCode
              }
            }
            currentSubtotalPriceSet {
              shopMoney {
                amount
                currencyCode
              }
              presentmentMoney {
                amount
                currencyCode
              }
            }
          }
        }
        """
        
        variables = {"id": f"gid://shopify/Order/{order_id}"}
        
        try:
            # Check if GraphQL method exists
            if not hasattr(self.extractor, '_make_graphql_request'):
                print(f"⚠️  GraphQL method not available, using REST API...")
                order_data = self.extractor._make_request(f'orders/{order_id}.json')
                if order_data and 'order' in order_data:
                    return order_data['order']
                return {}
            
            print(f"🔄 Making GraphQL request for order {order_id}...")
            graphql_data = self.extractor._make_graphql_request(query, variables)
            
            print(f"🔍 GraphQL response received: {bool(graphql_data)}")
            if graphql_data:
                print(f"🔍 GraphQL data keys: {list(graphql_data.keys()) if isinstance(graphql_data, dict) else 'Not a dict'}")
                if 'errors' in graphql_data:
                    print(f"❌ GraphQL errors: {graphql_data['errors']}")
                if 'data' in graphql_data:
                    print(f"🔍 GraphQL data.order exists: {bool(graphql_data['data'].get('order'))}")
            
            if graphql_data and 'data' in graphql_data and graphql_data['data'].get('order'):
                order = graphql_data['data']['order']
                print(f"✅ Retrieved order data via GraphQL: {order.get('name')}")
                return order
            else:
                print(f"⚠️  GraphQL failed, falling back to REST API...")
                # Fallback to REST API
                order_data = self.extractor._make_request(f'orders/{order_id}.json')
                if order_data and 'order' in order_data:
                    return order_data['order']
                    
        except Exception as e:
            print(f"❌ GraphQL request failed: {e}, falling back to REST API...")
            # Fallback to REST API
            order_data = self.extractor._make_request(f'orders/{order_id}.json')
            if order_data and 'order' in order_data:
                return order_data['order']
        
        return {}
    
    def _get_order_transactions(self, order_id: str, order_data: Dict = None) -> List[Dict]:
        """Get all transactions for an order via REST API (GraphQL doesn't have transaction details)"""
        
        print(f"💳 Fetching transactions via REST API...")
        
        transactions_data = self.extractor._make_request(f'orders/{order_id}/transactions.json')
        
        if transactions_data and transactions_data.get('transactions'):
            # Filter to only capture/sale transactions (not authorization)
            capture_transactions = []
            for tx in transactions_data['transactions']:
                if tx.get('kind') in ['capture', 'sale']:
                    # Enhance transaction with GraphQL exchange rate data if available
                    if order_data:
                        tx['_graphql_order_data'] = order_data
                    capture_transactions.append(tx)
            
            print(f"✅ Found {len(transactions_data['transactions'])} total transactions, {len(capture_transactions)} capture/sale transactions")
            return capture_transactions
        
        print(f"⚠️  No transactions found for order")
        return []
    
    def _process_transaction_with_graphql_exchange_rate(self, tx: Dict, order: Dict) -> Dict:
        """Process REST transaction data enhanced with GraphQL exchange rate information"""
        
        print(f"   🔄 Processing transaction {tx.get('id', 'unknown')} with GraphQL exchange rates")
        
        # Get basic transaction data from REST API
        gross_amount_usd = float(tx.get('amount', 0))
        currency = tx.get('currency', 'USD')
        
        # Get GraphQL order data for exchange rates
        graphql_order = tx.get('_graphql_order_data', {})
        
        # Extract exchange rate from GraphQL totalPriceSet
        total_price_set = graphql_order.get('totalPriceSet', {})
        shop_money = total_price_set.get('shopMoney', {})
        presentment_money = total_price_set.get('presentmentMoney', {})
        
        # Calculate actual exchange rate from GraphQL data
        if (shop_money.get('currencyCode') == 'EUR' and 
            presentment_money.get('currencyCode') == 'USD'):
            
            total_usd = float(presentment_money.get('amount', 0))
            total_eur = float(shop_money.get('amount', 0))
            
            if total_usd > 0:
                # Use the actual exchange rate from the order
                exchange_rate = total_eur / total_usd
                gross_amount_eur = gross_amount_usd * exchange_rate
                
                print(f"   💱 Using GraphQL exchange rate: {exchange_rate:.6f}")
                print(f"   💰 USD ${gross_amount_usd:.2f} → EUR €{gross_amount_eur:.2f}")
            else:
                # Fallback to basic calculation
                exchange_rate = 0.85
                gross_amount_eur = gross_amount_usd * exchange_rate
                print(f"   ⚠️  Using fallback exchange rate: {exchange_rate:.6f}")
        else:
            # Fallback for non-multi-currency or missing data
            exchange_rate = 0.85
            gross_amount_eur = gross_amount_usd * exchange_rate
            print(f"   ⚠️  Using fallback exchange rate: {exchange_rate:.6f}")
        
        # Calculate fees using your specific Shopify fee structure
        shopify_payment_fee = (gross_amount_eur * 0.029) + 0.25
        
        # Currency conversion fee only if converting
        currency_conversion_fee = 0
        if currency != 'EUR' and gross_amount_usd != gross_amount_eur:
            currency_conversion_fee = gross_amount_eur * 0.019
        
        # No VAT on fees in your setup
        shopify_payment_vat = 0
        currency_conversion_vat = 0
        transaction_fee = 0
        
        total_fees = shopify_payment_fee + currency_conversion_fee
        net_amount = gross_amount_eur - total_fees
        
        # Create enhanced transaction data
        enhanced_tx = {
            'transaction_id': str(tx.get('id', '')),
            'order_id': str(order.get('id', '')),
            'order_number': str(order.get('name', '')),
            'created_at': str(tx.get('created_at', '')),
            'kind': str(tx.get('kind', '')),
            'status': str(tx.get('status', '')),
            'gross_amount': gross_amount_usd,  # For backward compatibility
            'gross_amount_usd': gross_amount_usd,
            'gross_amount_eur': round(gross_amount_eur, 2),
            'currency': str(currency),
            'gateway': str(tx.get('gateway', 'unknown')),
            'exchange_rate': round(exchange_rate, 6),
            'shopify_payment_fee': round(shopify_payment_fee, 2),
            'shopify_payment_vat': round(shopify_payment_vat, 2),
            'currency_conversion_fee': round(currency_conversion_fee, 2),
            'currency_conversion_vat': round(currency_conversion_vat, 2),
            'transaction_fee': round(transaction_fee, 2),
            'total_fees': round(total_fees, 2),
            'net_amount': round(net_amount, 2),
            'data_source': 'rest_api_with_graphql_exchange_rate'
        }
        
        print(f"   ✅ Transaction processed with GraphQL exchange rate")
        
        return enhanced_tx
    
    def _process_graphql_transaction(self, tx: Dict, order: Dict) -> Dict:
        """Process GraphQL transaction data with accurate exchange rates and fees"""
        
        print(f"   🔄 Processing GraphQL transaction {tx.get('id', 'unknown')}")
        
        # Extract amounts from GraphQL amountSet structure
        amount_set = tx.get('amountSet', {})
        shop_money = amount_set.get('shopMoney', {})
        presentment_money = amount_set.get('presentmentMoney', {})
        
        # Get actual amounts
        gross_amount_eur = float(shop_money.get('amount', 0)) if shop_money.get('currencyCode') == 'EUR' else 0
        gross_amount_usd = float(presentment_money.get('amount', 0)) if presentment_money.get('currencyCode') == 'USD' else 0
        
        # Calculate actual exchange rate from Shopify's conversion
        exchange_rate = gross_amount_eur / gross_amount_usd if gross_amount_usd > 0 else 0
        
        # Process fees from GraphQL
        total_fees = 0
        shopify_payment_fee = 0
        currency_conversion_fee = 0
        shopify_payment_vat = 0
        currency_conversion_vat = 0
        transaction_fee = 0
        
        fees = tx.get('fees', [])
        for fee in fees:
            fee_amount_set = fee.get('amountSet', {})
            fee_shop_money = fee_amount_set.get('shopMoney', {})
            fee_amount = float(fee_shop_money.get('amount', 0))
            fee_type = fee.get('type', '').lower()
            
            if 'payment' in fee_type:
                shopify_payment_fee += fee_amount
            elif 'conversion' in fee_type or 'currency' in fee_type:
                currency_conversion_fee += fee_amount
            elif 'vat' in fee_type and 'payment' in fee_type:
                shopify_payment_vat += fee_amount
            elif 'vat' in fee_type and ('conversion' in fee_type or 'currency' in fee_type):
                currency_conversion_vat += fee_amount
            else:
                transaction_fee += fee_amount
            
            total_fees += fee_amount
        
        # If no fees from GraphQL, calculate using Shopify's actual rates
        if total_fees == 0 and gross_amount_eur > 0:
            # Use your specific Shopify fee structure
            shopify_payment_fee = (gross_amount_eur * 0.029) + 0.25
            
            # Currency conversion fee only if converting
            if gross_amount_usd > 0 and gross_amount_usd != gross_amount_eur:
                currency_conversion_fee = gross_amount_eur * 0.019
            
            # No VAT on fees in your setup
            shopify_payment_vat = 0
            currency_conversion_vat = 0
            transaction_fee = 0
            
            total_fees = shopify_payment_fee + currency_conversion_fee
        
        net_amount = gross_amount_eur - total_fees
        
        # Create enhanced transaction data
        enhanced_tx = {
            'transaction_id': str(tx.get('id', '')),
            'order_id': str(order.get('id', '')),
            'order_number': str(order.get('name', '')),
            'created_at': str(tx.get('createdAt', '')),
            'kind': str(tx.get('kind', '')),
            'status': str(tx.get('status', '')),
            'gross_amount': gross_amount_usd,  # For backward compatibility
            'gross_amount_usd': gross_amount_usd,
            'gross_amount_eur': gross_amount_eur,
            'currency': str(presentment_money.get('currencyCode', 'USD')),
            'gateway': str(tx.get('gateway', 'unknown')),
            'exchange_rate': round(exchange_rate, 6),
            'shopify_payment_fee': round(shopify_payment_fee, 2),
            'shopify_payment_vat': round(shopify_payment_vat, 2),
            'currency_conversion_fee': round(currency_conversion_fee, 2),
            'currency_conversion_vat': round(currency_conversion_vat, 2),
            'transaction_fee': round(transaction_fee, 2),
            'total_fees': round(total_fees, 2),
            'net_amount': round(net_amount, 2),
            'data_source': 'graphql_api'
        }
        
        print(f"   ✅ GraphQL transaction processed: USD ${gross_amount_usd:.2f} → EUR €{gross_amount_eur:.2f} (rate: {exchange_rate:.6f})")
        
        return enhanced_tx
    
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
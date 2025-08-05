#!/usr/bin/env python3
"""
Enhanced Financial Analytics Extractor
Captures detailed fee breakdowns, currency conversion, and multi-perspective financial data:
1. Sales Performance (order creation date based)
2. Cash Flow (payment processing date based) 
3. Settlement Analytics (payout date based with detailed fees)
4. Currency conversion tracking
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class EnhancedFinancialAnalyticsExtractor:
    """Enhanced extractor with detailed fee breakdown and currency conversion"""
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.base_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Shopify"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Shopify API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Shopify request failed: {e}")
            return None
    
    def extract_multi_perspective_financial_data(self, date: datetime) -> Dict:
        """Extract financial data from multiple perspectives"""
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"💰 Extracting multi-perspective financial data for {date_str}")
        
        return {
            'date': date_str,
            'sales_performance': self._extract_sales_performance(date),
            'cash_flow': self._extract_cash_flow(date),
            'settlement_analytics': self._extract_settlement_analytics(date),
            'fee_breakdown': self._extract_detailed_fees(date),
            'currency_conversion': self._extract_currency_conversions(date)
        }
    
    def _extract_sales_performance(self, date: datetime) -> Dict:
        """Extract sales performance - orders created on specific date"""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Convert to timezone-aware dates
        local_tz = timezone(timedelta(hours=2))  # Adjust to your timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)
        
        print(f"   📊 Sales Performance: Orders created {date.strftime('%Y-%m-%d')}")
        
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250,
            'fields': 'id,order_number,created_at,total_price,currency,financial_status,total_discounts,total_tax,shipping_lines'
        })
        
        if not orders_data or not orders_data.get('orders'):
            return {'orders': [], 'summary': {'count': 0, 'gross_sales': 0, 'net_sales': 0}}
        
        orders = orders_data['orders']
        enhanced_orders = []
        
        total_gross = 0
        total_net = 0
        
        for order in orders:
            gross_amount = float(order.get('total_price', 0))
            discounts = float(order.get('total_discounts', 0))
            tax = float(order.get('total_tax', 0))
            
            # Calculate shipping
            shipping_amount = 0
            shipping_lines = order.get('shipping_lines', [])
            for shipping in shipping_lines:
                shipping_amount += float(shipping.get('price', 0))
            
            net_amount = gross_amount - discounts
            
            enhanced_order = {
                'order_id': str(order.get('id')),
                'order_number': order.get('order_number'),
                'created_at': order.get('created_at'),
                'gross_amount': gross_amount,
                'discounts': discounts,
                'tax': tax,
                'shipping': shipping_amount,
                'net_amount': net_amount,
                'currency': order.get('currency', 'USD'),
                'financial_status': order.get('financial_status', 'unknown')
            }
            
            enhanced_orders.append(enhanced_order)
            total_gross += gross_amount
            total_net += net_amount
        
        return {
            'orders': enhanced_orders,
            'summary': {
                'count': len(orders),
                'gross_sales': round(total_gross, 2),
                'net_sales': round(total_net, 2),
                'total_discounts': round(sum(o['discounts'] for o in enhanced_orders), 2),
                'total_shipping': round(sum(o['shipping'] for o in enhanced_orders), 2)
            }
        }
    
    def _extract_cash_flow(self, date: datetime) -> Dict:
        """Extract cash flow - payments processed on specific date"""
        
        print(f"   💳 Cash Flow: Payments processed {date.strftime('%Y-%m-%d')}")
        
        # Get orders and their transactions for the date range
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # This gets orders, then we'll filter transactions by processing date
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': (start_date - timedelta(days=7)).isoformat(),  # Look back 7 days
            'created_at_max': (end_date + timedelta(days=7)).isoformat(),    # Look forward 7 days
            'limit': 250
        })
        
        if not orders_data or not orders_data.get('orders'):
            return {'transactions': [], 'summary': {'count': 0, 'total_processed': 0}}
        
        transactions_processed = []
        total_processed = 0
        
        target_date_str = date.strftime('%Y-%m-%d')
        
        for order in orders_data['orders']:
            order_id = order.get('id')
            
            # Get transactions for this order
            transactions_data = self._make_request(f'orders/{order_id}/transactions.json')
            
            if transactions_data and transactions_data.get('transactions'):
                for transaction in transactions_data['transactions']:
                    tx_created = transaction.get('created_at', '')
                    
                    # Check if transaction was processed on target date
                    if tx_created and tx_created.startswith(target_date_str):
                        enhanced_tx = self._enhance_transaction_with_fees(transaction, order)
                        transactions_processed.append(enhanced_tx)
                        total_processed += enhanced_tx.get('gross_amount', 0)
        
        return {
            'transactions': transactions_processed,
            'summary': {
                'count': len(transactions_processed),
                'total_processed': round(total_processed, 2)
            }
        }
    
    def _extract_settlement_analytics(self, date: datetime) -> Dict:
        """Extract settlement analytics - actual payouts with detailed fees"""
        
        print(f"   🏦 Settlement Analytics: Payouts for {date.strftime('%Y-%m-%d')}")
        
        # Get payouts/disputes/balance transactions
        # Note: This requires additional Shopify permissions
        try:
            # Get balance transactions (payouts, fees, etc.)
            balance_data = self._make_request('shopify_payments/balance/transactions.json', {
                'payout_date': date.strftime('%Y-%m-%d')
            })
            
            if balance_data and balance_data.get('transactions'):
                return self._process_balance_transactions(balance_data['transactions'])
            
        except Exception as e:
            print(f"   ⚠️  Settlement data requires Shopify Payments API access: {e}")
        
        # Fallback: Estimate settlements from transactions
        return self._estimate_settlements_from_transactions(date)
    
    def _extract_detailed_fees(self, date: datetime) -> Dict:
        """Extract detailed fee breakdown per transaction"""
        
        print(f"   💸 Fee Breakdown: Detailed fees for {date.strftime('%Y-%m-%d')}")
        
        fee_breakdown = {
            'shopify_payment_fees': [],
            'currency_conversion_fees': [],
            'transaction_fees': [],
            'vat_on_fees': [],
            'total_fees': 0
        }
        
        # Get transactions and calculate detailed fees
        cash_flow_data = self._extract_cash_flow(date)
        
        for transaction in cash_flow_data['transactions']:
            fees = self._calculate_detailed_transaction_fees(transaction)
            
            fee_breakdown['shopify_payment_fees'].append(fees['shopify_payment_fee'])
            fee_breakdown['currency_conversion_fees'].append(fees['currency_conversion_fee'])
            fee_breakdown['transaction_fees'].append(fees['transaction_fee'])
            fee_breakdown['vat_on_fees'].append(fees['vat_on_fees'])
            fee_breakdown['total_fees'] += fees['total_fees']
        
        return fee_breakdown
    
    def _extract_currency_conversions(self, date: datetime) -> Dict:
        """Extract currency conversion details"""
        
        print(f"   💱 Currency Conversions: Exchange rates for {date.strftime('%Y-%m-%d')}")
        
        conversions = {
            'usd_to_eur_transactions': [],
            'exchange_rates_used': {},
            'conversion_fees': 0,
            'total_converted_amount': 0
        }
        
        # Get transactions with currency conversion
        cash_flow_data = self._extract_cash_flow(date)
        
        for transaction in cash_flow_data['transactions']:
            if transaction.get('currency') != 'EUR':  # Your payout currency
                conversion_data = self._get_currency_conversion_details(transaction)
                if conversion_data:
                    conversions['usd_to_eur_transactions'].append(conversion_data)
        
        return conversions
    
    def _enhance_transaction_with_fees(self, transaction: Dict, order: Dict) -> Dict:
        """Enhance transaction with detailed fee breakdown"""
        
        base_transaction = {
            'transaction_id': str(transaction.get('id', '')),
            'order_id': str(order.get('id', '')),
            'order_number': order.get('order_number', ''),
            'created_at': transaction.get('created_at', ''),
            'kind': transaction.get('kind', ''),
            'status': transaction.get('status', ''),
            'gross_amount': float(transaction.get('amount', 0)),
            'currency': transaction.get('currency', 'USD'),
            'gateway': transaction.get('gateway', 'unknown')
        }
        
        # Add detailed fee breakdown
        fees = self._calculate_detailed_transaction_fees(transaction)
        base_transaction.update(fees)
        
        # Add currency conversion if applicable
        if base_transaction['currency'] != 'EUR':
            conversion = self._get_currency_conversion_details(transaction)
            if conversion:
                base_transaction.update(conversion)
        
        return base_transaction
    
    def _calculate_detailed_transaction_fees(self, transaction: Dict) -> Dict:
        """Calculate detailed fee breakdown like Shopify shows"""
        
        gross_amount = float(transaction.get('amount', 0))
        currency = transaction.get('currency', 'USD')
        gateway = transaction.get('gateway', 'shopify_payments')
        
        # Base Shopify Payment fee (2.9% + €0.30 or $0.30)
        if currency == 'EUR':
            base_rate = 0.029
            fixed_fee = 0.30
        else:
            base_rate = 0.029
            fixed_fee = 0.30
        
        shopify_payment_fee = (gross_amount * base_rate) + fixed_fee
        
        # Currency conversion fee (additional 1% if converting)
        currency_conversion_fee = 0
        if currency != 'EUR':
            currency_conversion_fee = gross_amount * 0.01
        
        # Transaction fee (varies by gateway)
        transaction_fee = 0
        if 'paypal' in gateway.lower():
            transaction_fee = gross_amount * 0.005  # Additional PayPal fee
        
        # VAT on fees (varies by country, assuming EU 21%)
        total_fees_before_vat = shopify_payment_fee + currency_conversion_fee + transaction_fee
        vat_on_fees = total_fees_before_vat * 0.21
        
        total_fees = total_fees_before_vat + vat_on_fees
        net_amount = gross_amount - total_fees
        
        return {
            'shopify_payment_fee': round(shopify_payment_fee, 2),
            'currency_conversion_fee': round(currency_conversion_fee, 2),
            'transaction_fee': round(transaction_fee, 2),
            'vat_on_fees': round(vat_on_fees, 2),
            'total_fees': round(total_fees, 2),
            'net_amount': round(net_amount, 2)
        }
    
    def _get_currency_conversion_details(self, transaction: Dict) -> Optional[Dict]:
        """Get currency conversion details"""
        
        gross_amount = float(transaction.get('amount', 0))
        from_currency = transaction.get('currency', 'USD')
        
        if from_currency == 'EUR':
            return None
        
        # Example: $36.77 USD → €32.21 EUR
        # You'd need to get the actual exchange rate used by Shopify
        # This is an approximation
        
        if from_currency == 'USD':
            # Approximate EUR/USD rate (you'd get this from Shopify or ECB API)
            exchange_rate = 0.876  # Example rate
            converted_amount = gross_amount * exchange_rate
            
            return {
                'original_amount': gross_amount,
                'original_currency': from_currency,
                'converted_amount': round(converted_amount, 2),
                'converted_currency': 'EUR',
                'exchange_rate': exchange_rate,
                'conversion_date': transaction.get('created_at', '')
            }
        
        return None
    
    def _process_balance_transactions(self, balance_transactions: List[Dict]) -> Dict:
        """Process Shopify balance transactions (requires Shopify Payments API)"""
        
        settlements = {
            'payouts': [],
            'fees': [],
            'adjustments': [],
            'total_payout': 0,
            'total_fees': 0
        }
        
        for tx in balance_transactions:
            tx_type = tx.get('type', '')
            amount = float(tx.get('amount', 0))
            
            if tx_type == 'payout':
                settlements['payouts'].append(tx)
                settlements['total_payout'] += amount
            elif tx_type in ['fee', 'adjustment']:
                settlements['fees'].append(tx)
                settlements['total_fees'] += abs(amount)
        
        return settlements
    
    def _estimate_settlements_from_transactions(self, date: datetime) -> Dict:
        """Estimate settlements when balance API is not available"""
        
        cash_flow_data = self._extract_cash_flow(date)
        
        total_gross = sum(tx.get('gross_amount', 0) for tx in cash_flow_data['transactions'])
        total_fees = sum(tx.get('total_fees', 0) for tx in cash_flow_data['transactions'])
        estimated_payout = total_gross - total_fees
        
        return {
            'estimated_payout': round(estimated_payout, 2),
            'estimated_fees': round(total_fees, 2),
            'note': 'Estimated from transactions (balance API not available)'
        }
    
    def test_connection(self) -> bool:
        """Test Shopify connection"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception:
            return False

def main():
    """Test the enhanced financial analytics extractor"""
    
    print("🚀 Enhanced Financial Analytics Extractor")
    print("=" * 60)
    
    extractor = EnhancedFinancialAnalyticsExtractor()
    
    # Test connection
    if not extractor.test_connection():
        print("❌ Cannot connect to Shopify API")
        return
    
    # Extract multi-perspective data for July 29
    test_date = datetime.strptime('2025-07-29', '%Y-%m-%d')
    data = extractor.extract_multi_perspective_financial_data(test_date)
    
    # Print summary
    print(f"\n📊 MULTI-PERSPECTIVE FINANCIAL ANALYSIS")
    print("=" * 50)
    
    sales = data['sales_performance']['summary']
    print(f"📈 Sales Performance (Orders Created July 29):")
    print(f"   Orders: {sales['count']}")
    print(f"   Gross Sales: €{sales['gross_sales']:,.2f}")
    print(f"   Net Sales: €{sales['net_sales']:,.2f}")
    
    cash = data['cash_flow']['summary']
    print(f"\n💰 Cash Flow (Payments Processed July 29):")
    print(f"   Transactions: {cash['count']}")
    print(f"   Total Processed: €{cash['total_processed']:,.2f}")
    
    fees = data['fee_breakdown']
    print(f"\n💸 Fee Breakdown:")
    print(f"   Total Fees: €{fees['total_fees']:,.2f}")
    
    print(f"\n✅ Enhanced financial analytics extraction completed!")

if __name__ == "__main__":
    main()
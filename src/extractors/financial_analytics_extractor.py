import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class FinancialAnalyticsExtractor:
    """Extract comprehensive financial analytics data from Shopify API"""
    
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
    
    def _calculate_processing_fee(self, amount: float, payment_method: str, gateway: str) -> float:
        """Calculate estimated processing fee based on payment method and gateway"""
        # Standard Shopify Payments rates (adjust based on your actual rates)
        fee_rates = {
            'shopify_payments': {
                'credit_card': 0.029,  # 2.9% + $0.30
                'paypal': 0.029,
                'apple_pay': 0.029,
                'google_pay': 0.029,
                'shop_pay': 0.029
            },
            'paypal': {
                'paypal': 0.034,  # 3.4% + $0.30 for external PayPal
            }
        }
        
        gateway_rates = fee_rates.get(gateway, {'credit_card': 0.029})
        rate = gateway_rates.get(payment_method, 0.029)
        
        return (amount * rate) + 0.30  # Base rate + fixed fee
    
    def _determine_risk_level(self, transaction: Dict) -> str:
        """Determine transaction risk level based on various factors"""
        # Simple risk assessment - can be enhanced
        gateway = transaction.get('gateway', '').lower()
        status = transaction.get('status', '').lower()
        amount = float(transaction.get('amount', 0))
        
        # High risk indicators
        if status in ['pending', 'error', 'failure']:
            return 'high'
        elif amount > 500:  # Large transactions
            return 'medium'
        elif gateway in ['manual', 'cash_on_delivery']:
            return 'medium'
        else:
            return 'low'
    
    def _get_customer_country(self, order_id: str) -> str:
        """Get customer country from order"""
        try:
            order_data = self._make_request(f'orders/{order_id}.json')
            if order_data and 'order' in order_data:
                order = order_data['order']
                shipping_address = order.get('shipping_address', {})
                billing_address = order.get('billing_address', {})
                
                # Try shipping address first, then billing
                country = shipping_address.get('country') or billing_address.get('country')
                return country or 'Unknown'
        except Exception:
            pass
        return 'Unknown'
    
    def extract_transactions_for_date_range(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Extract all financial transactions for a date range"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        # Convert to timezone-aware dates (CET +02:00)
        local_tz = timezone(timedelta(hours=2))
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)
        
        print(f"💰 Extracting financial analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get orders for the date range first
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if not orders_data or not orders_data.get('orders'):
            print(f"ℹ️  No orders found for the specified date range")
            return []
        
        orders = orders_data['orders']
        print(f"✅ Found {len(orders)} orders to process for transactions")
        
        all_transactions = []
        
        for i, order in enumerate(orders, 1):
            try:
                order_id = order.get('id')
                order_number = order.get('order_number')
                print(f"   Processing order {i}/{len(orders)}: #{order_number}")
                
                # Get transactions for this order
                transactions_data = self._make_request(f'orders/{order_id}/transactions.json')
                
                if not transactions_data or not transactions_data.get('transactions'):
                    print(f"     ⚠️  No transactions found for order #{order_number}")
                    continue
                
                transactions = transactions_data['transactions']
                print(f"     ✅ Found {len(transactions)} transactions")
                
                # Get customer country once for all transactions in this order
                customer_country = self._get_customer_country(order_id)
                
                for transaction in transactions:
                    try:
                        # Basic transaction information
                        transaction_id = str(transaction.get('id', ''))
                        created_at = transaction.get('created_at', '')
                        
                        # Financial details
                        gross_amount = float(transaction.get('amount', 0))
                        currency = transaction.get('currency', 'USD')
                        
                        # Payment information
                        gateway = transaction.get('gateway', 'unknown')
                        kind = transaction.get('kind', 'sale')  # sale, refund, authorization, capture, void
                        status = transaction.get('status', 'unknown')
                        
                        # Determine payment method from gateway
                        payment_method = 'credit_card'  # Default
                        if 'paypal' in gateway.lower():
                            payment_method = 'paypal'
                        elif 'apple' in gateway.lower():
                            payment_method = 'apple_pay'
                        elif 'google' in gateway.lower():
                            payment_method = 'google_pay'
                        elif 'shop' in gateway.lower():
                            payment_method = 'shop_pay'
                        
                        # Calculate processing fee
                        processing_fee = 0
                        if kind == 'sale' and status == 'success':
                            processing_fee = self._calculate_processing_fee(gross_amount, payment_method, gateway)
                        
                        # Net amount after fees
                        net_amount = gross_amount - processing_fee
                        
                        # Risk assessment
                        risk_level = self._determine_risk_level(transaction)
                        
                        # Additional transaction details
                        authorization_code = transaction.get('authorization', '')
                        
                        # Try multiple sources for gateway reference
                        gateway_reference = ''
                        if transaction.get('receipt'):
                            receipt = transaction.get('receipt', {})
                            gateway_reference = (receipt.get('transaction_id') or 
                                               receipt.get('reference') or 
                                               receipt.get('authorization_code') or '')
                        
                        # Fallback to transaction ID if no gateway reference
                        if not gateway_reference:
                            gateway_reference = transaction_id
                        
                        # Device and location info (limited from transaction data)
                        device_type = 'unknown'  # Would need additional data source
                        ip_country = customer_country  # Using customer country as proxy
                        
                        transaction_data = {
                            'transaction_id': transaction_id,
                            'order_reference': str(order_id),
                            'order_number': order_number,
                            'date': created_at,
                            'transaction_type': kind,
                            'gross_amount': gross_amount,
                            'processing_fee': processing_fee,
                            'net_amount': net_amount,
                            'currency': currency,
                            'exchange_rate': 1.0,  # Would need currency conversion service
                            'payment_method': payment_method,
                            'payment_gateway': gateway,
                            'card_type': 'unknown',  # Not available in basic transaction data
                            'last_4_digits': '',  # Not available in basic transaction data
                            'status': status,
                            'risk_level': risk_level,
                            'fraud_score': 0,  # Would need Shopify fraud analysis
                            'avs_result': 'unknown',  # Address verification
                            'cvv_result': 'unknown',  # CVV verification
                            'customer_country': customer_country,
                            'ip_country': ip_country,
                            'device_type': device_type,
                            'browser': 'unknown',
                            'gateway_reference': gateway_reference,
                            'authorization_code': authorization_code,
                            'settlement_date': '',  # Would need additional API calls
                            'disputed': False  # Would need to check for disputes
                        }
                        
                        all_transactions.append(transaction_data)
                        
                    except Exception as e:
                        print(f"     ❌ Error processing transaction {transaction.get('id', 'unknown')}: {e}")
                        continue
                
            except Exception as e:
                print(f"   ❌ Error processing order #{order.get('order_number', 'unknown')}: {e}")
                continue
        
        print(f"✅ Successfully processed {len(all_transactions)} transactions")
        return all_transactions
    
    def extract_single_date(self, date: datetime = None) -> List[Dict]:
        """Extract transactions for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self.extract_transactions_for_date_range(start_date, end_date)
    
    def test_connection(self) -> bool:
        """Test if connection to Shopify is working"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception as e:
            print(f"❌ Shopify connection test failed: {e}")
            return False
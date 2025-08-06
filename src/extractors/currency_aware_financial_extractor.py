import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class CurrencyAwareFinancialExtractor:
    """
    Currency-Aware Financial Analytics Extractor
    
    Provides comprehensive financial data with proper currency conversion tracking:
    1. Customer currency amounts (what customer paid - USD)
    2. Shop currency amounts (what merchant received - EUR) 
    3. Exchange rate calculation and analysis
    4. Proper order-to-payout reconciliation
    """
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        print("💱 Currency-Aware Financial Analytics: USD→EUR Conversion Tracking")
    
    def _execute_graphql_query(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Execute GraphQL query against Shopify API"""
        try:
            payload = {'query': query, 'variables': variables or {}}
            response = requests.post(self.graphql_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errors'):
                    print(f"❌ GraphQL errors: {result['errors']}")
                    return None
                return result
            else:
                print(f"❌ GraphQL API error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ GraphQL request failed: {e}")
            return None
    
    def get_payout_data(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Get payout-level data with currency information"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        print(f"💰 Getting payout data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        query = """
        query getPayoutsInRange($first: Int!) {
            shopifyPaymentsAccount {
                payouts(first: $first) {
                    edges {
                        node {
                            id
                            legacyResourceId
                            issuedAt
                            status
                            transactionType
                            net {
                                amount
                                currencyCode
                            }
                            summary {
                                chargesFee { amount currencyCode }
                                chargesGross { amount currencyCode }
                                refundsFee { amount currencyCode }
                                refundsFeeGross { amount currencyCode }
                                adjustmentsFee { amount currencyCode }
                                adjustmentsGross { amount currencyCode }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self._execute_graphql_query(query, {"first": 100})
        
        if not result or not result.get('data'):
            print("❌ No payout data retrieved")
            return []
        
        edges = result.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {}).get('edges', [])
        
        # Filter by date range
        payouts = []
        
        # Ensure timezone awareness
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        for edge in edges:
            payout = edge['node']
            issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
            
            if start_date <= issued_date <= end_date:
                payout_data = self._transform_payout_data(payout)
                payouts.append(payout_data)
        
        print(f"✅ Found {len(payouts)} payouts")
        return payouts
    
    def _transform_payout_data(self, payout: Dict) -> Dict:
        """Transform payout data with enhanced currency metadata"""
        summary = payout['summary']
        issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
        
        return {
            'payout_id': payout['legacyResourceId'],
            'settlement_date': issued_date.isoformat(),
            'settlement_date_formatted': issued_date.strftime('%Y-%m-%d'),
            'payout_status': payout['status'],
            'gross_sales': float(summary['chargesGross']['amount']),
            'processing_fee': float(summary['chargesFee']['amount']),
            'net_amount': float(payout['net']['amount']),
            'payout_currency': summary['chargesGross']['currencyCode'],  # Should be EUR
            'fee_rate_percent': round((float(summary['chargesFee']['amount']) / float(summary['chargesGross']['amount']) * 100), 2) if float(summary['chargesGross']['amount']) > 0 else 0,
            'refunds_gross': float(summary['refundsFeeGross']['amount']),
            'adjustments_gross': float(summary['adjustmentsGross']['amount']),
        }
    
    def get_orders_with_currency_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get orders using GraphQL to capture both customer and shop currency amounts"""
        
        print(f"📦 Getting order currency data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Extend date range to account for payout timing
        search_start = start_date - timedelta(days=3)
        search_end = end_date + timedelta(days=1)
        
        # Format dates for GraphQL
        search_start_iso = search_start.isoformat()
        search_end_iso = search_end.isoformat()
        
        query = """
        query getOrdersWithCurrency($first: Int!) {
            orders(first: $first) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        processedAt
                        presentmentCurrencyCode
                        currencyCode
                        displayFinancialStatus
                        customer {
                            id
                            email
                        }
                        shippingAddress {
                            country
                            city
                        }
                        totalPriceSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        subtotalPriceSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalTaxSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalShippingPriceSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalDiscountsSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        paymentGatewayNames
                        lineItems(first: 10) {
                            edges {
                                node {
                                    id
                                    quantity
                                    product {
                                        productType
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "first": 250
        }
        
        result = self._execute_graphql_query(query, variables)
        
        if not result or not result.get('data'):
            print("❌ No order data retrieved")
            return []
        
        edges = result.get('data', {}).get('orders', {}).get('edges', [])
        print(f"📊 Found {len(edges)} orders with currency data")
        
        # Transform to detailed order records with currency conversion
        detailed_orders = []
        
        for edge in edges:
            order = edge['node']
            order_details = self._extract_currency_aware_order_details(order)
            if order_details:
                detailed_orders.append(order_details)
        
        print(f"✅ Processed {len(detailed_orders)} currency-aware order records")
        return detailed_orders
    
    def _extract_currency_aware_order_details(self, order: Dict) -> Optional[Dict]:
        """Extract comprehensive order details with currency conversion data"""
        try:
            # Basic order info
            order_id = order['id'].split('/')[-1]  # Extract numeric ID from GraphQL ID
            order_number = order['name'].replace('#', '')  # Remove # from name
            created_at = order['createdAt']
            
            # Customer info
            customer = order.get('customer', {})
            customer_email = customer.get('email', 'Guest') if customer else 'Guest'
            customer_id = customer.get('id', '').split('/')[-1] if customer and customer.get('id') else ''
            
            # Address info
            shipping_address = order.get('shippingAddress', {})
            customer_country = shipping_address.get('country', 'Unknown') if shipping_address else 'Unknown'
            customer_city = shipping_address.get('city', 'Unknown') if shipping_address else 'Unknown'
            
            # Currency codes
            customer_currency = order.get('presentmentCurrencyCode', 'USD')
            shop_currency = order.get('currencyCode', 'EUR')
            
            # Dual currency amounts
            total_price_set = order.get('totalPriceSet', {})
            customer_total = float(total_price_set.get('presentmentMoney', {}).get('amount', 0))
            shop_total = float(total_price_set.get('shopMoney', {}).get('amount', 0))
            
            subtotal_set = order.get('subtotalPriceSet', {})
            customer_subtotal = float(subtotal_set.get('presentmentMoney', {}).get('amount', 0))
            shop_subtotal = float(subtotal_set.get('shopMoney', {}).get('amount', 0))
            
            tax_set = order.get('totalTaxSet', {})
            customer_tax = float(tax_set.get('presentmentMoney', {}).get('amount', 0))
            shop_tax = float(tax_set.get('shopMoney', {}).get('amount', 0))
            
            shipping_set = order.get('totalShippingPriceSet', {})
            customer_shipping = float(shipping_set.get('presentmentMoney', {}).get('amount', 0)) if shipping_set else 0
            shop_shipping = float(shipping_set.get('shopMoney', {}).get('amount', 0)) if shipping_set else 0
            
            discounts_set = order.get('totalDiscountsSet', {})
            customer_discounts = float(discounts_set.get('presentmentMoney', {}).get('amount', 0))
            shop_discounts = float(discounts_set.get('shopMoney', {}).get('amount', 0))
            
            # Calculate exchange rate
            exchange_rate = 0
            if customer_total > 0 and shop_total > 0:
                exchange_rate = customer_total / shop_total
            
            # Payment gateway
            payment_gateways = order.get('paymentGatewayNames', [])
            payment_gateway = payment_gateways[0] if payment_gateways else 'unknown'
            
            # Line items info
            line_items = order.get('lineItems', {}).get('edges', [])
            total_quantity = sum(int(item['node'].get('quantity', 0)) for item in line_items)
            
            # Product type (first item)
            product_type = 'Unknown'
            if line_items and line_items[0]['node'].get('product', {}).get('productType'):
                product_type = line_items[0]['node']['product']['productType']
            
            # Parse creation date
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            return {
                # Order identifiers
                'order_id': order_id,
                'order_number': order_number,
                'created_at': created_at,
                'created_date_formatted': created_date.strftime('%Y-%m-%d'),
                'created_time_formatted': created_date.strftime('%H:%M:%S'),
                
                # Customer currency amounts (what customer paid)
                'customer_currency': customer_currency,
                'customer_total': customer_total,
                'customer_subtotal': customer_subtotal,
                'customer_tax': customer_tax,
                'customer_shipping': customer_shipping,
                'customer_discounts': customer_discounts,
                
                # Shop currency amounts (what merchant received)
                'shop_currency': shop_currency,
                'shop_total': shop_total,
                'shop_subtotal': shop_subtotal,
                'shop_tax': shop_tax,
                'shop_shipping': shop_shipping,
                'shop_discounts': shop_discounts,
                
                # Currency conversion
                'exchange_rate': round(exchange_rate, 4),
                'conversion_date': created_date.strftime('%Y-%m-%d'),
                
                # Customer information
                'customer_id': customer_id,
                'customer_email': customer_email,
                'customer_country': customer_country,
                'customer_city': customer_city,
                
                # Payment and product details
                'payment_gateway': payment_gateway,
                'financial_status': order.get('displayFinancialStatus', 'unknown'),
                'total_quantity': total_quantity,
                'product_type': product_type,
                'line_items_count': len(line_items),
                
                # Metadata
                'data_source': 'graphql_orders_currency',
                'extraction_timestamp': datetime.now().isoformat(),
                
                # Placeholder for payout mapping
                'mapped_payout_id': '',
                'estimated_payout_date': ''
            }
            
        except Exception as e:
            print(f"❌ Error processing order {order.get('name', 'unknown')}: {e}")
            return None
    
    def map_orders_to_payouts_with_currency(self, payouts: List[Dict], orders: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Map orders to payouts with currency reconciliation"""
        
        print(f"🔗 Mapping {len(orders)} orders to {len(payouts)} payouts with currency reconciliation")
        
        mapped_orders = []
        payout_order_mapping = []
        
        for payout in payouts:
            payout_id = payout['payout_id']
            payout_date = datetime.fromisoformat(payout['settlement_date'])
            payout_gross_eur = payout['gross_sales']  # EUR amount
            
            print(f"\n   Analyzing payout {payout_id}: €{payout_gross_eur:.2f} EUR")
            
            # Find candidate orders (1-5 days before payout)
            candidate_orders = []
            
            for order in orders:
                order_date = datetime.fromisoformat(order['created_at'])
                days_difference = (payout_date - order_date).days
                
                if 0 <= days_difference <= 5:
                    candidate_orders.append(order)
            
            if not candidate_orders:
                print(f"      ⚠️  No candidate orders found")
                continue
            
            # Sort by date proximity and try to match EUR amounts
            candidate_orders.sort(key=lambda x: abs((payout_date - datetime.fromisoformat(x['created_at'])).days))
            
            # Match orders using shop currency (EUR) amounts
            selected_orders = []
            running_eur_total = 0
            
            for order in candidate_orders:
                shop_total_eur = order['shop_total']  # EUR amount
                
                # Add order if we haven't exceeded payout amount by more than 10%
                if running_eur_total < payout_gross_eur * 1.1:
                    selected_orders.append(order)
                    running_eur_total += shop_total_eur
            
            # Map selected orders to this payout
            total_usd = 0
            total_eur = 0
            
            for order in selected_orders:
                order_copy = order.copy()
                order_copy['mapped_payout_id'] = payout_id
                order_copy['estimated_payout_date'] = payout['settlement_date_formatted']
                mapped_orders.append(order_copy)
                
                total_usd += order['customer_total']
                total_eur += order['shop_total']
                
                # Create mapping record with currency details
                payout_order_mapping.append({
                    'payout_id': payout_id,
                    'payout_date': payout['settlement_date_formatted'],
                    'payout_amount_eur': payout_gross_eur,
                    'order_id': order['order_id'],
                    'order_number': order['order_number'],
                    'order_date': order['created_date_formatted'],
                    'customer_paid_usd': order['customer_total'],
                    'shop_received_eur': order['shop_total'],
                    'exchange_rate': order['exchange_rate'],
                    'days_to_payout': (payout_date - datetime.fromisoformat(order['created_at'])).days,
                    'customer_currency': order['customer_currency'],
                    'shop_currency': order['shop_currency']
                })
            
            avg_rate = (total_usd / total_eur) if total_eur > 0 else 0
            
            print(f"      ✅ Mapped {len(selected_orders)} orders:")
            print(f"         Customer paid: ${total_usd:.2f} USD")
            print(f"         Shop received: €{total_eur:.2f} EUR") 
            print(f"         Payout amount: €{payout_gross_eur:.2f} EUR")
            print(f"         Avg exchange rate: {avg_rate:.4f}")
            print(f"         Currency match: {'✅' if abs(total_eur - payout_gross_eur) < 5 else '⚠️'}")
        
        print(f"\n✅ Mapped {len(mapped_orders)} orders with currency conversion data")
        return mapped_orders, payout_order_mapping
    
    def get_comprehensive_currency_data(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Get comprehensive financial data with currency conversion analysis"""
        
        print(f"💱 COMPREHENSIVE CURRENCY-AWARE FINANCIAL DATA")
        print("=" * 70)
        
        # Get payout data
        payouts = self.get_payout_data(start_date, end_date)
        
        # Get order data with currency info
        orders = self.get_orders_with_currency_data(start_date, end_date)
        
        # Map orders to payouts with currency reconciliation
        mapped_orders, currency_mapping = self.map_orders_to_payouts_with_currency(payouts, orders)
        
        # Calculate currency conversion metrics
        currency_metrics = self._calculate_currency_metrics(mapped_orders, payouts)
        
        return {
            'payouts': payouts,
            'orders': mapped_orders,
            'currency_mapping': currency_mapping,
            'currency_metrics': currency_metrics,
            'summary': {
                'total_payouts': len(payouts),
                'total_orders': len(mapped_orders),
                'total_eur_from_payouts': sum(p['gross_sales'] for p in payouts),
                'total_usd_from_orders': sum(o['customer_total'] for o in mapped_orders),
                'total_eur_from_orders': sum(o['shop_total'] for o in mapped_orders),
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d') if end_date else start_date.strftime('%Y-%m-%d')}"
            }
        }
    
    def _calculate_currency_metrics(self, orders: List[Dict], payouts: List[Dict]) -> Dict:
        """Calculate currency conversion metrics and analysis"""
        
        if not orders:
            return {}
        
        # Exchange rate analysis
        exchange_rates = [o['exchange_rate'] for o in orders if o['exchange_rate'] > 0]
        
        if not exchange_rates:
            return {}
        
        avg_rate = sum(exchange_rates) / len(exchange_rates)
        min_rate = min(exchange_rates)
        max_rate = max(exchange_rates)
        
        # Currency totals
        total_usd = sum(o['customer_total'] for o in orders)
        total_eur_orders = sum(o['shop_total'] for o in orders)
        total_eur_payouts = sum(p['gross_sales'] for p in payouts)
        
        # Conversion accuracy
        conversion_accuracy = (total_eur_orders / total_eur_payouts) if total_eur_payouts > 0 else 0
        
        return {
            'average_exchange_rate': round(avg_rate, 4),
            'min_exchange_rate': round(min_rate, 4),
            'max_exchange_rate': round(max_rate, 4),
            'exchange_rate_volatility': round(max_rate - min_rate, 4),
            'total_customer_usd': round(total_usd, 2),
            'total_shop_eur': round(total_eur_orders, 2),
            'total_payout_eur': round(total_eur_payouts, 2),
            'conversion_accuracy_percent': round(conversion_accuracy * 100, 2),
            'currency_conversion_difference': round(abs(total_eur_orders - total_eur_payouts), 2)
        }
    
    def test_connection(self) -> bool:
        """Test GraphQL connections for both payouts and orders"""
        try:
            # Test payout access
            payout_query = """
            query testPayoutAccess {
                shopifyPaymentsAccount {
                    payouts(first: 1) {
                        edges {
                            node {
                                id
                                status
                            }
                        }
                    }
                }
            }
            """
            
            # Test order currency access
            order_query = """
            query testOrderCurrencyAccess {
                orders(first: 1) {
                    edges {
                        node {
                            id
                            presentmentCurrencyCode
                            currencyCode
                            totalPriceSet {
                                presentmentMoney { amount }
                                shopMoney { amount }
                            }
                        }
                    }
                }
            }
            """
            
            payout_result = self._execute_graphql_query(payout_query)
            order_result = self._execute_graphql_query(order_query)
            
            payout_ok = bool(payout_result and payout_result.get('data', {}).get('shopifyPaymentsAccount'))
            order_ok = bool(order_result and order_result.get('data', {}).get('orders'))
            
            print(f"✅ GraphQL Payouts: {'Connected' if payout_ok else 'Failed'}")
            print(f"✅ GraphQL Orders (Currency): {'Connected' if order_ok else 'Failed'}")
            
            return payout_ok and order_ok
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
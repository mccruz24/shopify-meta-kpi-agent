import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class EnhancedFinancialAnalyticsExtractor:
    """
    Enhanced Financial Analytics Extractor with Order-Level Granularity
    
    Provides both:
    1. Payout-level summaries (settlement view)
    2. Order-level details (transaction granularity)
    3. Order-to-payout mapping
    """
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.rest_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        print("💰 Enhanced Financial Analytics: Payout + Order Granularity")
    
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
    
    def _make_rest_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make REST API request"""
        try:
            url = f"{self.rest_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ REST API error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ REST request failed: {e}")
            return None
    
    def get_payout_data(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Get payout-level data (same as before but enhanced)"""
        
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
        """Transform payout data with enhanced metadata"""
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
            'currency': summary['chargesGross']['currencyCode'],
            'fee_rate_percent': round((float(summary['chargesFee']['amount']) / float(summary['chargesGross']['amount']) * 100), 2) if float(summary['chargesGross']['amount']) > 0 else 0,
            'refunds_gross': float(summary['refundsFeeGross']['amount']),
            'adjustments_gross': float(summary['adjustmentsGross']['amount']),
        }
    
    def get_orders_for_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get individual orders with full financial details"""
        
        print(f"📦 Getting order details from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Extend date range to account for payout timing
        search_start = start_date - timedelta(days=3)  # Orders can be 1-3 days before payout
        search_end = end_date + timedelta(days=1)      # Small buffer
        
        # Use timezone-aware dates
        local_tz = timezone(timedelta(hours=2))  # CET
        search_start = search_start.replace(tzinfo=local_tz)
        search_end = search_end.replace(tzinfo=local_tz)
        
        orders_data = self._make_rest_request('orders.json', {
            'status': 'any',
            'financial_status': 'paid',
            'created_at_min': search_start.isoformat(),
            'created_at_max': search_end.isoformat(),
            'limit': 250
        })
        
        if not orders_data or not orders_data.get('orders'):
            print("❌ No orders found")
            return []
        
        orders = orders_data['orders']
        print(f"📊 Found {len(orders)} orders in extended date range")
        
        # Transform to detailed order records
        detailed_orders = []
        
        for order in orders:
            order_details = self._extract_order_financial_details(order)
            if order_details:
                detailed_orders.append(order_details)
        
        print(f"✅ Processed {len(detailed_orders)} order records")
        return detailed_orders
    
    def _extract_order_financial_details(self, order: Dict) -> Optional[Dict]:
        """Extract comprehensive financial details from an order"""
        try:
            order_id = str(order.get('id'))
            order_number = order.get('order_number')
            created_at = order.get('created_at', '')
            
            # Financial amounts
            total_price = float(order.get('total_price', 0))
            subtotal_price = float(order.get('subtotal_price', 0))
            total_discounts = float(order.get('total_discounts', 0))
            total_tax = float(order.get('total_tax', 0))
            
            # Shipping
            shipping_cost = 0
            shipping_lines = order.get('shipping_lines', [])
            for shipping in shipping_lines:
                shipping_cost += float(shipping.get('price', 0))
            
            # Customer info
            customer = order.get('customer', {})
            customer_email = customer.get('email', 'Guest') if customer else 'Guest'
            customer_id = str(customer.get('id', '')) if customer else ''
            
            # Payment gateway (from first transaction if available)
            payment_gateway = 'unknown'
            gateway_names = order.get('payment_gateway_names', [])
            if gateway_names:
                payment_gateway = gateway_names[0]
            
            # Location info
            shipping_address = order.get('shipping_address', {})
            customer_country = shipping_address.get('country', 'Unknown') if shipping_address else 'Unknown'
            customer_city = shipping_address.get('city', 'Unknown') if shipping_address else 'Unknown'
            
            # Line items summary
            line_items = order.get('line_items', [])
            total_quantity = sum(int(item.get('quantity', 0)) for item in line_items)
            
            # Product categories (first product's type as proxy)
            product_type = 'Unknown'
            if line_items and line_items[0].get('product_type'):
                product_type = line_items[0]['product_type']
            
            # Financial status and fulfillment
            financial_status = order.get('financial_status', 'unknown')
            fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
            
            # Parse creation date
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.now()
            
            return {
                # Order identifiers
                'order_id': order_id,
                'order_number': order_number,
                'created_at': created_at,
                'created_date_formatted': created_date.strftime('%Y-%m-%d'),
                'created_time_formatted': created_date.strftime('%H:%M:%S'),
                
                # Financial details
                'total_price': total_price,
                'subtotal_price': subtotal_price,
                'total_discounts': total_discounts,
                'total_tax': total_tax,
                'shipping_cost': shipping_cost,
                'currency': order.get('currency', 'EUR'),
                
                # Customer information
                'customer_id': customer_id,
                'customer_email': customer_email,
                'customer_country': customer_country,
                'customer_city': customer_city,
                
                # Payment details
                'payment_gateway': payment_gateway,
                'financial_status': financial_status,
                'fulfillment_status': fulfillment_status,
                
                # Product details
                'total_quantity': total_quantity,
                'product_type': product_type,
                'line_items_count': len(line_items),
                
                # Metadata
                'data_source': 'rest_orders',
                'extraction_timestamp': datetime.now().isoformat(),
                
                # Placeholder for payout mapping (filled later)
                'mapped_payout_id': '',
                'estimated_payout_date': ''
            }
            
        except Exception as e:
            print(f"❌ Error processing order {order.get('order_number', 'unknown')}: {e}")
            return None
    
    def map_orders_to_payouts(self, payouts: List[Dict], orders: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Map orders to their corresponding payouts using date and amount heuristics"""
        
        print(f"🔗 Mapping {len(orders)} orders to {len(payouts)} payouts")
        
        mapped_orders = []
        payout_order_mapping = []
        
        for payout in payouts:
            payout_id = payout['payout_id']
            payout_date = datetime.fromisoformat(payout['settlement_date'])
            payout_gross = payout['gross_sales']
            
            # Find orders that likely contributed to this payout
            # Orders are typically 1-3 days before payout settlement
            candidate_orders = []
            
            for order in orders:
                order_date = datetime.fromisoformat(order['created_at'])
                days_difference = (payout_date - order_date).days
                
                # Orders within 0-5 days before payout are candidates
                if 0 <= days_difference <= 5:
                    candidate_orders.append(order)
            
            if not candidate_orders:
                print(f"   ⚠️  No candidate orders found for payout {payout_id}")
                continue
            
            # Try to match order amounts to payout gross
            # Start with orders closest to payout date
            candidate_orders.sort(key=lambda x: abs((payout_date - datetime.fromisoformat(x['created_at'])).days))
            
            # Use simple heuristic: include orders until we reach approximate payout amount
            selected_orders = []
            running_total = 0
            
            for order in candidate_orders:
                if running_total < payout_gross * 1.1:  # Allow 10% buffer for timing differences
                    selected_orders.append(order)
                    running_total += order['total_price']
            
            # Map selected orders to this payout
            for order in selected_orders:
                order_copy = order.copy()
                order_copy['mapped_payout_id'] = payout_id
                order_copy['estimated_payout_date'] = payout['settlement_date_formatted']
                mapped_orders.append(order_copy)
                
                # Create mapping record
                payout_order_mapping.append({
                    'payout_id': payout_id,
                    'payout_date': payout['settlement_date_formatted'],
                    'payout_gross': payout_gross,
                    'order_id': order['order_id'],
                    'order_number': order['order_number'],
                    'order_date': order['created_date_formatted'],
                    'order_total': order['total_price'],
                    'days_to_payout': (payout_date - datetime.fromisoformat(order['created_at'])).days,
                    'mapping_confidence': 'estimated'  # Could be enhanced with more sophisticated logic
                })
            
            mapped_count = len(selected_orders)
            total_amount = sum(o['total_price'] for o in selected_orders)
            print(f"   ✅ Payout {payout_id}: {mapped_count} orders, €{total_amount:.2f} total (target: €{payout_gross:.2f})")
        
        print(f"✅ Mapped {len(mapped_orders)} orders to payouts")
        return mapped_orders, payout_order_mapping
    
    def get_comprehensive_financial_data(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Get both payout and order-level data with mapping"""
        
        print(f"🔍 COMPREHENSIVE FINANCIAL DATA EXTRACTION")
        print("=" * 60)
        
        # Get payout data
        payouts = self.get_payout_data(start_date, end_date)
        
        # Get order data
        orders = self.get_orders_for_date_range(start_date, end_date)
        
        # Map orders to payouts
        mapped_orders, payout_order_mapping = self.map_orders_to_payouts(payouts, orders)
        
        return {
            'payouts': payouts,
            'orders': mapped_orders,
            'payout_order_mapping': payout_order_mapping,
            'summary': {
                'total_payouts': len(payouts),
                'total_orders': len(mapped_orders),
                'total_gross_from_payouts': sum(p['gross_sales'] for p in payouts),
                'total_from_orders': sum(o['total_price'] for o in mapped_orders),
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d') if end_date else start_date.strftime('%Y-%m-%d')}"
            }
        }
    
    def test_connection(self) -> bool:
        """Test both GraphQL and REST connections"""
        try:
            # Test GraphQL payout access
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
            
            graphql_result = self._execute_graphql_query(payout_query)
            graphql_ok = bool(graphql_result and graphql_result.get('data', {}).get('shopifyPaymentsAccount'))
            
            # Test REST orders access
            rest_result = self._make_rest_request('orders.json', {'limit': 1})
            rest_ok = bool(rest_result and rest_result.get('orders'))
            
            print(f"✅ GraphQL Payouts: {'Connected' if graphql_ok else 'Failed'}")
            print(f"✅ REST Orders: {'Connected' if rest_ok else 'Failed'}")
            
            return graphql_ok and rest_ok
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class OrdersAnalyticsExtractor:
    """Extract comprehensive order analytics data from Shopify API"""
    
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
    
    def _categorize_aov(self, amount: float) -> str:
        """Categorize order value into Low/Medium/High"""
        if amount < 30:
            return "Low"
        elif amount <= 80:
            return "Medium"
        else:
            return "High"
    
    def _get_customer_type(self, customer_id: str, order_date: datetime) -> str:
        """Determine if customer is new or returning"""
        if not customer_id:
            return "Guest"
        
        # Check for previous orders
        previous_orders = self._make_request('orders.json', {
            'customer_id': customer_id,
            'status': 'any',
            'created_at_max': order_date.isoformat(),
            'limit': 1
        })
        
        if previous_orders and previous_orders.get('orders'):
            return "Returning Customer"
        else:
            return "New Customer"
    
    def _extract_product_categories(self, line_items: List[Dict]) -> List[str]:
        """Extract product categories from line items"""
        categories = set()
        
        for item in line_items:
            # Get product details to extract categories/tags
            product_id = item.get('product_id')
            if product_id:
                product_data = self._make_request(f'products/{product_id}.json')
                if product_data and 'product' in product_data:
                    product = product_data['product']
                    
                    # Add product type as category
                    product_type = product.get('product_type')
                    if product_type:
                        categories.add(product_type)
                    
                    # Add tags as categories
                    tags = product.get('tags', '').split(', ')
                    for tag in tags:
                        if tag.strip():
                            categories.add(tag.strip())
        
        return list(categories)
    
    def _calculate_processing_days(self, created_at: str, fulfillments: List[Dict]) -> int:
        """Calculate days from order creation to fulfillment"""
        if not fulfillments:
            return 0
        
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            fulfilled_date = None
            
            for fulfillment in fulfillments:
                if fulfillment.get('status') == 'success':
                    fulfilled_at = fulfillment.get('created_at')
                    if fulfilled_at:
                        fulfilled_date = datetime.fromisoformat(fulfilled_at.replace('Z', '+00:00'))
                        break
            
            if fulfilled_date:
                return (fulfilled_date - created_date).days
            
        except Exception as e:
            print(f"⚠️  Error calculating processing days: {e}")
        
        return 0
    
    def extract_orders_for_date_range(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Extract all orders for a date range with complete analytics data"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        # Convert to timezone-aware dates (CET +02:00)
        local_tz = timezone(timedelta(hours=2))
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)
        
        print(f"📊 Extracting orders analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get orders for the date range
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250  # Maximum allowed
        })
        
        if not orders_data or not orders_data.get('orders'):
            print(f"ℹ️  No orders found for the specified date range")
            return []
        
        orders = orders_data['orders']
        print(f"✅ Found {len(orders)} orders to process")
        
        processed_orders = []
        
        for i, order in enumerate(orders, 1):
            try:
                print(f"   Processing order {i}/{len(orders)}: #{order.get('order_number')}")
                
                # Basic order information
                order_data = {
                    'order_id': str(order.get('id', '')),
                    'order_number': order.get('order_number', 0),
                    'date_created': order.get('created_at', ''),
                    'order_status': order.get('financial_status', 'unknown')
                }
                
                # Financial metrics
                total_price = float(order.get('total_price', 0))
                subtotal = float(order.get('subtotal_price', 0))
                tax_amount = float(order.get('total_tax', 0))
                discount_amount = float(order.get('total_discounts', 0))
                
                # Calculate shipping cost
                shipping_cost = 0
                shipping_lines = order.get('shipping_lines', [])
                for shipping in shipping_lines:
                    shipping_cost += float(shipping.get('price', 0))
                
                order_data.update({
                    'total_revenue': total_price,
                    'subtotal': subtotal,
                    'tax_amount': tax_amount,
                    'shipping_cost': shipping_cost,
                    'discount_amount': discount_amount,
                    'net_revenue': total_price - discount_amount
                })
                
                # Customer analysis - try multiple sources for customer data
                customer = order.get('customer', {})
                customer_id = customer.get('id') if customer else None
                order_date = datetime.fromisoformat(order.get('created_at', '').replace('Z', '+00:00'))
                
                # Try to get email from multiple sources
                customer_email = ''
                if customer and customer.get('email'):
                    customer_email = customer.get('email')
                elif order.get('contact_email'):
                    customer_email = order.get('contact_email')
                elif order.get('email'):
                    customer_email = order.get('email')
                
                # Try to get name from multiple sources
                customer_name = ''
                if customer and (customer.get('first_name') or customer.get('last_name')):
                    first_name = customer.get('first_name', '') or ''
                    last_name = customer.get('last_name', '') or ''
                    customer_name = f"{first_name} {last_name}".strip()
                else:
                    # Try shipping address for name
                    shipping_address = order.get('shipping_address', {})
                    if shipping_address:
                        if shipping_address.get('name'):
                            customer_name = shipping_address.get('name')
                        elif shipping_address.get('first_name') or shipping_address.get('last_name'):
                            first_name = shipping_address.get('first_name', '') or ''
                            last_name = shipping_address.get('last_name', '') or ''
                            customer_name = f"{first_name} {last_name}".strip()
                
                # If still no name, use a generic identifier
                if not customer_name:
                    customer_name = f"Guest Customer #{order.get('order_number', 'Unknown')}"
                
                order_data.update({
                    'customer_email': customer_email,
                    'customer_type': self._get_customer_type(customer_id, order_date) if customer_id else 'Guest',
                    'customer_name': customer_name
                })
                
                # Geographic information
                shipping_address = order.get('shipping_address', {})
                if shipping_address:
                    order_data.update({
                        'country': shipping_address.get('country') or 'Unknown',
                        'state_province': shipping_address.get('province') or 'Unknown',
                        'city': shipping_address.get('city') or 'Unknown'
                    })
                else:
                    order_data.update({
                        'country': 'Unknown',
                        'state_province': 'Unknown',
                        'city': 'Unknown'
                    })
                
                # Product and operational data
                line_items = order.get('line_items', [])
                product_categories = self._extract_product_categories(line_items)
                
                # Get fulfillments
                fulfillments = order.get('fulfillments', [])
                processing_days = self._calculate_processing_days(order.get('created_at', ''), fulfillments)
                
                order_data.update({
                    'product_categories': product_categories,
                    'items_count': len(line_items),
                    'payment_method': 'credit_card',  # Default, can be enhanced
                    'fulfillment_status': order.get('fulfillment_status', 'unfulfilled'),
                    'tags': order.get('tags', '').split(', ') if order.get('tags') else [],
                    'processing_days': processing_days
                })
                
                # Performance metrics
                order_data.update({
                    'aov_category': self._categorize_aov(total_price),
                    'has_refund': len(order.get('refunds', [])) > 0
                })
                
                # Traffic source (placeholder - would need additional tracking)
                order_data['traffic_source'] = 'web'  # Default value
                
                processed_orders.append(order_data)
                
            except Exception as e:
                print(f"❌ Error processing order #{order.get('order_number', 'unknown')}: {e}")
                continue
        
        print(f"✅ Successfully processed {len(processed_orders)} orders")
        return processed_orders
    
    def extract_single_date(self, date: datetime = None) -> List[Dict]:
        """Extract orders for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self.extract_orders_for_date_range(start_date, end_date)
    
    def test_connection(self) -> bool:
        """Test if connection to Shopify is working"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception as e:
            print(f"❌ Shopify connection test failed: {e}")
            return False
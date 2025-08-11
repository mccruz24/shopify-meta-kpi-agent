import os
import requests
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class ShopifyExtractor:
    """Extract KPI data from Shopify"""
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.base_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Make API request to Shopify with retry logic and rate limiting handling"""
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                response = requests.get(url, headers=self.headers, params=params or {}, timeout=60)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 5))
                    print(f"⚠️  Rate limited. Waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(retry_after + random.uniform(0.5, 2.0))
                    continue
                elif response.status_code in [500, 502, 503, 504]:  # Server errors - retry
                    wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"⚠️  Server error {response.status_code}. Retrying in {wait_time:.1f}s ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Shopify API error {response.status_code}: {response.text}")
                    return None
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                print(f"⚠️  Network error: {e}. Retrying in {wait_time:.1f}s ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Network error after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                print(f"❌ Shopify request failed: {e}")
                return None
        
        print(f"❌ All {max_retries} retry attempts failed")
        return None
    
    def get_daily_sales_data(self, date: datetime = None) -> Dict:
        """Get daily sales KPIs for P&L sheet"""
        if date is None:
            date = datetime.now() - timedelta(days=1)  # Yesterday
        
        # Date range for the specific day - using timezone-aware dates
        # Assuming Central European Time (+02:00) based on order timestamps
        from datetime import timezone
        
        # Convert to local timezone (CET +02:00)
        local_tz = timezone(timedelta(hours=2))
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
        end_date = start_date + timedelta(days=1)
        
        print(f"📊 Extracting Shopify sales data for {start_date.strftime('%Y-%m-%d')}")
        
        # Get orders for the day
        print(f"   🔍 Searching for orders between:")
        print(f"      From: {start_date.isoformat()}")
        print(f"      To:   {end_date.isoformat()}")
        
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        print(f"   📊 API Response: {orders_data is not None}")
        if orders_data:
            total_orders_in_response = len(orders_data.get('orders', []))
            print(f"   📦 Total orders in response: {total_orders_in_response}")
        
        if not orders_data:
            return {}
        
        orders = orders_data.get('orders', [])
        
        print(f"   🔍 Orders after filtering: {len(orders)}")
        
        # Debug: Show some order details if available
        if orders:
            for i, order in enumerate(orders[:3]):  # Show first 3 orders
                created_at = order.get('created_at', 'Unknown')
                order_id = order.get('id', 'Unknown')
                total = order.get('total_price', '0')
                print(f"      Order {i+1}: ID={order_id}, Created={created_at}, Total=${total}")
        
        if not orders:
            print(f"ℹ️  No orders found for {start_date.strftime('%Y-%m-%d')}")
            return {
                'shopify_gross_sales': 0,
                'shopify_shipping': 0,
                'shopify_discounts': 0,
                'shopify_refunds': 0,
                'shopify_fees': 0,
                'total_orders': 0,
                'aov': 0,
                'new_customers': 0,
                'returning_customers': 0,
            }
        
        # Calculate P&L metrics
        gross_sales = sum(float(order['subtotal_price']) for order in orders)
        
        # Calculate AOV (Average Order Value)
        aov = gross_sales / len(orders) if len(orders) > 0 else 0
        
        # Get unique customer IDs and check if they're new or returning
        customer_ids = []
        new_customers = 0
        returning_customers = 0
        
        for order in orders:
            customer_id = order.get('customer', {}).get('id') if order.get('customer') else None
            if customer_id:
                customer_ids.append(customer_id)
        
        # Check each customer to see if they're new or returning
        unique_customer_ids = list(set(customer_ids))
        for customer_id in unique_customer_ids:
            # Check if customer has previous orders before this date
            previous_orders = self._make_request('orders.json', {
                'customer_id': customer_id,
                'status': 'any',
                'created_at_max': start_date.isoformat(),
                'limit': 1
            })
            
            if previous_orders and previous_orders.get('orders'):
                returning_customers += 1
            else:
                new_customers += 1
        
        # Calculate shipping
        shipping = 0
        for order in orders:
            shipping_lines = order.get('shipping_lines', [])
            for shipping_line in shipping_lines:
                shipping += float(shipping_line.get('price', 0))
        
        # Calculate discounts
        discounts = sum(float(order.get('total_discounts', 0)) for order in orders)
        
        # Calculate refunds (if any refunds exist)
        refunds = 0
        for order in orders:
            order_refunds = order.get('refunds', [])
            for refund in order_refunds:
                refund_line_items = refund.get('refund_line_items', [])
                for item in refund_line_items:
                    refunds += float(item.get('subtotal', 0))
        
        # Estimate Shopify fees (typically 2.9% + 30¢ per transaction)
        shopify_fees = 0
        for order in orders:
            order_total = float(order['total_price'])
            # Basic fee calculation - adjust based on your Shopify plan
            shopify_fees += (order_total * 0.029) + 0.30
        
        print(f"✅ Found {len(orders)} orders")
        print(f"   Gross Sales: ${gross_sales:.2f}")
        print(f"   AOV: ${aov:.2f}")
        print(f"   New Customers: {new_customers}")
        print(f"   Returning Customers: {returning_customers}")
        print(f"   Shipping: ${shipping:.2f}")
        print(f"   Discounts: ${discounts:.2f}")
        print(f"   Refunds: ${refunds:.2f}")
        print(f"   Est. Fees: ${shopify_fees:.2f}")
        
        return {
            'shopify_gross_sales': round(gross_sales, 2),
            'shopify_shipping': round(shipping, 2),
            'shopify_discounts': round(-abs(discounts), 2) if discounts > 0 else 0,  # Negative value
            'shopify_refunds': round(-abs(refunds), 2) if refunds > 0 else 0,  # Negative value
            'shopify_fees': round(shopify_fees, 2),
            'total_orders': len(orders),
            'aov': round(aov, 2),
            'new_customers': new_customers,
            'returning_customers': returning_customers,
        }
    
    def test_connection(self) -> bool:
        """Test if connection to Shopify is working"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception as e:
            print(f"❌ Shopify connection test failed: {e}")
            return False
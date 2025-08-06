import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class PrintifyExtractor:
    """Extract cost data from Printify API"""
    
    def __init__(self):
        self.api_token = os.getenv('PRINTIFY_API_TOKEN')
        self.shop_id = os.getenv('PRINTIFY_SHOP_ID')  # Optional - we'll find it automatically
        self.base_url = "https://api.printify.com/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'KPI-Agent/1.0'
        }
        self._shops = None  # Cache shops
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Printify"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print(f"❌ Printify API authentication failed. Check your API token.")
                return None
            elif response.status_code == 403:
                print(f"❌ Printify API access forbidden. Check permissions.")
                return None
            else:
                print(f"❌ Printify API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Printify request failed: {e}")
            return None
    
    def get_shops(self) -> List[Dict]:
        """Get available shops - GET /v1/shops.json"""
        if not self.api_token:
            print("❌ No Printify API token configured")
            return []
        
        shops_data = self._make_request('shops.json')
        
        if shops_data:
            # Printify returns shops as a direct array
            if isinstance(shops_data, list):
                return shops_data
            elif isinstance(shops_data, dict) and 'data' in shops_data:
                return shops_data.get('data', [])
            else:
                # Single shop object
                return [shops_data] if shops_data else []
        
        return []
    
    def get_primary_shop_id(self):
        """Get the primary shop ID automatically"""
        if self.shop_id:
            return self.shop_id
        
        if self._shops is None:
            self._shops = self.get_shops()
        
        if self._shops:
            # Use the first shop by default
            primary_shop = self._shops[0]
            shop_id = primary_shop.get('id')
            shop_title = primary_shop.get('title', 'Unknown Shop')
            print(f"🏪 Using shop: {shop_title} (ID: {shop_id})")
            return shop_id
        
        print("❌ No Printify shops found")
        return None
    
    def get_daily_costs(self, date: datetime = None) -> Dict:
        """Get daily Printify costs (COGS) - UPDATED VERSION"""
        if date is None:
            date = datetime.now() - timedelta(days=1)  # Yesterday
        
        # Get shop ID automatically
        shop_id = self.get_primary_shop_id()
        if not shop_id:
            print("❌ No Printify shop ID available")
            return {'printify_charge': 0}
        
        # Date range for the specific day
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        
        print(f"🖨️  Extracting Printify costs for {start_date.strftime('%Y-%m-%d')}")
        
        # Step 1: Get orders with proper pagination handling
        params = {
            'created_at_min': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_max': end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'limit': 100  # Max per page
        }
        
        orders_response = self._make_request(f'shops/{shop_id}/orders.json', params)
        
        if not orders_response:
            print(f"ℹ️  No Printify API response for {start_date.strftime('%Y-%m-%d')}")
            return {'printify_charge': 0}
        
        # Handle paginated response structure
        if isinstance(orders_response, dict) and 'data' in orders_response:
            all_orders = orders_response['data']
            print(f"📄 Retrieved page 1 with {len(all_orders)} orders")
            
            # Handle pagination if there are more pages
            current_page = orders_response.get('current_page', 1)
            last_page = orders_response.get('last_page', 1)
            
            if last_page > 1:
                print(f"📚 Found {last_page} pages total, fetching remaining pages...")
                for page in range(2, min(last_page + 1, 6)):  # Limit to 5 pages max for safety
                    page_params = {**params, 'page': page}
                    page_response = self._make_request(f'shops/{shop_id}/orders.json', page_params)
                    
                    if page_response and 'data' in page_response:
                        all_orders.extend(page_response['data'])
                        print(f"📄 Retrieved page {page} with {len(page_response['data'])} orders")
                    
                    time.sleep(0.2)  # Small delay between pages
        elif isinstance(orders_response, list):
            # Direct array (shouldn't happen based on API docs, but just in case)
            all_orders = orders_response
        else:
            print(f"❌ Unexpected API response format: {type(orders_response)}")
            return {'printify_charge': 0}
        
        if not all_orders:
            print(f"ℹ️  No Printify orders found for {start_date.strftime('%Y-%m-%d')}")
            return {'printify_charge': 0}
        
        # Step 2: Filter orders to only include those from the specific date
        daily_orders = []
        for order in all_orders:
            # Check if order was created on the specific date
            order_date_str = order.get('created_at', '')
            if order_date_str:
                try:
                    # Parse the order date (format: "2025-06-24 20:40:06+00:00")
                    order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                    order_date = order_date.replace(tzinfo=None)  # Remove timezone for comparison
                    
                    # Check if order is from the target date
                    if order_date.date() == start_date.date():
                        daily_orders.append(order)
                except ValueError as e:
                    print(f"⚠️  Could not parse date '{order_date_str}': {e}")
                    # If date parsing fails, include the order (better safe than sorry)
                    daily_orders.append(order)
        
        if not daily_orders:
            print(f"ℹ️  No Printify orders found for {start_date.strftime('%Y-%m-%d')} after date filtering")
            return {'printify_charge': 0}
        
        # Step 3: Calculate costs from daily orders
        total_cost = 0
        order_count = 0
        cost_breakdown = {
            'product_cost': 0,
            'shipping_cost': 0
        }
        
        print(f"📅 Processing {len(daily_orders)} orders from {start_date.strftime('%Y-%m-%d')}")
        
        for order in daily_orders:
            order_id = order.get('id', 'Unknown')
            order_cost = self._calculate_order_cost_from_response(order)
            
            # Track cost breakdown
            line_items = order.get('line_items', [])
            for item in line_items:
                cost_breakdown['product_cost'] += float(item.get('cost', 0)) / 100
                cost_breakdown['shipping_cost'] += float(item.get('shipping_cost', 0)) / 100
            
            total_cost += order_cost
            order_count += 1
            
            print(f"   📦 Order {order_id}: ${order_cost:.2f}")
        
        print(f"✅ Found {order_count} Printify orders for {start_date.strftime('%Y-%m-%d')}")
        print(f"   Product costs: ${cost_breakdown['product_cost']:.2f}")
        print(f"   Shipping costs: ${cost_breakdown['shipping_cost']:.2f}")
        print(f"   Total COGS: ${total_cost:.2f}")
        
        return {
            'printify_charge': round(total_cost, 2)
        }
    
    def _calculate_order_cost_from_response(self, order: Dict) -> float:
        """Calculate order cost from the API response data"""
        total_cost = 0
        
        # Extract cost from line items (data is already detailed in the response)
        line_items = order.get('line_items', [])
        
        for item in line_items:
            # NOTE: cost and shipping_cost fields already represent totals for the quantity
            # No need to multiply by quantity as these are already line item totals
            
            # Product cost total (in cents) - already includes quantity
            product_cost_total = float(item.get('cost', 0)) / 100
            
            # Shipping cost total (in cents) - already includes quantity
            shipping_cost_total = float(item.get('shipping_cost', 0)) / 100
            
            # Calculate total item cost (no quantity multiplication needed)
            item_total = product_cost_total + shipping_cost_total
            total_cost += item_total
        
        return total_cost
    
    def get_order_details(self, shop_id: str, order_id: str) -> Optional[Dict]:
        """Get detailed order information with full properties - GET /v1/shops/{shop_id}/orders/{order_id}.json"""
        try:
            detailed_order = self._make_request(f'shops/{shop_id}/orders/{order_id}.json')
            
            if detailed_order:
                print(f"   📋 Retrieved detailed properties for order {order_id}")
                return detailed_order
            else:
                print(f"   ⚠️  Could not retrieve detailed properties for order {order_id}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error getting order details for {order_id}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if connection to Printify is working"""
        try:
            if not self.api_token:
                print("❌ No Printify API token configured in .env file")
                print("   Add: PRINTIFY_API_TOKEN=your_token_here")
                return False
            
            print(f"🔍 Testing Printify API connection...")
            print(f"   Token: {self.api_token[:20]}..." if len(self.api_token) > 20 else f"   Token: {self.api_token}")
            
            # Test by getting shops
            shops = self.get_shops()
            
            if shops:
                print(f"✅ Printify connection successful! Found {len(shops)} shop(s):")
                for shop in shops:
                    shop_id = shop.get('id', 'N/A')
                    shop_title = shop.get('title', 'N/A')
                    shop_sales_channel = shop.get('sales_channel', 'N/A')
                    print(f"   📋 {shop_title} (ID: {shop_id}) - {shop_sales_channel}")
                
                # Test getting recent orders for the first shop
                if shops:
                    test_shop_id = shops[0].get('id')
                    print(f"\n🧪 Testing order retrieval for shop {test_shop_id}...")
                    
                    # Get recent orders (last 7 days)
                    recent_date = datetime.now() - timedelta(days=7)
                    test_params = {
                        'created_at_min': recent_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'limit': 5
                    }
                    
                    recent_orders = self._make_request(f'shops/{test_shop_id}/orders.json', test_params)
                    
                    if recent_orders:
                        if isinstance(recent_orders, dict) and 'data' in recent_orders:
                            order_count = len(recent_orders['data'])
                        else:
                            order_count = len(recent_orders) if isinstance(recent_orders, list) else 0
                        
                        print(f"✅ Found {order_count} recent orders in the last 7 days")
                    else:
                        print("ℹ️  No recent orders found (normal for new shops)")
                
                return True
            else:
                print("❌ No shops found in Printify account")
                print("   Make sure your API token has the correct permissions")
                return False
                
        except Exception as e:
            print(f"❌ Printify connection test failed: {e}")
            return False
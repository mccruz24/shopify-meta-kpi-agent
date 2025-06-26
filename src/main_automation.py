import os
import requests
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
    
    def get_daily_sales_data(self, date: datetime = None) -> Dict:
        """Get daily sales KPIs for P&L sheet"""
        if date is None:
            date = datetime.now() - timedelta(days=1)  # Yesterday
        
        # Date range for the specific day
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        print(f"📊 Extracting Shopify sales data for {start_date.strftime('%Y-%m-%d')}")
        
        # Get orders for the day
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'financial_status': 'paid',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if not orders_data:
            return {}
        
        orders = orders_data.get('orders', [])
        
        if not orders:
            print(f"ℹ️  No orders found for {start_date.strftime('%Y-%m-%d')}")
            return {
                'shopify_gross_sales': 0,
                'shopify_shipping': 0,
                'shopify_discounts': 0,
                'shopify_refunds': 0,
                'shopify_fees': 0,
            }
        
        # Calculate P&L metrics
        gross_sales = sum(float(order['subtotal_price']) for order in orders)
        
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
        }
    
    def test_connection(self) -> bool:
        """Test if connection to Shopify is working"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception as e:
            print(f"❌ Shopify connection test failed: {e}")
            return False
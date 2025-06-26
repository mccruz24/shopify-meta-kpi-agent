import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class OrdersNotionLoader:
    """Load orders analytics data into Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.orders_db_id = "21e8db45e2f980b99159f9da13f924a8"  # Orders Analytics database
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def _make_notion_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make request to Notion API"""
        try:
            url = f"https://api.notion.com/v1/{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=data or {})
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data or {})
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"❌ Notion API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Notion request failed: {e}")
            return None
    
    def check_order_exists(self, order_id: str) -> bool:
        """Check if order already exists in Notion database"""
        try:
            query_data = {
                "filter": {
                    "property": "Order ID",
                    "title": {
                        "equals": order_id
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.orders_db_id}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception as e:
            print(f"⚠️  Could not check if order exists: {e}")
            return False
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for Notion"""
        try:
            if not date_str:
                return datetime.now().isoformat()
            
            # Handle Shopify date format
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            elif '+' in date_str and date_str.count(':') == 3:
                # Already has timezone
                pass
            
            dt = datetime.fromisoformat(date_str)
            return dt.date().isoformat()
        except Exception as e:
            print(f"⚠️  Date formatting error: {e}")
            return datetime.now().date().isoformat()
    
    def _create_notion_properties(self, order_data: Dict) -> Dict:
        """Create Notion properties from order data"""
        # Helper function to safely create select fields
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        # Calculate Net Revenue
        total_revenue = float(order_data.get('total_revenue', 0))
        discount_amount = float(order_data.get('discount_amount', 0))
        net_revenue = total_revenue - discount_amount
        
        properties = {
            "Order ID": {
                "title": [{"text": {"content": str(order_data.get('order_id', ''))}}]
            },
            "Order Number": {
                "number": order_data.get('order_number', 0)
            },
            "Date Created": {
                "date": {"start": self._format_date(order_data.get('date_created', ''))}
            },
            "Order Status": safe_select(order_data.get('order_status'), 'unknown'),
            "Total Revenue": {
                "number": round(total_revenue, 2)
            },
            "Subtotal": {
                "number": round(float(order_data.get('subtotal', 0)), 2)
            },
            "Tax Amount": {
                "number": round(float(order_data.get('tax_amount', 0)), 2)
            },
            "Shipping Cost": {
                "number": round(float(order_data.get('shipping_cost', 0)), 2)
            },
            "Discount Amount": {
                "number": round(discount_amount, 2)
            },
            "Net Revenue": {
                "number": round(net_revenue, 2)
            },
            "Customer Email": {
                "email": str(order_data.get('customer_email', '')) or None
            },
            "Customer Type": safe_select(order_data.get('customer_type'), 'Guest'),
            "Customer Name": {
                "rich_text": [{"text": {"content": str(order_data.get('customer_name', ''))}}]
            },
            "Country": safe_select(order_data.get('country'), 'Unknown'),
            "State/Province": {
                "rich_text": [{"text": {"content": str(order_data.get('state_province', ''))}}]
            },
            "City": {
                "rich_text": [{"text": {"content": str(order_data.get('city', ''))}}]
            },
            "Traffic Source": safe_select(order_data.get('traffic_source'), 'web'),
            "Items Count": {
                "number": int(order_data.get('items_count', 0))
            },
            "Payment Method": safe_select(order_data.get('payment_method'), 'credit_card'),
            "AOV Category": safe_select(order_data.get('aov_category'), 'Medium'),
            "Processing Days": {
                "number": int(order_data.get('processing_days', 0))
            },
            "Has Refund": {
                "checkbox": bool(order_data.get('has_refund', False))
            }
        }
        
        # Remove Customer Email if it's empty
        if not properties["Customer Email"]["email"]:
            del properties["Customer Email"]
        
        # Handle multi-select fields
        if order_data.get('product_categories'):
            properties["Product Categories"] = {
                "multi_select": [{"name": str(cat)} for cat in order_data['product_categories'][:10] if cat]  # Limit to 10
            }
        
        if order_data.get('tags'):
            properties["Tags"] = {
                "multi_select": [{"name": str(tag)} for tag in order_data['tags'][:10] if tag and str(tag).strip()]  # Limit to 10
            }
        
        return properties
    
    def load_order(self, order_data: Dict, skip_if_exists: bool = True) -> bool:
        """Load single order into Notion"""
        try:
            order_id = order_data.get('order_id', '')
            if not order_id:
                print("❌ No order ID provided")
                return False
            
            # Check if already exists
            if skip_if_exists and self.check_order_exists(order_id):
                print(f"⏭️  Order {order_id} already exists - skipping")
                return True
            
            # Create Notion page
            page_data = {
                "parent": {"database_id": self.orders_db_id},
                "properties": self._create_notion_properties(order_data)
            }
            
            result = self._make_notion_request('POST', 'pages', page_data)
            
            if result:
                order_number = order_data.get('order_number', 'Unknown')
                total = order_data.get('total_revenue', 0)
                print(f"✅ Added order #{order_number} (${total:.2f}) to Notion")
                return True
            else:
                print(f"❌ Failed to add order {order_id} to Notion")
                return False
                
        except Exception as e:
            print(f"❌ Error loading order {order_data.get('order_id', 'unknown')}: {e}")
            return False
    
    def load_orders_batch(self, orders_data: List[Dict], skip_if_exists: bool = True) -> Dict:
        """Load multiple orders into Notion"""
        print(f"📊 Loading {len(orders_data)} orders into Notion...")
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, order_data in enumerate(orders_data, 1):
            print(f"   Processing order {i}/{len(orders_data)}")
            
            try:
                # Check if exists first
                order_id = order_data.get('order_id', '')
                if skip_if_exists and self.check_order_exists(order_id):
                    skipped += 1
                    print(f"   ⏭️  Order {order_id} already exists - skipping")
                    continue
                
                success = self.load_order(order_data, skip_if_exists=False)  # Already checked above
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Small delay to avoid rate limits
                if i % 10 == 0:  # Every 10 requests
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                failed += 1
                print(f"❌ Error processing order: {e}")
        
        results = {
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'total': len(orders_data)
        }
        
        print(f"\n🎉 Orders loading completed!")
        print(f"   ✅ Successfully loaded: {successful}")
        print(f"   ⏭️  Skipped (existing): {skipped}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total processed: {successful + skipped + failed}/{len(orders_data)}")
        
        return results
    
    def test_connection(self) -> bool:
        """Test connection to Notion database"""
        try:
            result = self._make_notion_request('GET', f'databases/{self.orders_db_id}')
            return bool(result and result.get('id'))
        except Exception as e:
            print(f"❌ Notion connection test failed: {e}")
            return False
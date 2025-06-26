import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class PrintifyNotionLoader:
    """Load Printify analytics data into Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.printify_db_id = None  # Will be set when user provides it
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def set_database_id(self, database_id: str):
        """Set the Printify Analytics database ID"""
        self.printify_db_id = database_id
    
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
        if not self.printify_db_id:
            print("❌ No database ID set")
            return False
        
        try:
            query_data = {
                "filter": {
                    "property": "Order ID",
                    "title": {
                        "equals": order_id
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.printify_db_id}/query', query_data)
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
            
            # Handle Printify date format
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            elif '+' in date_str and date_str.count(':') == 3:
                pass  # Already has timezone
            
            dt = datetime.fromisoformat(date_str)
            return dt.date().isoformat()
        except Exception as e:
            print(f"⚠️  Date formatting error: {e}")
            return datetime.now().date().isoformat()
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Format datetime string for Notion"""
        try:
            if not datetime_str:
                return datetime.now().isoformat()
            
            # Handle Printify datetime format
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str.replace('Z', '+00:00')
            
            dt = datetime.fromisoformat(datetime_str)
            return dt.isoformat()
        except Exception as e:
            print(f"⚠️  Datetime formatting error: {e}")
            return datetime.now().isoformat()
    
    def _create_notion_properties(self, analytics_data: Dict) -> Dict:
        """Create Notion properties from Printify analytics data"""
        
        # Helper function to safely create select fields
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        # Helper function to safely create multi-select fields
        def safe_multi_select(values_list):
            if not values_list:
                return {"multi_select": []}
            return {"multi_select": [{"name": str(val)[:100]} for val in values_list[:10] if val]}  # Limit length and count
        
        properties = {
            # Order Information (8 fields)
            "Order ID": {
                "title": [{"text": {"content": str(analytics_data.get('order_id', ''))}}]
            },
            "Date": {
                "date": {"start": self._format_date(analytics_data.get('date', ''))}
            },
            "Shopify Order ID": {
                "rich_text": [{"text": {"content": str(analytics_data.get('shopify_order_id', ''))}}]
            },
            "Status": safe_select(analytics_data.get('status'), 'unknown'),
            "Fulfillment Type": safe_select(analytics_data.get('fulfillment_type'), 'ordinary'),
            "Print Provider": {
                "rich_text": [{"text": {"content": str(analytics_data.get('print_provider', ''))}}]
            },
            "Shop Name": {
                "rich_text": [{"text": {"content": str(analytics_data.get('shop_name', ''))}}]
            },
            "Order Type": safe_select(analytics_data.get('order_type'), 'regular'),
            
            # Financial Data (12 fields)
            "Total Revenue": {
                "number": round(float(analytics_data.get('total_revenue', 0)), 2)
            },
            "Product COGS": {
                "number": round(float(analytics_data.get('product_cogs', 0)), 2)
            },
            "Shipping COGS": {
                "number": round(float(analytics_data.get('shipping_cogs', 0)), 2)
            },
            "Total COGS": {
                "number": round(float(analytics_data.get('total_cogs', 0)), 2)
            },
            "Tax Amount": {
                "number": round(float(analytics_data.get('tax_amount', 0)), 2)
            },
            "Gross Profit": {
                "number": round(float(analytics_data.get('gross_profit', 0)), 2)
            },
            "Net Profit": {
                "number": round(float(analytics_data.get('net_profit', 0)), 2)
            },
            "Gross Margin": {
                "number": round(float(analytics_data.get('gross_margin', 0)), 1)
            },
            "Net Margin": {
                "number": round(float(analytics_data.get('net_margin', 0)), 1)
            },
            "Shipping Revenue": {
                "number": round(float(analytics_data.get('shipping_revenue', 0)), 2)
            },
            "Items Count": {
                "number": int(analytics_data.get('items_count', 0))
            },
            "Average Item Cost": {
                "number": round(float(analytics_data.get('average_item_cost', 0)), 2)
            },
            
            # Timeline & Operations (6 fields)
            "Created At": {
                "date": {"start": self._format_datetime(analytics_data.get('created_at', ''))}
            },
            "Sent to Production": {
                "date": {"start": self._format_datetime(analytics_data.get('sent_to_production', ''))} if analytics_data.get('sent_to_production') else None
            },
            "Lead Time Hours": {
                "number": round(float(analytics_data.get('lead_time_hours', 0)), 1) if analytics_data.get('lead_time_hours') is not None else None
            },
            "Processing Status": safe_select(analytics_data.get('processing_status'), 'pending'),
            "Shipping Method": safe_select(analytics_data.get('shipping_method'), 'standard'),
            # Days Since Order will be calculated as a formula in Notion
            
            # Product & Provider Data (6 fields)
            "Product Titles": safe_multi_select(analytics_data.get('product_titles', [])),
            "Blueprint IDs": {
                "rich_text": [{"text": {"content": str(analytics_data.get('blueprint_ids', ''))}}]
            },
            "Variant Count": {
                "number": int(analytics_data.get('variant_count', 0))
            },
            "Primary Category": safe_select(analytics_data.get('primary_category'), 'other'),
            "Provider Name": {
                "rich_text": [{"text": {"content": str(analytics_data.get('provider_name', ''))}}]
            },
            "Provider Performance": safe_select(analytics_data.get('provider_performance'), 'unknown'),
            
            # Customer & Geographic (3 fields)
            "Customer Country": safe_select(analytics_data.get('customer_country'), 'Unknown'),
            "Customer State": safe_select(analytics_data.get('customer_state'), 'Unknown'),
            "Shipping Zone": safe_select(analytics_data.get('shipping_zone'), 'unknown')
        }
        
        # Remove None values for optional fields
        properties = {k: v for k, v in properties.items() if v is not None}
        
        return properties
    
    def load_order(self, analytics_data: Dict, skip_if_exists: bool = True) -> bool:
        """Load single order analytics into Notion"""
        if not self.printify_db_id:
            print("❌ No database ID set for Printify Analytics")
            return False
        
        try:
            order_id = analytics_data.get('order_id', '')
            if not order_id:
                print("❌ No order ID provided")
                return False
            
            # Check if already exists
            if skip_if_exists and self.check_order_exists(order_id):
                print(f"⏭️  Order {order_id} already exists - skipping")
                return True
            
            # Create Notion page
            page_data = {
                "parent": {"database_id": self.printify_db_id},
                "properties": self._create_notion_properties(analytics_data)
            }
            
            result = self._make_notion_request('POST', 'pages', page_data)
            
            if result:
                status = analytics_data.get('status', 'unknown')
                revenue = analytics_data.get('total_revenue', 0)
                profit = analytics_data.get('net_profit', 0)
                margin = analytics_data.get('net_margin', 0)
                print(f"✅ Added {status} order ${revenue:.2f} (${profit:.2f}, {margin:.1f}%) to Notion")
                return True
            else:
                print(f"❌ Failed to add order {order_id} to Notion")
                return False
                
        except Exception as e:
            print(f"❌ Error loading order {analytics_data.get('order_id', 'unknown')}: {e}")
            return False
    
    def load_orders_batch(self, analytics_data_list: List[Dict], skip_if_exists: bool = True) -> Dict:
        """Load multiple orders into Notion"""
        if not self.printify_db_id:
            print("❌ No database ID set for Printify Analytics")
            return {'successful': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        
        print(f"🖨️  Loading {len(analytics_data_list)} Printify analytics records into Notion...")
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, analytics_data in enumerate(analytics_data_list, 1):
            print(f"   Processing order {i}/{len(analytics_data_list)}")
            
            try:
                # Check if exists first
                order_id = analytics_data.get('order_id', '')
                if skip_if_exists and self.check_order_exists(order_id):
                    skipped += 1
                    print(f"   ⏭️  Order {order_id} already exists - skipping")
                    continue
                
                success = self.load_order(analytics_data, skip_if_exists=False)  # Already checked above
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Rate limiting
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
            'total': len(analytics_data_list)
        }
        
        print(f"\\n🎉 Printify analytics loading completed!")
        print(f"   ✅ Successfully loaded: {successful}")
        print(f"   ⏭️  Skipped (existing): {skipped}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total processed: {successful + skipped + failed}/{len(analytics_data_list)}")
        
        return results
    
    def test_connection(self) -> bool:
        """Test connection to Notion database"""
        if not self.printify_db_id:
            print("❌ No database ID set for Printify Analytics")
            return False
        
        try:
            result = self._make_notion_request('GET', f'databases/{self.printify_db_id}')
            return bool(result and result.get('id'))
        except Exception as e:
            print(f"❌ Notion connection test failed: {e}")
            return False
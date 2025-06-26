import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class TrafficNotionLoader:
    """Load traffic analytics data into Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.traffic_db_id = "21e8db45e2f9800a99fcde81a5efd6c5"  # Traffic Analytics database
        
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
    
    def check_session_exists(self, session_id: str) -> bool:
        """Check if session already exists in Notion database"""
        try:
            query_data = {
                "filter": {
                    "property": "Session ID",
                    "title": {
                        "equals": session_id
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.traffic_db_id}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception as e:
            print(f"⚠️  Could not check if session exists: {e}")
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
    
    def _create_notion_properties(self, session_data: Dict) -> Dict:
        """Create Notion properties from session data"""
        # Helper function to safely create select fields
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        properties = {
            "Session ID": {
                "title": [{"text": {"content": str(session_data.get('session_id', ''))}}]
            },
            "Date": {
                "date": {"start": self._format_date(session_data.get('date', ''))}
            },
            "Visitor Type": safe_select(session_data.get('visitor_type'), 'new_visitor'),
            "Traffic Source": safe_select(session_data.get('traffic_source'), 'direct'),
            "Medium": safe_select(session_data.get('medium'), 'direct'),
            "Campaign Name": {
                "rich_text": [{"text": {"content": str(session_data.get('utm_campaign', ''))}}]
            },
            "Order Number": {
                "rich_text": [{"text": {"content": str(session_data.get('order_number', ''))}}]
            },
            "Source Details": {
                "rich_text": [{"text": {"content": str(session_data.get('referral_website', '') or session_data.get('source_details', ''))}}]
            },
            "UTM Parameters": {
                "rich_text": [{"text": {"content": str(session_data.get('utm_parameters', ''))}}]
            },
            "Device Type": safe_select(session_data.get('device_type'), 'desktop'),
            "Operating System": safe_select(session_data.get('operating_system'), 'Unknown'),
            "Browser": safe_select(session_data.get('browser'), 'Unknown'),
            "Screen Resolution": {
                "rich_text": [{"text": {"content": str(session_data.get('screen_resolution', ''))}}]
            },
            "Country": safe_select(session_data.get('country'), 'Unknown'),
            "State/Province": {
                "rich_text": [{"text": {"content": str(session_data.get('state_province', ''))}}]
            },
            "City": {
                "rich_text": [{"text": {"content": str(session_data.get('city', ''))}}]
            },
            "Timezone": safe_select(session_data.get('timezone'), 'UTC'),
            "Page Views": {
                "number": int(session_data.get('pages_viewed', 1))
            },
            "Session Duration": {
                "number": int(session_data.get('session_duration', 0))
            },
            "Bounce Rate": {
                "checkbox": bool(session_data.get('bounce_rate', False))
            },
            "Entry Page": {
                "rich_text": [{"text": {"content": str(session_data.get('entry_page', '/'))}}]
            },
            "Exit Page URL": {
                "rich_text": [{"text": {"content": str(session_data.get('exit_page', '/'))}}]
            },
            "Converted": {
                "checkbox": bool(session_data.get('converted', False))
            },
            "Order Value": {
                "number": round(float(session_data.get('order_value', 0)), 2)
            },
            "Cart Added": {
                "checkbox": bool(session_data.get('cart_added', False))
            },
            "Checkout Started": {
                "checkbox": bool(session_data.get('checkout_started', False))
            },
            "Page Load Time": {
                "number": round(float(session_data.get('page_load_time', 0)), 1)
            },
            "Purchase Time": {
                "number": int(session_data.get('time_to_purchase', 0))
            },
            "Touch Points": {
                "number": int(session_data.get('touch_points', 1))
            }
        }
        
        # Note: Order Reference field to be added manually as relation field in Notion
        # order_number = session_data.get('order_number', '')
        # Will be used when you create the relation field
        
        # Handle products viewed as multi-select
        products_viewed = session_data.get('products_viewed', [])
        if products_viewed:
            properties["Product Categories"] = {
                "multi_select": [{"name": str(product)[:100]} for product in products_viewed[:10] if product]  # Limit length and count
            }
        
        return properties
    
    def load_session(self, session_data: Dict, skip_if_exists: bool = True) -> bool:
        """Load single session into Notion"""
        try:
            session_id = session_data.get('session_id', '')
            if not session_id:
                print("❌ No session ID provided")
                return False
            
            # Check if already exists
            if skip_if_exists and self.check_session_exists(session_id):
                print(f"⏭️  Session {session_id} already exists - skipping")
                return True
            
            # Create Notion page
            page_data = {
                "parent": {"database_id": self.traffic_db_id},
                "properties": self._create_notion_properties(session_data)
            }
            
            result = self._make_notion_request('POST', 'pages', page_data)
            
            if result:
                traffic_source = session_data.get('traffic_source', 'unknown')
                device = session_data.get('device_type', 'unknown')
                converted = "✅" if session_data.get('converted') else "❌"
                order_value = session_data.get('order_value', 0)
                print(f"✅ Added {traffic_source}/{device} session {converted} (${order_value:.2f}) to Notion")
                return True
            else:
                print(f"❌ Failed to add session {session_id} to Notion")
                return False
                
        except Exception as e:
            print(f"❌ Error loading session {session_data.get('session_id', 'unknown')}: {e}")
            return False
    
    def load_sessions_batch(self, sessions_data: List[Dict], skip_if_exists: bool = True) -> Dict:
        """Load multiple sessions into Notion"""
        print(f"🚗 Loading {len(sessions_data)} traffic sessions into Notion...")
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, session_data in enumerate(sessions_data, 1):
            print(f"   Processing session {i}/{len(sessions_data)}")
            
            try:
                # Check if exists first
                session_id = session_data.get('session_id', '')
                if skip_if_exists and self.check_session_exists(session_id):
                    skipped += 1
                    print(f"   ⏭️  Session {session_id} already exists - skipping")
                    continue
                
                success = self.load_session(session_data, skip_if_exists=False)  # Already checked above
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
                print(f"❌ Error processing session: {e}")
        
        results = {
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'total': len(sessions_data)
        }
        
        print(f"\n🎉 Traffic sessions loading completed!")
        print(f"   ✅ Successfully loaded: {successful}")
        print(f"   ⏭️  Skipped (existing): {skipped}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total processed: {successful + skipped + failed}/{len(sessions_data)}")
        
        return results
    
    def test_connection(self) -> bool:
        """Test connection to Notion database"""
        try:
            result = self._make_notion_request('GET', f'databases/{self.traffic_db_id}')
            return bool(result and result.get('id'))
        except Exception as e:
            print(f"❌ Notion connection test failed: {e}")
            return False
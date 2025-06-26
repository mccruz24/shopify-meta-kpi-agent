import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class FinancialNotionLoader:
    """Load financial analytics data into Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.financial_db_id = "21e8db45e2f98061a311f3a875b96e16"  # Financial Analytics database
        self.orders_db_id = "21e8db45e2f980b99159f9da13f924a8"  # Orders Analytics database (for relations)
        
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
    
    def find_order_page_id(self, order_id: str) -> Optional[str]:
        """Find the Notion page ID for the related order"""
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
                pages = result['results']
                if pages:
                    return pages[0]['id']
            
            return None
        except Exception as e:
            print(f"⚠️  Could not find order page ID: {e}")
            return None

    def check_transaction_exists(self, transaction_id: str) -> bool:
        """Check if transaction already exists in Notion database"""
        try:
            query_data = {
                "filter": {
                    "property": "Transaction ID",
                    "title": {
                        "equals": transaction_id
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.financial_db_id}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception as e:
            print(f"⚠️  Could not check if transaction exists: {e}")
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
    
    def _create_notion_properties(self, transaction_data: Dict) -> Dict:
        """Create Notion properties from transaction data"""
        # Helper function to safely create select fields
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        # Find related order page ID
        order_id = transaction_data.get('order_reference', '')
        order_page_id = self.find_order_page_id(order_id) if order_id else None
        
        properties = {
            "Transaction ID": {
                "title": [{"text": {"content": str(transaction_data.get('transaction_id', ''))}}]
            },
            "Order Reference": {
                "relation": [{"id": order_page_id}] if order_page_id else []
            },
            "Date": {
                "date": {"start": self._format_date(transaction_data.get('date', ''))}
            },
            "Transaction Type": safe_select(transaction_data.get('transaction_type'), 'sale'),
            "Gross Amount": {
                "number": round(float(transaction_data.get('gross_amount', 0)), 2)
            },
            "Processing Fee": {
                "number": round(float(transaction_data.get('processing_fee', 0)), 2)
            },
            "Currency": safe_select(transaction_data.get('currency'), 'USD'),
            "Exchange Rate": {
                "number": round(float(transaction_data.get('exchange_rate', 1.0)), 4)
            },
            "Payment Method": safe_select(transaction_data.get('payment_method'), 'credit_card'),
            "Payment Gateway": safe_select(transaction_data.get('payment_gateway'), 'shopify_payments'),
            "Card Type": safe_select(transaction_data.get('card_type'), 'unknown'),
            "Last 4 Digits": {
                "rich_text": [{"text": {"content": str(transaction_data.get('last_4_digits', ''))}}]
            },
            "Status": safe_select(transaction_data.get('status'), 'success'),
            "Risk Level": safe_select(transaction_data.get('risk_level'), 'low'),
            "Fraud Score": {
                "number": int(transaction_data.get('fraud_score', 0))
            },
            "AVS Result": safe_select(transaction_data.get('avs_result'), 'unknown'),
            "CVV Result": safe_select(transaction_data.get('cvv_result'), 'unknown'),
            "Customer Country": safe_select(transaction_data.get('customer_country'), 'Unknown'),
            "IP Country": safe_select(transaction_data.get('ip_country'), 'Unknown'),
            "Device Type": safe_select(transaction_data.get('device_type'), 'unknown'),
            "Browser": {
                "rich_text": [{"text": {"content": str(transaction_data.get('browser', ''))}}]
            },
            "Gateway Reference": {
                "rich_text": [{"text": {"content": str(transaction_data.get('gateway_reference', '') or transaction_data.get('transaction_id', ''))}}]
            },
            "Authorization Code": {
                "rich_text": [{"text": {"content": str(transaction_data.get('authorization_code', ''))}}]
            },
            "Settlement Date": {
                "date": {"start": self._format_date(transaction_data.get('settlement_date', ''))} if transaction_data.get('settlement_date') else None
            },
            "Disputed": {
                "checkbox": bool(transaction_data.get('disputed', False))
            }
        }
        
        # Remove Settlement Date if it's None
        if not properties["Settlement Date"]:
            del properties["Settlement Date"]
        
        return properties
    
    def load_transaction(self, transaction_data: Dict, skip_if_exists: bool = True) -> bool:
        """Load single transaction into Notion"""
        try:
            transaction_id = transaction_data.get('transaction_id', '')
            if not transaction_id:
                print("❌ No transaction ID provided")
                return False
            
            # Check if already exists
            if skip_if_exists and self.check_transaction_exists(transaction_id):
                print(f"⏭️  Transaction {transaction_id} already exists - skipping")
                return True
            
            # Create Notion page
            page_data = {
                "parent": {"database_id": self.financial_db_id},
                "properties": self._create_notion_properties(transaction_data)
            }
            
            result = self._make_notion_request('POST', 'pages', page_data)
            
            if result:
                order_number = transaction_data.get('order_number', 'Unknown')
                amount = transaction_data.get('gross_amount', 0)
                tx_type = transaction_data.get('transaction_type', 'unknown')
                print(f"✅ Added {tx_type} transaction for order #{order_number} (${amount:.2f}) to Notion")
                return True
            else:
                print(f"❌ Failed to add transaction {transaction_id} to Notion")
                return False
                
        except Exception as e:
            print(f"❌ Error loading transaction {transaction_data.get('transaction_id', 'unknown')}: {e}")
            return False
    
    def load_transactions_batch(self, transactions_data: List[Dict], skip_if_exists: bool = True) -> Dict:
        """Load multiple transactions into Notion"""
        print(f"💰 Loading {len(transactions_data)} transactions into Notion...")
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, transaction_data in enumerate(transactions_data, 1):
            print(f"   Processing transaction {i}/{len(transactions_data)}")
            
            try:
                # Check if exists first
                transaction_id = transaction_data.get('transaction_id', '')
                if skip_if_exists and self.check_transaction_exists(transaction_id):
                    skipped += 1
                    print(f"   ⏭️  Transaction {transaction_id} already exists - skipping")
                    continue
                
                success = self.load_transaction(transaction_data, skip_if_exists=False)  # Already checked above
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
                print(f"❌ Error processing transaction: {e}")
        
        results = {
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'total': len(transactions_data)
        }
        
        print(f"\n🎉 Financial transactions loading completed!")
        print(f"   ✅ Successfully loaded: {successful}")
        print(f"   ⏭️  Skipped (existing): {skipped}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total processed: {successful + skipped + failed}/{len(transactions_data)}")
        
        return results
    
    def test_connection(self) -> bool:
        """Test connection to Notion database"""
        try:
            result = self._make_notion_request('GET', f'databases/{self.financial_db_id}')
            return bool(result and result.get('id'))
        except Exception as e:
            print(f"❌ Notion connection test failed: {e}")
            return False
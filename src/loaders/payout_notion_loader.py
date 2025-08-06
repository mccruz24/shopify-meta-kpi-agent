import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class PayoutNotionLoader:
    """Load payout analytics data into Notion database with daily granularity"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.financial_db_id = "21e8db45e2f98061a311f3a875b96e16"  # Financial Analytics database
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        print("💰 Payout Notion Loader: Daily payout granularity with gross/net breakdown")
    
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
    
    def check_payout_exists(self, payout_id: str) -> bool:
        """Check if payout already exists in Notion database"""
        try:
            query_data = {
                "filter": {
                    "property": "Payout ID",
                    "title": {
                        "equals": str(payout_id)
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.financial_db_id}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception as e:
            print(f"⚠️  Could not check if payout exists: {e}")
            return False
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for Notion"""
        try:
            if not date_str:
                return datetime.now().date().isoformat()
            
            # Handle Shopify date format
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            
            dt = datetime.fromisoformat(date_str)
            return dt.date().isoformat()
        except Exception as e:
            print(f"⚠️  Date formatting error: {e}")
            return datetime.now().date().isoformat()
    
    def _create_payout_notion_properties(self, payout_data: Dict) -> Dict:
        """Create Notion properties from payout data with enhanced financial breakdown"""
        
        # Helper function to safely create select fields
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        # Calculate derived metrics
        gross_amount = float(payout_data.get('gross_amount', 0))
        processing_fee = float(payout_data.get('processing_fee', 0))
        net_amount = float(payout_data.get('net_amount', 0))
        fee_rate = float(payout_data.get('fee_rate_percent', 0))
        
        properties = {
            # Primary identifiers
            "Payout ID": {
                "title": [{"text": {"content": str(payout_data.get('payout_id', ''))}}]
            },
            "Settlement Date": {
                "date": {"start": self._format_date(payout_data.get('settlement_date', ''))}
            },
            
            # Financial breakdown (main focus)
            "Gross Amount": {
                "number": round(gross_amount, 2)
            },
            "Processing Fee": {
                "number": round(processing_fee, 2)
            },
            "Net Amount (Bank)": {
                "number": round(net_amount, 2)
            },
            "Fee Rate %": {
                "number": round(fee_rate, 2)
            },
            
            # Currency and status
            "Currency": safe_select(payout_data.get('currency'), 'EUR'),
            "Payout Status": safe_select(payout_data.get('payout_status'), 'paid'),
            "Transaction Type": safe_select(payout_data.get('transaction_type_detailed'), 'payout'),
            
            # Additional financial details
            "Refunds Gross": {
                "number": round(float(payout_data.get('refunds_gross', 0)), 2)
            },
            "Refunds Fee": {
                "number": round(float(payout_data.get('refunds_fee', 0)), 2)
            },
            "Adjustments Gross": {
                "number": round(float(payout_data.get('adjustments_gross', 0)), 2)
            },
            "Adjustments Fee": {
                "number": round(float(payout_data.get('adjustments_fee', 0)), 2)
            },
            
            # Reserved funds
            "Reserved Funds Gross": {
                "number": round(float(payout_data.get('reserved_funds_gross', 0)), 2)
            },
            "Reserved Funds Fee": {
                "number": round(float(payout_data.get('reserved_funds_fee', 0)), 2)
            },
            
            # Metadata
            "Data Source": safe_select(payout_data.get('data_source'), 'graphql_payout'),
            "Extraction Date": {
                "date": {"start": datetime.now().date().isoformat()}
            },
            "GraphQL ID": {
                "rich_text": [{"text": {"content": str(payout_data.get('payout_graphql_id', ''))}}]
            }
        }
        
        return properties
    
    def load_payout(self, payout_data: Dict, skip_if_exists: bool = True) -> bool:
        """Load single payout into Notion"""
        try:
            payout_id = str(payout_data.get('payout_id', ''))
            if not payout_id:
                print("❌ No payout ID provided")
                return False
            
            # Check if already exists
            if skip_if_exists and self.check_payout_exists(payout_id):
                print(f"⏭️  Payout {payout_id} already exists - skipping")
                return True
            
            # Create Notion page
            page_data = {
                "parent": {"database_id": self.financial_db_id},
                "properties": self._create_payout_notion_properties(payout_data)
            }
            
            result = self._make_notion_request('POST', 'pages', page_data)
            
            if result:
                settlement_date = payout_data.get('settlement_date_formatted', 'Unknown')
                gross_amount = payout_data.get('gross_amount', 0)
                net_amount = payout_data.get('net_amount', 0)
                currency = payout_data.get('currency', 'EUR')
                
                print(f"✅ Added payout {payout_id} for {settlement_date}")
                print(f"   💰 Gross: {currency}{gross_amount:.2f} → Net: {currency}{net_amount:.2f}")
                return True
            else:
                print(f"❌ Failed to add payout {payout_id} to Notion")
                return False
                
        except Exception as e:
            print(f"❌ Error loading payout {payout_data.get('payout_id', 'unknown')}: {e}")
            return False
    
    def load_payouts_batch(self, payouts_data: List[Dict], skip_if_exists: bool = True) -> Dict:
        """Load multiple payouts into Notion"""
        print(f"💰 Loading {len(payouts_data)} payouts into Notion...")
        
        successful = 0
        failed = 0
        skipped = 0
        
        # Calculate totals for summary
        total_gross = 0
        total_fees = 0
        total_net = 0
        currency = payouts_data[0].get('currency', 'EUR') if payouts_data else 'EUR'
        
        for i, payout_data in enumerate(payouts_data, 1):
            print(f"   Processing payout {i}/{len(payouts_data)}")
            
            try:
                # Check if exists first
                payout_id = str(payout_data.get('payout_id', ''))
                if skip_if_exists and self.check_payout_exists(payout_id):
                    skipped += 1
                    print(f"   ⏭️  Payout {payout_id} already exists - skipping")
                    continue
                
                success = self.load_payout(payout_data, skip_if_exists=False)  # Already checked above
                if success:
                    successful += 1
                    # Add to totals
                    total_gross += float(payout_data.get('gross_amount', 0))
                    total_fees += float(payout_data.get('processing_fee', 0))
                    total_net += float(payout_data.get('net_amount', 0))
                else:
                    failed += 1
                
                # Small delay to avoid rate limits
                if i % 5 == 0:  # Every 5 requests (more conservative for payouts)
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                failed += 1
                print(f"❌ Error processing payout: {e}")
        
        results = {
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'total': len(payouts_data),
            'total_gross': total_gross,
            'total_fees': total_fees,
            'total_net': total_net,
            'currency': currency
        }
        
        print(f"\n🎉 Payout loading completed!")
        print(f"   ✅ Successfully loaded: {successful}")
        print(f"   ⏭️  Skipped (existing): {skipped}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total processed: {successful + skipped + failed}/{len(payouts_data)}")
        
        if successful > 0:
            print(f"\n💰 Financial Summary:")
            print(f"   Gross Amount: {currency}{total_gross:.2f}")
            print(f"   Processing Fees: {currency}{total_fees:.2f}")
            print(f"   Net Amount (Bank): {currency}{total_net:.2f}")
            print(f"   Average Fee Rate: {(total_fees/total_gross*100):.2f}%" if total_gross > 0 else "   Average Fee Rate: 0%")
        
        return results
    
    def test_connection(self) -> bool:
        """Test connection to Notion payout database"""
        try:
            result = self._make_notion_request('GET', f'databases/{self.financial_db_id}')
            if result and result.get('id'):
                print("✅ Notion payout database connection successful")
                return True
            else:
                print("❌ Notion payout database connection failed")
                return False
        except Exception as e:
            print(f"❌ Notion payout connection test failed: {e}")
            return False
    
    def get_recent_payouts(self, days_back: int = 7) -> List[Dict]:
        """Get recent payouts from Notion for verification"""
        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()
            
            query_data = {
                "filter": {
                    "property": "Settlement Date",
                    "date": {
                        "on_or_after": cutoff_date
                    }
                },
                "sorts": [
                    {
                        "property": "Settlement Date",
                        "direction": "descending"
                    }
                ]
            }
            
            result = self._make_notion_request('POST', f'databases/{self.financial_db_id}/query', query_data)
            if result and result.get('results'):
                payouts = []
                for page in result['results']:
                    props = page['properties']
                    payout_info = {
                        'notion_id': page['id'],
                        'payout_id': props.get('Payout ID', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                        'settlement_date': props.get('Settlement Date', {}).get('date', {}).get('start', ''),
                        'gross_amount': props.get('Gross Amount', {}).get('number', 0),
                        'net_amount': props.get('Net Amount (Bank)', {}).get('number', 0),
                        'currency': props.get('Currency', {}).get('select', {}).get('name', 'EUR')
                    }
                    payouts.append(payout_info)
                
                print(f"📊 Found {len(payouts)} recent payouts in Notion")
                return payouts
            
            return []
        except Exception as e:
            print(f"❌ Error getting recent payouts: {e}")
            return []
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class MetaExtractor:
    """Extract KPI data from Meta Ads"""
    
    def __init__(self):
        self.access_token = os.getenv('META_ACCESS_TOKEN')
        self.ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com/v18.0"
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Meta"""
        try:
            url = f"{self.base_url}/{endpoint}"
            request_params = {'access_token': self.access_token}
            if params:
                request_params.update(params)
            
            response = requests.get(url, params=request_params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Meta API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Meta request failed: {e}")
            return None
    
    def get_daily_ad_data(self, date: datetime = None) -> Dict:
        """Get daily advertising spend for P&L sheet"""
        if date is None:
            date = datetime.now() - timedelta(days=1)  # Yesterday
        
        date_str = date.strftime('%Y-%m-%d')
        
        print(f"📱 Extracting Meta Ads spend for {date_str}")
        
        # Get insights for the specific day
        insights_data = self._make_request(f'{self.ad_account_id}/insights', {
            'time_range': f'{{"since":"{date_str}","until":"{date_str}"}}',
            'fields': 'spend,impressions,clicks,ctr,cpc,actions',
            'level': 'account'
        })
        
        if not insights_data or not insights_data.get('data'):
            print(f"ℹ️  No Meta Ads data found for {date_str}")
            return {
                'meta_ad_spend': 0,
                'impressions': 0,
                'clicks': 0,
                'ctr': 0,
                'cpc': 0,
                'roas': 0
            }
        
        insight = insights_data['data'][0]
        spend = float(insight.get('spend', 0))
        impressions = int(insight.get('impressions', 0))
        clicks = int(insight.get('clicks', 0))
        ctr = float(insight.get('ctr', 0))
        cpc = float(insight.get('cpc', 0))
        
        # Calculate ROAS if we have purchase actions
        roas = 0
        actions = insight.get('actions', [])
        purchase_value = 0
        for action in actions:
            if action.get('action_type') == 'purchase':
                purchase_value = float(action.get('value', 0))
                break
        
        if spend > 0 and purchase_value > 0:
            roas = purchase_value / spend
        
        print(f"✅ Meta Ads data:")
        print(f"   Spend: €{spend:.2f}")
        print(f"   Impressions: {impressions:,}")
        print(f"   Clicks: {clicks:,}")
        print(f"   CTR: {ctr:.2f}%")
        print(f"   CPC: €{cpc:.2f}")
        print(f"   ROAS: {roas:.2f}")
        
        return {
            'meta_ad_spend': round(spend, 2),
            'impressions': impressions,
            'clicks': clicks,
            'ctr': round(ctr, 2),
            'cpc': round(cpc, 2),
            'roas': round(roas, 2)
        }
    
    def test_connection(self) -> bool:
        """Test if connection to Meta is working"""
        try:
            account_data = self._make_request(self.ad_account_id, {
                'fields': 'name,account_status'
            })
            return bool(account_data and account_data.get('name'))
        except Exception as e:
            print(f"❌ Meta connection test failed: {e}")
            return False
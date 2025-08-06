import requests
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

class PayoutComparison:
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.rest_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def execute_query(self, query, variables=None):
        """Execute GraphQL query"""
        payload = {'query': query, 'variables': variables or {}}
        response = requests.post(self.graphql_url, headers=self.headers, json=payload)
        return response.json() if response.status_code == 200 else None
    
    def get_rest_request(self, endpoint, params=None):
        """Make REST API request"""
        url = f"{self.rest_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params or {})
        return response.json() if response.status_code == 200 else None
    
    def get_payout_data(self, payout_id="127505695067"):
        """Get specific payout via GraphQL"""
        graphql_id = f"gid://shopify/ShopifyPaymentsPayout/{payout_id}"
        
        query = """
        query getPayout($id: ID!) {
            node(id: $id) {
                ... on ShopifyPaymentsPayout {
                    id
                    legacyResourceId
                    issuedAt
                    status
                    net {
                        amount
                        currencyCode
                    }
                    summary {
                        chargesFee { amount currencyCode }
                        chargesGross { amount currencyCode }
                    }
                }
            }
        }
        """
        
        result = self.execute_query(query, {"id": graphql_id})
        return result.get('data', {}).get('node') if result else None
    
    def get_transactions_for_date(self, date_str="2025-02-26"):
        """Get transactions using current REST approach"""
        target_date = datetime.fromisoformat(date_str)
        local_tz = timezone(timedelta(hours=2))  # CET
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
        end_date = start_date + timedelta(days=1)
        
        # Get orders for the date (mimicking current financial_analytics_extractor.py)
        orders_data = self.get_rest_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if not orders_data or not orders_data.get('orders'):
            return []
        
        orders = orders_data['orders']
        all_transactions = []
        
        for order in orders:
            order_id = order.get('id')
            transactions_data = self.get_rest_request(f'orders/{order_id}/transactions.json')
            
            if transactions_data and transactions_data.get('transactions'):
                for transaction in transactions_data['transactions']:
                    if transaction.get('kind') == 'sale' and transaction.get('status') == 'success':
                        gross_amount = float(transaction.get('amount', 0))
                        # Current approach: estimate 2.9% + €0.30
                        estimated_fee = (gross_amount * 0.029) + 0.30
                        net_amount = gross_amount - estimated_fee
                        
                        all_transactions.append({
                            'order_id': order_id,
                            'transaction_id': transaction.get('id'),
                            'gross_amount': gross_amount,
                            'estimated_fee': estimated_fee,
                            'estimated_net': net_amount,
                            'gateway': transaction.get('gateway', 'unknown')
                        })
        
        return all_transactions
    
    def compare_approaches(self):
        """Compare GraphQL payout vs REST transactions for same date"""
        print("🔍 COMPARISON: GraphQL Payout vs REST Transactions")
        print("=" * 60)
        
        # Get payout data
        payout = self.get_payout_data("127505695067")
        if not payout:
            print("❌ Could not get payout data")
            return
        
        payout_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        print(f"📅 Analyzing data for: {payout_date}")
        print(f"   Payout ID: {payout['legacyResourceId']}")
        
        # GraphQL Payout Data
        actual_gross = float(payout['summary']['chargesGross']['amount'])
        actual_fee = float(payout['summary']['chargesFee']['amount'])
        actual_net = float(payout['net']['amount'])
        
        print(f"\n✅ GRAPHQL PAYOUT DATA (What you SHOULD capture):")
        print(f"   Gross Amount: €{actual_gross:.2f}")
        print(f"   Processing Fee: €{actual_fee:.2f} ({(actual_fee/actual_gross*100):.2f}%)")
        print(f"   Net Amount: €{actual_net:.2f}")
        print(f"   Settlement Date: {payout_date} (actual bank transfer)")
        
        # REST Transactions Data
        transactions = self.get_transactions_for_date(payout_date)
        
        if transactions:
            total_gross = sum(t['gross_amount'] for t in transactions)
            total_estimated_fees = sum(t['estimated_fee'] for t in transactions)
            total_estimated_net = sum(t['estimated_net'] for t in transactions)
            
            print(f"\n⚠️  CURRENT REST APPROACH (What you ARE capturing):")
            print(f"   Transactions Found: {len(transactions)}")
            print(f"   Total Gross: €{total_gross:.2f}")
            print(f"   Estimated Fees: €{total_estimated_fees:.2f} (2.9% + €0.30 per transaction)")
            print(f"   Estimated Net: €{total_estimated_net:.2f}")
            print(f"   Settlement Date: '' (empty)")
            
            print(f"\n📊 COMPARISON:")
            print(f"   Gross Amount: €{actual_gross:.2f} vs €{total_gross:.2f} (difference: €{abs(actual_gross - total_gross):.2f})")
            print(f"   Fees: €{actual_fee:.2f} vs €{total_estimated_fees:.2f} (difference: €{abs(actual_fee - total_estimated_fees):.2f})")
            print(f"   Net Amount: €{actual_net:.2f} vs €{total_estimated_net:.2f} (difference: €{abs(actual_net - total_estimated_net):.2f})")
            
            if abs(actual_fee - total_estimated_fees) > 0.10:
                print(f"\n🚨 SIGNIFICANT DISCREPANCY IN FEES!")
                print(f"   Your current system is off by €{abs(actual_fee - total_estimated_fees):.2f}")
                print(f"   That's {abs((actual_fee - total_estimated_fees)/actual_fee*100):.1f}% error")
        else:
            print(f"\n❌ CURRENT REST APPROACH:")
            print(f"   No transactions found for {payout_date}")
            print(f"   This could mean timing/timezone issues with transaction-level approach")
        
        print(f"\n🎯 RECOMMENDATION:")
        print(f"   ✅ Switch to GraphQL payout-based approach")
        print(f"   ✅ Capture actual fees and settlement dates")
        print(f"   ✅ Get real money movement data instead of estimates")

def main():
    print("🕵️ SINGLE PAYOUT vs CURRENT APPROACH COMPARISON")
    print("=" * 60)
    
    comparator = PayoutComparison()
    comparator.compare_approaches()

if __name__ == "__main__":
    main()
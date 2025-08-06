import requests
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

class July30PayoutInvestigator:
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
    
    def find_july_30_payout(self):
        """Find payout from July 30, 2025"""
        print("🔍 Searching for payout from July 30, 2025...")
        
        query = """
        query findJuly30Payout($first: Int!) {
            shopifyPaymentsAccount {
                payouts(first: $first) {
                    edges {
                        node {
                            id
                            legacyResourceId
                            issuedAt
                            status
                            transactionType
                            net {
                                amount
                                currencyCode
                            }
                            summary {
                                chargesFee { amount currencyCode }
                                chargesGross { amount currencyCode }
                                refundsFee { amount currencyCode }
                                refundsFeeGross { amount currencyCode }
                                adjustmentsFee { amount currencyCode }
                                adjustmentsGross { amount currencyCode }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self.execute_query(query, {"first": 50})  # Get more payouts to find July 30
        
        if not result or result.get('errors'):
            print("❌ Failed to retrieve payouts")
            return None
        
        edges = result.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {}).get('edges', [])
        
        print(f"📊 Found {len(edges)} total payouts, searching for July 30, 2025...")
        
        # Look for July 30, 2025 payout
        target_date = "2025-07-30"
        july_30_payouts = []
        
        for edge in edges:
            payout = edge['node']
            issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
            payout_date = issued_date.strftime('%Y-%m-%d')
            
            print(f"   Checking payout {payout['legacyResourceId']}: {payout_date}")
            
            if payout_date == target_date:
                july_30_payouts.append(payout)
                print(f"   ✅ Found July 30 payout: ID {payout['legacyResourceId']}")
        
        if july_30_payouts:
            return july_30_payouts[0]  # Return first one if multiple
        else:
            print(f"❌ No payout found for {target_date}")
            print("   Available dates:")
            for edge in edges[:10]:  # Show first 10 dates
                payout = edge['node']
                issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
                print(f"      {payout['legacyResourceId']}: {issued_date.strftime('%Y-%m-%d')}")
            return None
    
    def analyze_july_30_payout(self, payout):
        """Deep analysis of July 30 payout"""
        print("\n🔍 JULY 30, 2025 PAYOUT ANALYSIS")
        print("=" * 50)
        
        payout_id = payout['legacyResourceId']
        issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
        
        print(f"📊 PAYOUT DETAILS:")
        print(f"   Payout ID: {payout_id}")
        print(f"   Settlement Date: {issued_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Status: {payout['status']}")
        print(f"   Type: {payout['transactionType']}")
        
        # Financial breakdown
        summary = payout['summary']
        gross_amount = float(summary['chargesGross']['amount'])
        fee_amount = float(summary['chargesFee']['amount'])
        net_amount = float(payout['net']['amount'])
        
        print(f"\n💰 FINANCIAL BREAKDOWN:")
        print(f"   Charges Gross: €{gross_amount:.2f}")
        print(f"   Processing Fee: €{fee_amount:.2f}")
        print(f"   Net Deposited: €{net_amount:.2f}")
        
        if gross_amount > 0:
            fee_percentage = (fee_amount / gross_amount) * 100
            print(f"   Effective Fee Rate: {fee_percentage:.2f}%")
        
        # Check for refunds and adjustments
        refund_gross = float(summary['refundsFeeGross']['amount'])
        refund_fee = float(summary['refundsFee']['amount'])
        adjustment_gross = float(summary['adjustmentsGross']['amount'])
        adjustment_fee = float(summary['adjustmentsFee']['amount'])
        
        if refund_gross > 0 or refund_fee > 0:
            print(f"\n🔄 REFUNDS:")
            print(f"   Refund Gross: €{refund_gross:.2f}")
            print(f"   Refund Fee: €{refund_fee:.2f}")
        
        if adjustment_gross != 0 or adjustment_fee != 0:
            print(f"\n⚖️  ADJUSTMENTS:")
            print(f"   Adjustment Gross: €{adjustment_gross:.2f}")
            print(f"   Adjustment Fee: €{adjustment_fee:.2f}")
        
        # Verification calculation
        calculated_net = gross_amount - fee_amount + adjustment_gross - adjustment_fee - refund_gross - refund_fee
        print(f"\n🧮 CALCULATION VERIFICATION:")
        print(f"   Expected Net: €{calculated_net:.2f}")
        print(f"   Actual Net: €{net_amount:.2f}")
        print(f"   Match: {'✅' if abs(calculated_net - net_amount) < 0.01 else '❌'}")
        
        return payout_id, issued_date.strftime('%Y-%m-%d')
    
    def compare_with_current_approach(self, payout_date="2025-07-30"):
        """Compare with current financial_analytics_extractor approach"""
        print(f"\n🔄 COMPARISON WITH CURRENT APPROACH")
        print("=" * 50)
        
        target_date = datetime.fromisoformat(payout_date)
        local_tz = timezone(timedelta(hours=2))  # CET
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
        end_date = start_date + timedelta(days=1)
        
        print(f"📅 Looking for transactions on {payout_date} using current REST approach...")
        
        # Get orders for the date (current approach)
        orders_data = self.get_rest_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if orders_data and orders_data.get('orders'):
            orders = orders_data['orders']
            print(f"   Found {len(orders)} orders")
            
            total_gross = 0
            total_estimated_fees = 0
            transaction_count = 0
            
            for order in orders:
                order_id = order.get('id')
                transactions_data = self.get_rest_request(f'orders/{order_id}/transactions.json')
                
                if transactions_data and transactions_data.get('transactions'):
                    for transaction in transactions_data['transactions']:
                        if transaction.get('kind') == 'sale' and transaction.get('status') == 'success':
                            gross_amount = float(transaction.get('amount', 0))
                            # Current approach: 2.9% + €0.30 per transaction
                            estimated_fee = (gross_amount * 0.029) + 0.30
                            
                            total_gross += gross_amount
                            total_estimated_fees += estimated_fee
                            transaction_count += 1
            
            total_estimated_net = total_gross - total_estimated_fees
            
            print(f"\n📊 CURRENT REST APPROACH RESULTS:")
            print(f"   Transactions: {transaction_count}")
            print(f"   Gross Amount: €{total_gross:.2f}")
            print(f"   Estimated Fees: €{total_estimated_fees:.2f} (2.9% + €0.30 each)")
            print(f"   Estimated Net: €{total_estimated_net:.2f}")
            print(f"   Settlement Date: '' (empty)")
            
        else:
            print("❌ No orders/transactions found for July 30, 2025")
            print("   This demonstrates the timing issue with transaction-level approach")

def main():
    print("🕵️ JULY 30, 2025 PAYOUT INVESTIGATION")
    print("=" * 60)
    
    investigator = July30PayoutInvestigator()
    
    # Find July 30 payout
    payout = investigator.find_july_30_payout()
    
    if payout:
        # Analyze the payout
        payout_id, date = investigator.analyze_july_30_payout(payout)
        
        # Compare with current approach
        investigator.compare_with_current_approach(date)
        
        print(f"\n🎯 INVESTIGATION SUMMARY:")
        print(f"✅ Found and analyzed payout {payout_id} from {date}")
        print(f"📈 This shows the ACTUAL financial data for July 30, 2025")
        print(f"🔄 Comparison reveals gaps in current transaction-based approach")
        
    else:
        print("\n❌ Could not find payout for July 30, 2025")
        print("   Check the available payout dates shown above")

if __name__ == "__main__":
    main()
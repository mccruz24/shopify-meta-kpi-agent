import requests
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

class RecentPayoutInvestigator:
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
    
    def get_specific_payout(self, payout_id="133241995611"):  # June 27, 2025 payout
        """Get specific recent payout for analysis"""
        print(f"🔍 Analyzing payout ID: {payout_id}")
        
        graphql_id = f"gid://shopify/ShopifyPaymentsPayout/{payout_id}"
        
        query = """
        query getSpecificPayout($id: ID!) {
            node(id: $id) {
                ... on ShopifyPaymentsPayout {
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
                        adjustmentsFee { amount currencyCode }
                        adjustmentsGross { amount currencyCode }
                        chargesFee { amount currencyCode }
                        chargesGross { amount currencyCode }
                        refundsFee { amount currencyCode }
                        refundsFeeGross { amount currencyCode }
                        reservedFundsFee { amount currencyCode }
                        reservedFundsGross { amount currencyCode }
                        retriedPayoutsFee { amount currencyCode }
                        retriedPayoutsGross { amount currencyCode }
                    }
                }
            }
        }
        """
        
        result = self.execute_query(query, {"id": graphql_id})
        
        if not result or result.get('errors'):
            print("❌ Failed to get payout data")
            if result and result.get('errors'):
                for error in result['errors']:
                    print(f"   Error: {error.get('message')}")
            return None
        
        return result.get('data', {}).get('node')
    
    def analyze_payout(self, payout):
        """Deep analysis of the payout"""
        print("\n🔍 PAYOUT DEEP DIVE")
        print("=" * 50)
        
        payout_id = payout['legacyResourceId']
        issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
        payout_date = issued_date.strftime('%Y-%m-%d')
        
        print(f"📊 PAYOUT OVERVIEW:")
        print(f"   Payout ID: {payout_id}")
        print(f"   Settlement Date: {issued_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Status: {payout['status']}")
        print(f"   Type: {payout['transactionType']}")
        print(f"   Net Amount: €{payout['net']['amount']} {payout['net']['currencyCode']}")
        
        # Financial breakdown
        summary = payout['summary']
        gross_amount = float(summary['chargesGross']['amount'])
        fee_amount = float(summary['chargesFee']['amount'])
        net_amount = float(payout['net']['amount'])
        
        print(f"\n💰 FINANCIAL BREAKDOWN:")
        print(f"   Sales Gross: €{gross_amount:.2f}")
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
        
        return payout_date, gross_amount, fee_amount, net_amount
    
    def compare_with_current_approach(self, payout_date, actual_gross, actual_fee, actual_net):
        """Compare with current financial_analytics_extractor approach"""
        print(f"\n🔄 COMPARISON: GraphQL vs Current REST Approach")
        print("=" * 60)
        
        print(f"📅 Analyzing {payout_date}")
        
        # Current approach simulation
        target_date = datetime.fromisoformat(payout_date)
        local_tz = timezone(timedelta(hours=2))  # CET
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
        end_date = start_date + timedelta(days=1)
        
        print(f"\n✅ GRAPHQL PAYOUT DATA (Actual Financial Reality):")
        print(f"   Gross Sales: €{actual_gross:.2f}")
        print(f"   Processing Fee: €{actual_fee:.2f} ({(actual_fee/actual_gross*100):.2f}%)")
        print(f"   Net Amount: €{actual_net:.2f}")
        print(f"   Settlement Date: {payout_date} (money in bank)")
        
        # Try current REST approach
        orders_data = self.get_rest_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if orders_data and orders_data.get('orders'):
            orders = orders_data['orders']
            
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
            
            print(f"\n⚠️  CURRENT REST APPROACH (What you're capturing now):")
            print(f"   Transactions Found: {transaction_count}")
            print(f"   Total Gross: €{total_gross:.2f}")
            print(f"   Estimated Fees: €{total_estimated_fees:.2f} (2.9% + €0.30 each)")
            print(f"   Estimated Net: €{total_estimated_net:.2f}")
            print(f"   Settlement Date: '' (empty)")
            
            print(f"\n📊 ACCURACY COMPARISON:")
            gross_diff = abs(actual_gross - total_gross)
            fee_diff = abs(actual_fee - total_estimated_fees)
            net_diff = abs(actual_net - total_estimated_net)
            
            print(f"   Gross Amount: €{gross_diff:.2f} difference")
            print(f"   Fees: €{fee_diff:.2f} difference ({((fee_diff/actual_fee)*100):.1f}% error)")
            print(f"   Net Amount: €{net_diff:.2f} difference")
            
            if fee_diff > 0.50:
                print(f"\n🚨 SIGNIFICANT FEE DISCREPANCY!")
                print(f"   Your system is off by €{fee_diff:.2f} on fees")
                if actual_fee > total_estimated_fees:
                    print(f"   You're UNDERESTIMATING fees by {((fee_diff/actual_fee)*100):.1f}%")
                else:
                    print(f"   You're OVERESTIMATING fees by {((fee_diff/actual_fee)*100):.1f}%")
        else:
            print(f"\n❌ CURRENT REST APPROACH:")
            print(f"   No transactions found for {payout_date}")
            print(f"   This shows the timing/data alignment issue")
        
        print(f"\n🎯 KEY INSIGHTS:")
        print(f"   ✅ GraphQL gives you ACTUAL money movements")
        print(f"   ✅ Real settlement dates for cash flow tracking")
        print(f"   ✅ Accurate fee calculations (not estimates)")
        print(f"   ❌ Current approach misses real financial timing")

def main():
    print("🕵️ RECENT PAYOUT INVESTIGATION")
    print("=" * 60)
    print("Since July 30, 2025 payout doesn't exist, analyzing most recent available:")
    print("Payout ID: 133241995611 (June 27, 2025)")
    
    investigator = RecentPayoutInvestigator()
    
    # Get the most recent payout (June 27, 2025)
    payout = investigator.get_specific_payout("133241995611")
    
    if payout:
        # Analyze the payout
        payout_date, gross, fee, net = investigator.analyze_payout(payout)
        
        # Compare with current approach
        investigator.compare_with_current_approach(payout_date, gross, fee, net)
        
        print(f"\n🎯 INVESTIGATION SUMMARY:")
        print(f"✅ Analyzed most recent payout from {payout_date}")
        print(f"📈 Shows actual vs estimated financial data")
        print(f"🔄 Reveals accuracy issues in current approach")
        
    else:
        print("\n❌ Could not retrieve payout data")

if __name__ == "__main__":
    main()
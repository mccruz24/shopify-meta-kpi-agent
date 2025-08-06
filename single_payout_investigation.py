import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SinglePayoutInvestigator:
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
    
    def get_specific_payout(self, payout_id="127505695067"):
        """Get a specific payout by ID for detailed analysis"""
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
        
        variables = {"id": graphql_id}
        result = self.execute_query(query, variables)
        
        if not result:
            print("❌ No response from GraphQL query")
            return None
            
        if result.get('errors'):
            print("❌ GraphQL Errors:")
            for error in result['errors']:
                print(f"   - {error.get('message')}")
            return None
        
        node = result.get('data', {}).get('node')
        if not node:
            print(f"❌ No payout found with ID: {payout_id}")
            print(f"   Full response: {json.dumps(result, indent=2)}")
            return None
            
        return node
    
    def analyze_single_payout(self, payout):
        """Deep dive analysis of a single payout"""
        print("🔍 SINGLE PAYOUT DEEP DIVE")
        print("=" * 50)
        
        payout_id = payout['legacyResourceId']
        issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
        
        print(f"📊 PAYOUT OVERVIEW:")
        print(f"   ID: {payout_id}")
        print(f"   Date: {issued_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Status: {payout['status']}")
        print(f"   Type: {payout['transactionType']}")
        print(f"   Net Amount: €{payout['net']['amount']} {payout['net']['currencyCode']}")
        
        summary = payout['summary']
        
        print(f"\n💰 FINANCIAL BREAKDOWN:")
        print(f"   Charges Gross: €{summary['chargesGross']['amount']}")
        print(f"   Charges Fee: €{summary['chargesFee']['amount']}")
        
        gross_amount = float(summary['chargesGross']['amount'])
        fee_amount = float(summary['chargesFee']['amount'])
        net_amount = float(payout['net']['amount'])
        
        if gross_amount > 0:
            fee_percentage = (fee_amount / gross_amount) * 100
            print(f"   Fee Percentage: {fee_percentage:.2f}%")
        
        print(f"   Net Amount: €{net_amount}")
        print(f"   Calculation Check: €{gross_amount} - €{fee_amount} = €{gross_amount - fee_amount:.2f}")
        
        # Check for other fees
        other_fees = []
        if float(summary['refundsFee']['amount']) > 0:
            other_fees.append(f"Refunds Fee: €{summary['refundsFee']['amount']}")
        if float(summary['adjustmentsFee']['amount']) > 0:
            other_fees.append(f"Adjustments Fee: €{summary['adjustmentsFee']['amount']}")
        if float(summary['reservedFundsFee']['amount']) > 0:
            other_fees.append(f"Reserved Funds Fee: €{summary['reservedFundsFee']['amount']}")
        
        if other_fees:
            print(f"\n⚠️  OTHER FEES:")
            for fee in other_fees:
                print(f"   {fee}")
        
        return payout_id, issued_date

def main():
    print("🕵️ SINGLE PAYOUT INVESTIGATION")
    print("=" * 50)
    
    investigator = SinglePayoutInvestigator()
    
    # Get specific payout for analysis
    print("Attempting to get payout ID: 127505695067")
    payout = investigator.get_specific_payout("127505695067")
    
    if payout:
        payout_id, date = investigator.analyze_single_payout(payout)
        
        print(f"\n🎯 SUMMARY:")
        print(f"✅ Successfully analyzed payout {payout_id} from {date.strftime('%Y-%m-%d')}")
        print(f"📈 This payout shows ACTUAL financial data from Shopify Payments")
        print(f"🔄 This is what your financial_analytics_extractor should capture")
        
    else:
        print("❌ No payout data available")

if __name__ == "__main__":
    main()
import requests
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class PayoutDataInvestigator:
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def execute_query(self, query, variables=None):
        """Execute GraphQL query"""
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ GraphQL error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ GraphQL request failed: {e}")
            return None
    
    def get_detailed_payouts(self, limit=20):
        """Get detailed payout data for investigation"""
        print(f"\n🔍 Investigating {limit} recent payouts...")
        
        query = """
        query getDetailedPayouts($first: Int!) {
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
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                    }
                }
            }
        }
        """
        
        variables = {"first": limit}
        result = self.execute_query(query, variables)
        
        if not result or result.get('errors'):
            print("❌ Failed to retrieve payout data")
            return []
        
        payouts = result.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {})
        edges = payouts.get('edges', [])
        
        print(f"✅ Retrieved {len(edges)} payouts")
        return [edge['node'] for edge in edges]
    
    def analyze_payout_data(self, payouts):
        """Analyze payout data structure and content"""
        print("\n📊 PAYOUT DATA ANALYSIS")
        print("=" * 60)
        
        if not payouts:
            print("❌ No payouts to analyze")
            return
        
        # Overall statistics
        total_payouts = len(payouts)
        total_net = sum(float(p['net']['amount']) for p in payouts)
        total_fees = sum(float(p['summary']['chargesFee']['amount']) for p in payouts)
        total_gross = sum(float(p['summary']['chargesGross']['amount']) for p in payouts)
        
        print(f"📈 SUMMARY:")
        print(f"   Total Payouts: {total_payouts}")
        print(f"   Total Net Amount: €{total_net:.2f}")
        print(f"   Total Fees: €{total_fees:.2f}")
        print(f"   Total Gross Sales: €{total_gross:.2f}")
        print(f"   Average Fee Rate: {(total_fees/total_gross*100):.2f}% (if gross > 0)")
        
        # Date range
        dates = [datetime.fromisoformat(p['issuedAt'].replace('Z', '+00:00')) for p in payouts]
        if dates:
            print(f"   Date Range: {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")
        
        print(f"\n🔍 DETAILED PAYOUT BREAKDOWN:")
        print("-" * 60)
        
        for i, payout in enumerate(payouts[:10], 1):  # Show first 10 in detail
            issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            
            print(f"\n{i}. Payout ID: {payout['legacyResourceId']}")
            print(f"   Date: {issued_date}")
            print(f"   Status: {payout['status']}")
            print(f"   Type: {payout['transactionType']}")
            print(f"   Net Amount: €{payout['net']['amount']} {payout['net']['currencyCode']}")
            
            summary = payout['summary']
            print(f"   📊 Breakdown:")
            print(f"      Charges Gross: €{summary['chargesGross']['amount']}")
            print(f"      Charges Fee: €{summary['chargesFee']['amount']}")
            
            if float(summary['refundsFeeGross']['amount']) > 0:
                print(f"      Refunds Gross: €{summary['refundsFeeGross']['amount']}")
                print(f"      Refunds Fee: €{summary['refundsFee']['amount']}")
            
            if float(summary['adjustmentsGross']['amount']) != 0:
                print(f"      Adjustments Gross: €{summary['adjustmentsGross']['amount']}")
                print(f"      Adjustments Fee: €{summary['adjustmentsFee']['amount']}")
        
        if total_payouts > 10:
            print(f"\n... and {total_payouts - 10} more payouts")
    
    def compare_with_current_approach(self, payouts):
        """Compare GraphQL payout data with current REST approach"""
        print(f"\n🔄 COMPARISON: GraphQL vs Current REST Approach")
        print("=" * 60)
        
        if not payouts:
            return
        
        # Take the most recent payout for comparison
        latest_payout = payouts[0]
        payout_date = datetime.fromisoformat(latest_payout['issuedAt'].replace('Z', '+00:00'))
        
        print(f"📅 Analyzing payout from {payout_date.strftime('%Y-%m-%d')}")
        print(f"   Payout ID: {latest_payout['legacyResourceId']}")
        
        # GraphQL data
        actual_gross = float(latest_payout['summary']['chargesGross']['amount'])
        actual_fee = float(latest_payout['summary']['chargesFee']['amount'])
        actual_net = float(latest_payout['net']['amount'])
        actual_fee_rate = (actual_fee / actual_gross * 100) if actual_gross > 0 else 0
        
        # Current approach estimate (2.9% + €0.30 per transaction)
        # This is a rough estimate - we'd need to know transaction count
        estimated_fee_rate = 2.9  # %
        estimated_fee = actual_gross * (estimated_fee_rate / 100)
        estimated_net = actual_gross - estimated_fee
        
        print(f"\n📊 FINANCIAL DATA COMPARISON:")
        print(f"   Gross Amount: €{actual_gross:.2f} (both methods)")
        print(f"   ")
        print(f"   FEES:")
        print(f"   🔹 GraphQL (Actual): €{actual_fee:.2f} ({actual_fee_rate:.2f}%)")
        print(f"   🔹 Current Method (Est): €{estimated_fee:.2f} ({estimated_fee_rate:.1f}%)")
        print(f"   🔹 Difference: €{abs(actual_fee - estimated_fee):.2f}")
        print(f"   ")
        print(f"   NET AMOUNT:")
        print(f"   🔹 GraphQL (Actual): €{actual_net:.2f}")
        print(f"   🔹 Current Method (Est): €{estimated_net:.2f}")
        print(f"   🔹 Difference: €{abs(actual_net - estimated_net):.2f}")
        
        # Settlement timing
        print(f"\n📅 SETTLEMENT TIMING:")
        print(f"   🔹 GraphQL: {latest_payout['issuedAt']} (actual payout date)")
        print(f"   🔹 Current Method: Empty string (no settlement data)")
        
        print(f"\n✅ CONCLUSION:")
        if abs(actual_fee - estimated_fee) > 0.50:  # If difference is more than 50 cents
            print(f"   ⚠️  Significant difference in fee calculation!")
            print(f"   📈 GraphQL provides ACTUAL fee data vs estimates")
        else:
            print(f"   ✅ Fee estimates are reasonably close")
        
        print(f"   🎯 GraphQL provides:")
        print(f"      - Actual settlement dates (not empty)")
        print(f"      - Real fee breakdowns (not estimates)")
        print(f"      - Payout-level view (vs transaction-level)")

def main():
    print("🕵️ SHOPIFY PAYOUT DATA INVESTIGATION")
    print("=" * 60)
    
    investigator = PayoutDataInvestigator()
    
    # Get detailed payout data
    payouts = investigator.get_detailed_payouts(limit=20)
    
    if payouts:
        # Analyze the data
        investigator.analyze_payout_data(payouts)
        
        # Compare with current approach
        investigator.compare_with_current_approach(payouts)
        
        print(f"\n🎯 INVESTIGATION SUMMARY:")
        print(f"✅ GraphQL payout queries provide:")
        print(f"   - Real settlement dates and amounts")
        print(f"   - Actual fee breakdowns (not estimates)")
        print(f"   - Comprehensive payout summary data")
        print(f"   - Better accuracy for financial analytics")
    else:
        print("❌ No payout data available for investigation")

if __name__ == "__main__":
    main()
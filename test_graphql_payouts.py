import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class ShopifyGraphQLTester:
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
    
    def test_payouts_query(self):
        """Test basic shopifyPaymentsPayout query"""
        print("\n🔍 Testing shopifyPaymentsPayout query...")
        
        query = """
        query getPayouts($first: Int!) {
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
                                adjustmentsFee {
                                    amount
                                    currencyCode
                                }
                                adjustmentsGross {
                                    amount
                                    currencyCode
                                }
                                chargesFee {
                                    amount
                                    currencyCode
                                }
                                chargesGross {
                                    amount
                                    currencyCode
                                }
                                refundsFee {
                                    amount
                                    currencyCode
                                }
                                refundsFeeGross {
                                    amount
                                    currencyCode
                                }
                                reservedFundsFee {
                                    amount
                                    currencyCode
                                }
                                reservedFundsGross {
                                    amount
                                    currencyCode
                                }
                                retriedPayoutsFee {
                                    amount
                                    currencyCode
                                }
                                retriedPayoutsGross {
                                    amount
                                    currencyCode
                                }
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
        
        variables = {"first": 10}
        result = self.execute_query(query, variables)
        
        if result:
            if 'errors' in result:
                print("❌ GraphQL Errors:")
                for error in result['errors']:
                    print(f"   - {error.get('message', 'Unknown error')}")
                return False
            
            payouts = result.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {})
            edges = payouts.get('edges', [])
            
            print(f"✅ Found {len(edges)} payouts")
            
            if edges:
                print("\n📋 Sample Payout Data:")
                payout = edges[0]['node']
                print(f"   ID: {payout.get('id')}")
                print(f"   Legacy ID: {payout.get('legacyResourceId')}")
                print(f"   Issued At: {payout.get('issuedAt')}")
                print(f"   Status: {payout.get('status')}")
                print(f"   Transaction Type: {payout.get('transactionType')}")
                
                net = payout.get('net', {})
                print(f"   Net Amount: {net.get('amount')} {net.get('currencyCode')}")
                
                summary = payout.get('summary', {})
                if summary:
                    print("\n   💰 Fee/Gross Breakdown:")
                    for fee_type in ['charges', 'refunds', 'adjustments']:
                        fee = summary.get(f'{fee_type}Fee', {})
                        gross = summary.get(f'{fee_type}Gross', {})
                        if fee.get('amount') or gross.get('amount'):
                            print(f"     {fee_type.title()}: Fee={fee.get('amount', 0)} Gross={gross.get('amount', 0)}")
                
                return True
            else:
                print("ℹ️  No payouts found in response")
                return False
        
        return False
    
    def test_specific_payout_query(self, payout_id=None):
        """Test querying a specific payout by ID"""
        if not payout_id:
            print("⚠️  No payout ID provided for specific test")
            return False
            
        print(f"\n🔍 Testing specific payout query for ID: {payout_id}")
        
        query = """
        query getPayout($id: ID!) {
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
        
        variables = {"id": payout_id}
        result = self.execute_query(query, variables)
        
        if result and not result.get('errors'):
            node = result.get('data', {}).get('node')
            if node:
                print("✅ Successfully retrieved specific payout")
                return True
            else:
                print("❌ Payout not found or access denied")
                return False
        else:
            if result and result.get('errors'):
                for error in result['errors']:
                    print(f"❌ Error: {error.get('message')}")
            return False

def main():
    print("🧪 Testing Shopify GraphQL Payout Queries")
    print("=" * 50)
    
    tester = ShopifyGraphQLTester()
    
    # First test REST API connection
    print("🔍 Testing REST API connection first...")
    try:
        response = requests.get(
            f"{tester.rest_url}/shop.json",
            headers=tester.headers
        )
        if response.status_code == 200:
            shop_data = response.json()
            print(f"✅ REST API connection successful")
            print(f"   Shop: {shop_data.get('shop', {}).get('name', 'Unknown')}")
        else:
            print(f"❌ REST API failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ REST API connection failed: {e}")
        return
    
    # Test basic payouts query
    success = tester.test_payouts_query()
    
    if not success:
        print("\n❌ Failed to retrieve payout data. This could be due to:")
        print("   1. Missing Shopify Payments payout permissions")
        print("   2. No Shopify Payments account configured")
        print("   3. No payouts available in the account")
        print("   4. GraphQL API version compatibility issues")
    
    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    if success:
        print("✅ GraphQL payout queries are working!")
        print("   - The data structure matches your financial analytics needs")
        print("   - You can access real fee breakdowns and settlement timing")
        print("   - This is much more accurate than the current REST approach")
    else:
        print("⚠️  GraphQL payout queries need troubleshooting:")
        print("   - Check app permissions for 'read_shopify_payments_payouts'")
        print("   - Verify Shopify Payments is enabled for this store")
        print("   - Consider using a different API version")

if __name__ == "__main__":
    main()
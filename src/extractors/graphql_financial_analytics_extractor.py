import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class GraphQLFinancialAnalyticsExtractor:
    """Extract accurate financial analytics data using Shopify GraphQL API"""
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def _execute_graphql_query(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Execute GraphQL query against Shopify API"""
        try:
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errors'):
                    print(f"❌ GraphQL errors: {result['errors']}")
                    return None
                return result
            else:
                print(f"❌ GraphQL API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ GraphQL request failed: {e}")
            return None
    
    def get_payouts_for_date_range(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Get all payouts within a date range"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        print(f"💰 Extracting GraphQL payout data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # GraphQL query for payouts with comprehensive financial breakdown
        query = """
        query getPayoutsInRange($first: Int!) {
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
        
        # Get more payouts to ensure we capture the date range
        result = self._execute_graphql_query(query, {"first": 100})
        
        if not result or not result.get('data'):
            print("❌ No payout data retrieved")
            return []
        
        payouts_data = result.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {})
        edges = payouts_data.get('edges', [])
        
        if not edges:
            print("ℹ️  No payouts found")
            return []
        
        # Filter payouts by date range
        filtered_payouts = []
        
        # Ensure start_date and end_date are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        for edge in edges:
            payout = edge['node']
            issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
            
            # Check if payout falls within our date range
            if start_date <= issued_date <= end_date:
                # Transform payout data into financial analytics format
                payout_data = self._transform_payout_to_financial_data(payout)
                filtered_payouts.append(payout_data)
        
        print(f"✅ Found {len(filtered_payouts)} payouts in date range")
        return filtered_payouts
    
    def _transform_payout_to_financial_data(self, payout: Dict) -> Dict:
        """Transform GraphQL payout data into financial analytics format"""
        
        summary = payout['summary']
        issued_date = datetime.fromisoformat(payout['issuedAt'].replace('Z', '+00:00'))
        
        # Extract financial amounts
        gross_amount = float(summary['chargesGross']['amount'])
        processing_fee = float(summary['chargesFee']['amount'])
        net_amount = float(payout['net']['amount'])
        
        # Handle refunds and adjustments
        refund_gross = float(summary['refundsFeeGross']['amount'])
        refund_fee = float(summary['refundsFee']['amount'])
        adjustment_gross = float(summary['adjustmentsGross']['amount'])
        adjustment_fee = float(summary['adjustmentsFee']['amount'])
        
        # Calculate effective fee rate
        fee_rate = (processing_fee / gross_amount * 100) if gross_amount > 0 else 0
        
        # Build comprehensive financial record
        financial_data = {
            'payout_id': payout['legacyResourceId'],
            'settlement_date': issued_date.isoformat(),
            'settlement_date_formatted': issued_date.strftime('%Y-%m-%d'),
            'payout_status': payout['status'],
            'transaction_type': payout['transactionType'],
            
            # Core financial metrics (what actually matters for analytics)
            'gross_sales': gross_amount,
            'processing_fee': processing_fee,
            'net_amount': net_amount,
            'fee_rate_percent': round(fee_rate, 2),
            'currency': summary['chargesGross']['currencyCode'],
            
            # Refunds and adjustments
            'refunds_gross': refund_gross,
            'refunds_fee': refund_fee,
            'adjustments_gross': adjustment_gross,
            'adjustments_fee': adjustment_fee,
            
            # Additional fees
            'reserved_funds_fee': float(summary['reservedFundsFee']['amount']),
            'reserved_funds_gross': float(summary['reservedFundsGross']['amount']),
            'retried_payouts_fee': float(summary['retriedPayoutsFee']['amount']),
            'retried_payouts_gross': float(summary['retriedPayoutsGross']['amount']),
            
            # Metadata
            'data_source': 'graphql_payout',
            'extraction_timestamp': datetime.now().isoformat(),
            'payout_graphql_id': payout['id']
        }
        
        return financial_data
    
    def get_single_date_payouts(self, date: datetime = None) -> List[Dict]:
        """Get payouts for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        # Set date range for the entire day
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        return self.get_payouts_for_date_range(start_date, end_date)
    
    def get_payout_by_id(self, payout_id: str) -> Optional[Dict]:
        """Get specific payout by ID for detailed analysis"""
        
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
        
        result = self._execute_graphql_query(query, {"id": graphql_id})
        
        if not result or not result.get('data', {}).get('node'):
            print(f"❌ Payout {payout_id} not found")
            return None
        
        payout = result['data']['node']
        return self._transform_payout_to_financial_data(payout)
    
    def get_financial_summary_for_period(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Get aggregated financial summary for a date period"""
        
        payouts = self.get_payouts_for_date_range(start_date, end_date)
        
        if not payouts:
            return {
                'total_payouts': 0,
                'total_gross_sales': 0,
                'total_processing_fees': 0,
                'total_net_amount': 0,
                'average_fee_rate': 0,
                'total_refunds': 0,
                'total_adjustments': 0,
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d') if end_date else start_date.strftime('%Y-%m-%d')}"
            }
        
        # Calculate aggregated metrics
        total_gross = sum(p['gross_sales'] for p in payouts)
        total_fees = sum(p['processing_fee'] for p in payouts)
        total_net = sum(p['net_amount'] for p in payouts)
        total_refunds = sum(p['refunds_gross'] for p in payouts)
        total_adjustments = sum(p['adjustments_gross'] for p in payouts)
        
        average_fee_rate = (total_fees / total_gross * 100) if total_gross > 0 else 0
        
        return {
            'total_payouts': len(payouts),
            'total_gross_sales': round(total_gross, 2),
            'total_processing_fees': round(total_fees, 2),
            'total_net_amount': round(total_net, 2),
            'average_fee_rate': round(average_fee_rate, 2),
            'total_refunds': round(total_refunds, 2),
            'total_adjustments': round(total_adjustments, 2),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d') if end_date else start_date.strftime('%Y-%m-%d')}",
            'currency': payouts[0]['currency'] if payouts else 'EUR'
        }
    
    def test_connection(self) -> bool:
        """Test GraphQL connection and payout access"""
        try:
            query = """
            query testPayoutAccess {
                shopifyPaymentsAccount {
                    payouts(first: 1) {
                        edges {
                            node {
                                id
                                legacyResourceId
                                status
                            }
                        }
                    }
                }
            }
            """
            
            result = self._execute_graphql_query(query)
            
            if result and result.get('data', {}).get('shopifyPaymentsAccount'):
                print("✅ GraphQL payout connection successful")
                return True
            else:
                print("❌ GraphQL payout connection failed")
                return False
                
        except Exception as e:
            print(f"❌ GraphQL connection test failed: {e}")
            return False
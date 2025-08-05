#!/usr/bin/env python3
"""
Enhanced Financial Notion Loader
Loads detailed fee breakdowns, currency conversion data, and multi-perspective financial analytics
into Notion with proper database structure for:
1. Sales Performance tracking
2. Cash Flow analysis
3. Settlement details with fee breakdown
4. Currency conversion tracking
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class EnhancedFinancialNotionLoader:
    """Load enhanced financial analytics data into Notion with detailed fee breakdown"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        
        # Database IDs for different perspectives
        self.financial_transactions_db = "21e8db45e2f98061a311f3a875b96e16"  # Enhanced transactions
        self.sales_performance_db = "21e8db45e2f980b99159f9da13f924a8"     # Sales/orders data
        self.settlement_analytics_db = None  # To be created
        
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
    
    def load_multi_perspective_data(self, financial_data: Dict) -> Dict:
        """Load all perspectives of financial data into Notion"""
        
        results = {
            'sales_performance': {'loaded': 0, 'skipped': 0, 'failed': 0},
            'cash_flow': {'loaded': 0, 'skipped': 0, 'failed': 0},
            'enhanced_transactions': {'loaded': 0, 'skipped': 0, 'failed': 0}
        }
        
        date = financial_data['date']
        print(f"💰 Loading multi-perspective financial data for {date}")
        
        # Load sales performance data
        sales_results = self.load_sales_performance(financial_data['sales_performance'])
        results['sales_performance'] = sales_results
        
        # Load enhanced transactions with detailed fees
        cash_results = self.load_enhanced_transactions(financial_data['cash_flow'])
        results['enhanced_transactions'] = cash_results
        
        # TODO: Load settlement analytics when we have the database
        
        return results
    
    def load_sales_performance(self, sales_data: Dict) -> Dict:
        """Load sales performance data (orders created perspective)"""
        
        print("📊 Loading sales performance data...")
        
        results = {'loaded': 0, 'skipped': 0, 'failed': 0}
        
        for order in sales_data['orders']:
            try:
                if self.load_single_order(order):
                    results['loaded'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                print(f"❌ Error loading order {order.get('order_number', 'unknown')}: {e}")
                results['failed'] += 1
        
        return results
    
    def load_enhanced_transactions(self, cash_flow_data: Dict) -> Dict:
        """Load enhanced transactions with detailed fee breakdown"""
        
        print("💳 Loading enhanced transactions with fee breakdown...")
        
        results = {'loaded': 0, 'skipped': 0, 'failed': 0}
        
        for transaction in cash_flow_data['transactions']:
            try:
                if self.load_single_enhanced_transaction(transaction):
                    results['loaded'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                print(f"❌ Error loading transaction {transaction.get('transaction_id', 'unknown')}: {e}")
                results['failed'] += 1
        
        return results
    
    def load_single_order(self, order_data: Dict) -> bool:
        """Load a single order into sales performance database"""
        
        order_id = order_data.get('order_id', '')
        if not order_id:
            return False
        
        # Check if order already exists
        if self.check_order_exists(order_id):
            print(f"⏭️  Order {order_data.get('order_number')} already exists - skipping")
            return True
        
        properties = self._create_order_properties(order_data)
        
        page_data = {
            "parent": {"database_id": self.sales_performance_db},
            "properties": properties
        }
        
        result = self._make_notion_request('POST', 'pages', page_data)
        
        if result:
            print(f"✅ Added order {order_data.get('order_number')} (€{order_data.get('gross_amount', 0):.2f})")
            return True
        else:
            print(f"❌ Failed to add order {order_data.get('order_number')}")
            return False
    
    def load_single_enhanced_transaction(self, transaction_data: Dict) -> bool:
        """Load a single enhanced transaction with detailed fees"""
        
        transaction_id = transaction_data.get('transaction_id', '')
        if not transaction_id:
            return False
        
        # Check if transaction already exists
        if self.check_transaction_exists(transaction_id):
            print(f"⏭️  Transaction {transaction_id} already exists - skipping")
            return True
        
        properties = self._create_enhanced_transaction_properties(transaction_data)
        
        page_data = {
            "parent": {"database_id": self.financial_transactions_db},
            "properties": properties
        }
        
        result = self._make_notion_request('POST', 'pages', page_data)
        
        if result:
            print(f"✅ Added enhanced transaction {transaction_id} (€{transaction_data.get('gross_amount', 0):.2f})")
            return True
        else:
            print(f"❌ Failed to add transaction {transaction_id}")
            return False
    
    def _create_order_properties(self, order_data: Dict) -> Dict:
        """Create Notion properties for order data"""
        
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        return {
            "Order ID": {
                "title": [{"text": {"content": str(order_data.get('order_id', ''))}}]
            },
            "Order Number": {
                "rich_text": [{"text": {"content": str(order_data.get('order_number', ''))}}]
            },
            "Created At": {
                "date": {"start": self._format_date(order_data.get('created_at', ''))}
            },
            "Gross Amount": {
                "number": round(float(order_data.get('gross_amount', 0)), 2)
            },
            "Net Amount": {
                "number": round(float(order_data.get('net_amount', 0)), 2)
            },
            "Discounts": {
                "number": round(float(order_data.get('discounts', 0)), 2)
            },
            "Tax": {
                "number": round(float(order_data.get('tax', 0)), 2)
            },
            "Shipping": {
                "number": round(float(order_data.get('shipping', 0)), 2)
            },
            "Currency": safe_select(order_data.get('currency'), 'USD'),
            "Financial Status": safe_select(order_data.get('financial_status'), 'unknown')
        }
    
    def _create_enhanced_transaction_properties(self, transaction_data: Dict) -> Dict:
        """Create Notion properties for enhanced transaction data with detailed fees"""
        
        def safe_select(value, default='Unknown'):
            return {"select": {"name": str(value) if value is not None else default}}
        
        # Base transaction properties
        properties = {
            "Transaction ID": {
                "title": [{"text": {"content": str(transaction_data.get('transaction_id', ''))}}]
            },
            "Order ID": {
                "rich_text": [{"text": {"content": str(transaction_data.get('order_id', ''))}}]
            },
            "Order Number": {
                "rich_text": [{"text": {"content": str(transaction_data.get('order_number', ''))}}]
            },
            "Created At": {
                "date": {"start": self._format_date(transaction_data.get('created_at', ''))}
            },
            "Transaction Type": safe_select(transaction_data.get('kind'), 'sale'),
            "Status": safe_select(transaction_data.get('status'), 'success'),
            "Gateway": safe_select(transaction_data.get('gateway'), 'shopify_payments'),
            
            # Financial amounts
            "Gross Amount": {
                "number": round(float(transaction_data.get('gross_amount', 0)), 2)
            },
            "Net Amount": {
                "number": round(float(transaction_data.get('net_amount', 0)), 2)
            },
            "Currency": safe_select(transaction_data.get('currency'), 'USD'),
            
            # Detailed fee breakdown
            "Shopify Payment Fee": {
                "number": round(float(transaction_data.get('shopify_payment_fee', 0)), 2)
            },
            "Currency Conversion Fee": {
                "number": round(float(transaction_data.get('currency_conversion_fee', 0)), 2)
            },
            "Transaction Fee": {
                "number": round(float(transaction_data.get('transaction_fee', 0)), 2)
            },
            "VAT on Fees": {
                "number": round(float(transaction_data.get('vat_on_fees', 0)), 2)
            },
            "Total Fees": {
                "number": round(float(transaction_data.get('total_fees', 0)), 2)
            }
        }
        
        # Add currency conversion details if present
        if transaction_data.get('original_currency'):
            properties.update({
                "Original Amount": {
                    "number": round(float(transaction_data.get('original_amount', 0)), 2)
                },
                "Original Currency": safe_select(transaction_data.get('original_currency'), 'USD'),
                "Converted Amount": {
                    "number": round(float(transaction_data.get('converted_amount', 0)), 2)
                },
                "Exchange Rate": {
                    "number": round(float(transaction_data.get('exchange_rate', 1.0)), 4)
                },
                "Conversion Date": {
                    "date": {"start": self._format_date(transaction_data.get('conversion_date', ''))}
                }
            })
        
        return properties
    
    def check_order_exists(self, order_id: str) -> bool:
        """Check if order already exists in Notion database"""
        try:
            query_data = {
                "filter": {
                    "property": "Order ID",
                    "title": {
                        "equals": order_id
                    }
                }
            }
            
            result = self._make_notion_request('POST', f'databases/{self.sales_performance_db}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception:
            return False
    
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
            
            result = self._make_notion_request('POST', f'databases/{self.financial_transactions_db}/query', query_data)
            if result and result.get('results'):
                return len(result['results']) > 0
            
            return False
        except Exception:
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
    
    def test_connection(self) -> bool:
        """Test connection to Notion database"""
        try:
            result = self._make_notion_request('GET', f'databases/{self.financial_transactions_db}')
            return bool(result and result.get('id'))
        except Exception as e:
            print(f"❌ Notion connection test failed: {e}")
            return False
    
    def create_summary_report(self, results: Dict, date: str) -> Dict:
        """Create a summary report of the loading process"""
        
        total_loaded = sum(r['loaded'] for r in results.values())
        total_failed = sum(r['failed'] for r in results.values())
        total_skipped = sum(r['skipped'] for r in results.values())
        
        report = {
            'date': date,
            'summary': {
                'total_loaded': total_loaded,
                'total_failed': total_failed,
                'total_skipped': total_skipped
            },
            'details': results,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📊 LOADING SUMMARY FOR {date}")
        print("=" * 40)
        print(f"✅ Total Loaded: {total_loaded}")
        print(f"⏭️  Total Skipped: {total_skipped}")
        print(f"❌ Total Failed: {total_failed}")
        
        for perspective, data in results.items():
            if data['loaded'] > 0 or data['failed'] > 0:
                print(f"\n{perspective.replace('_', ' ').title()}:")
                print(f"   Loaded: {data['loaded']}, Failed: {data['failed']}")
        
        return report

def main():
    """Test the enhanced financial notion loader"""
    
    print("🚀 Enhanced Financial Notion Loader Test")
    print("=" * 60)
    
    loader = EnhancedFinancialNotionLoader()
    
    # Test connection
    if not loader.test_connection():
        print("❌ Cannot connect to Notion API")
        return
    
    print("✅ Notion connection successful")
    print("💡 Ready to load multi-perspective financial data with detailed fee breakdown")
    
    # Test with sample data structure
    sample_data = {
        'date': '2025-07-29',
        'sales_performance': {
            'orders': [],
            'summary': {'count': 0, 'gross_sales': 0, 'net_sales': 0}
        },
        'cash_flow': {
            'transactions': [],
            'summary': {'count': 0, 'total_processed': 0}
        }
    }
    
    print("\n🎯 To use this loader:")
    print("1. Extract data using EnhancedFinancialAnalyticsExtractor")
    print("2. Pass the result to loader.load_multi_perspective_data()")
    print("3. Get detailed fee breakdown and currency conversion tracking")

if __name__ == "__main__":
    main()
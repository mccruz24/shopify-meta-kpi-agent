#!/usr/bin/env python3
"""
Shopify Date Discrepancy Investigator
Investigates the $2,049 vs $674.45 discrepancy by analyzing:
1. Order creation dates vs payment processing dates
2. All transaction statuses (not just successful)
3. Multi-day payment scenarios
4. Cross-reference with Shopify sales reports
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from src.extractors.financial_analytics_extractor import FinancialAnalyticsExtractor
    EXTRACTORS_AVAILABLE = True
except ImportError:
    EXTRACTORS_AVAILABLE = False
    print("⚠️  Note: Running without actual extractors - will show analysis framework")

class ShopifyDateDiscrepancyInvestigator:
    """Investigate date-based discrepancies in Shopify financial data"""
    
    def __init__(self):
        if EXTRACTORS_AVAILABLE:
            self.extractor = FinancialAnalyticsExtractor()
        self.target_date = "2025-07-29"
        self.shopify_reported_sales = 2049.00
        
    def enhanced_order_extraction(self, target_date: str) -> Dict:
        """Extract orders with detailed date analysis"""
        
        print(f"🔍 INVESTIGATING ORDERS FOR {target_date}")
        print("=" * 60)
        
        if not EXTRACTORS_AVAILABLE:
            return self._mock_enhanced_extraction(target_date)
        
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            
            # Get multiple date ranges to understand cross-day scenarios
            results = {
                'target_date': target_date,
                'orders_by_creation_date': [],
                'orders_by_payment_date': [],
                'transactions_by_processing_date': [],
                'date_mismatches': [],
                'summary': {}
            }
            
            # Method 1: Orders created on target date (regardless of payment date)
            print("1️⃣ Extracting orders CREATED on July 29...")
            orders_created_today = self._get_orders_by_creation_date(date_obj)
            results['orders_by_creation_date'] = orders_created_today
            
            # Method 2: Transactions processed on target date (regardless of order date)
            print("2️⃣ Extracting transactions PROCESSED on July 29...")
            transactions_today = self._get_transactions_by_processing_date(date_obj)
            results['transactions_by_processing_date'] = transactions_today
            
            # Method 3: Cross-reference to find date mismatches
            print("3️⃣ Analyzing date discrepancies...")
            mismatches = self._analyze_date_mismatches(orders_created_today, transactions_today)
            results['date_mismatches'] = mismatches
            
            # Method 4: Summary analysis
            results['summary'] = self._create_summary_analysis(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            return self._mock_enhanced_extraction(target_date)
    
    def _get_orders_by_creation_date(self, date: datetime) -> List[Dict]:
        """Get all orders created on specific date, regardless of payment timing"""
        
        # Create date range for order creation
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Use timezone-aware dates
        local_tz = timezone(timedelta(hours=2))  # Adjust to your store timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)
        
        print(f"   📅 Order creation window: {start_date} to {end_date}")
        
        # Get orders created in this timeframe
        orders_data = self.extractor._make_request('orders.json', {
            'status': 'any',  # Include all statuses
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250,
            'fields': 'id,order_number,created_at,updated_at,total_price,financial_status,fulfillment_status'
        })
        
        if not orders_data or not orders_data.get('orders'):
            print("   ℹ️  No orders found for creation date range")
            return []
        
        orders = orders_data['orders']
        print(f"   ✅ Found {len(orders)} orders created on {date.strftime('%Y-%m-%d')}")
        
        # Enhance each order with transaction details
        enhanced_orders = []
        for order in orders:
            enhanced_order = self._enhance_order_with_transactions(order)
            enhanced_orders.append(enhanced_order)
        
        return enhanced_orders
    
    def _get_transactions_by_processing_date(self, date: datetime) -> List[Dict]:
        """Get all transactions processed on specific date, regardless of order creation"""
        
        # This is the current method your system uses
        transactions = self.extractor.extract_single_date(date)
        
        print(f"   💳 Found {len(transactions)} transactions processed on {date.strftime('%Y-%m-%d')}")
        
        # Add order creation date to each transaction for comparison
        enhanced_transactions = []
        for tx in transactions:
            enhanced_tx = tx.copy()
            
            # Try to get order creation date
            order_id = tx.get('order_reference', '')
            if order_id:
                order_data = self.extractor._make_request(f'orders/{order_id}.json')
                if order_data and 'order' in order_data:
                    order = order_data['order']
                    enhanced_tx['order_created_at'] = order.get('created_at', '')
                    enhanced_tx['order_total'] = float(order.get('total_price', 0))
                    enhanced_tx['order_financial_status'] = order.get('financial_status', 'unknown')
            
            enhanced_transactions.append(enhanced_tx)
        
        return enhanced_transactions
    
    def _enhance_order_with_transactions(self, order: Dict) -> Dict:
        """Add transaction details to order data"""
        
        order_id = order.get('id')
        enhanced_order = order.copy()
        enhanced_order['transactions'] = []
        enhanced_order['total_transaction_amount'] = 0
        enhanced_order['transaction_count'] = 0
        
        if order_id:
            # Get all transactions for this order
            transactions_data = self.extractor._make_request(f'orders/{order_id}/transactions.json')
            
            if transactions_data and transactions_data.get('transactions'):
                transactions = transactions_data['transactions']
                enhanced_order['transactions'] = transactions
                enhanced_order['transaction_count'] = len(transactions)
                
                # Calculate total transaction amount
                total_amount = 0
                for tx in transactions:
                    amount = float(tx.get('amount', 0))
                    tx_kind = tx.get('kind', '')
                    
                    if tx_kind in ['sale', 'capture']:
                        total_amount += amount
                    elif tx_kind == 'refund':
                        total_amount -= amount
                
                enhanced_order['total_transaction_amount'] = total_amount
        
        return enhanced_order
    
    def _analyze_date_mismatches(self, orders_created: List[Dict], transactions_processed: List[Dict]) -> List[Dict]:
        """Analyze discrepancies between order creation and transaction processing dates"""
        
        mismatches = []
        
        # Create lookup of transactions by order ID
        tx_by_order = {}
        for tx in transactions_processed:
            order_ref = tx.get('order_reference', '')
            if order_ref:
                if order_ref not in tx_by_order:
                    tx_by_order[order_ref] = []
                tx_by_order[order_ref].append(tx)
        
        # Check each order created on target date
        for order in orders_created:
            order_id = str(order.get('id', ''))
            order_created = order.get('created_at', '')
            order_total = float(order.get('total_price', 0))
            
            # Check if this order has transactions processed on target date
            transactions_today = tx_by_order.get(f"order_{order_id}", [])
            
            if not transactions_today:
                # Order created today but no transactions processed today
                mismatches.append({
                    'type': 'order_created_no_payment_today',
                    'order_id': order_id,
                    'order_number': order.get('order_number', ''),
                    'order_created': order_created,
                    'order_total': order_total,
                    'transactions_today': 0,
                    'explanation': 'Order created July 29 but not paid on July 29'
                })
            else:
                # Check if amounts match
                tx_total = sum(tx.get('gross_amount', 0) for tx in transactions_today)
                if abs(order_total - tx_total) > 0.01:
                    mismatches.append({
                        'type': 'amount_mismatch',
                        'order_id': order_id,
                        'order_number': order.get('order_number', ''),
                        'order_total': order_total,
                        'transaction_total': tx_total,
                        'difference': order_total - tx_total,
                        'explanation': 'Order total does not match transaction total'
                    })
        
        # Check transactions processed today for orders created on different days
        for tx in transactions_processed:
            order_created = tx.get('order_created_at', '')
            if order_created:
                created_date = datetime.fromisoformat(order_created.replace('Z', '+00:00')).date()
                target_date_obj = datetime.strptime(self.target_date, '%Y-%m-%d').date()
                
                if created_date != target_date_obj:
                    mismatches.append({
                        'type': 'payment_today_order_different_day',
                        'transaction_id': tx.get('transaction_id', ''),
                        'order_number': tx.get('order_number', ''),
                        'order_created': order_created,
                        'order_created_date': created_date.isoformat(),
                        'payment_amount': tx.get('gross_amount', 0),
                        'explanation': f'Payment processed July 29 but order created {created_date}'
                    })
        
        return mismatches
    
    def _create_summary_analysis(self, results: Dict) -> Dict:
        """Create comprehensive summary of the analysis"""
        
        orders_created = results['orders_by_creation_date']
        transactions_processed = results['transactions_by_processing_date']
        mismatches = results['date_mismatches']
        
        # Calculate totals
        orders_created_total = sum(float(order.get('total_price', 0)) for order in orders_created)
        transactions_processed_total = sum(tx.get('gross_amount', 0) for tx in transactions_processed)
        
        # Categorize mismatches
        mismatch_categories = {}
        for mismatch in mismatches:
            category = mismatch['type']
            if category not in mismatch_categories:
                mismatch_categories[category] = {'count': 0, 'total_amount': 0}
            
            mismatch_categories[category]['count'] += 1
            if 'order_total' in mismatch:
                mismatch_categories[category]['total_amount'] += mismatch['order_total']
            elif 'payment_amount' in mismatch:
                mismatch_categories[category]['total_amount'] += mismatch['payment_amount']
        
        return {
            'target_date': self.target_date,
            'shopify_reported_sales': self.shopify_reported_sales,
            'orders_created_count': len(orders_created),
            'orders_created_total': round(orders_created_total, 2),
            'transactions_processed_count': len(transactions_processed),
            'transactions_processed_total': round(transactions_processed_total, 2),
            'primary_discrepancy': round(self.shopify_reported_sales - transactions_processed_total, 2),
            'order_vs_transaction_discrepancy': round(orders_created_total - transactions_processed_total, 2),
            'mismatch_categories': mismatch_categories,
            'potential_explanation': self._determine_likely_explanation(orders_created_total, transactions_processed_total)
        }
    
    def _determine_likely_explanation(self, orders_total: float, transactions_total: float) -> str:
        """Determine the most likely explanation for the discrepancy"""
        
        if abs(orders_total - self.shopify_reported_sales) < 10:
            return "Shopify sales report likely based on order creation date, not payment processing date"
        elif abs(transactions_total - self.shopify_reported_sales) < 10:
            return "Shopify sales report matches transaction processing - no discrepancy"
        elif orders_total > self.shopify_reported_sales > transactions_total:
            return "Shopify report includes some but not all orders - possibly filtering by payment status"
        else:
            return "Complex discrepancy requiring detailed investigation of individual transactions"
    
    def _mock_enhanced_extraction(self, target_date: str) -> Dict:
        """Provide mock data when extractors aren't available"""
        
        print("🔧 Running in SIMULATION MODE (no API access)")
        print("   This shows the analysis framework you'll get with real data")
        
        # Mock realistic data that could explain the discrepancy
        mock_orders_created = [
            {'id': '1001', 'order_number': '1001', 'created_at': f'{target_date}T10:30:00Z', 'total_price': '299.99', 'financial_status': 'pending'},
            {'id': '1002', 'order_number': '1002', 'created_at': f'{target_date}T11:45:00Z', 'total_price': '125.50', 'financial_status': 'paid'},
            {'id': '1003', 'order_number': '1003', 'created_at': f'{target_date}T14:20:00Z', 'total_price': '456.75', 'financial_status': 'authorized'},
            {'id': '1004', 'order_number': '1004', 'created_at': f'{target_date}T16:15:00Z', 'total_price': '89.99', 'financial_status': 'paid'},
            {'id': '1005', 'order_number': '1005', 'created_at': f'{target_date}T18:30:00Z', 'total_price': '234.50', 'financial_status': 'pending'},
            {'id': '1006', 'order_number': '1006', 'created_at': f'{target_date}T20:45:00Z', 'total_price': '678.90', 'financial_status': 'paid'},
            {'id': '1007', 'order_number': '1007', 'created_at': f'{target_date}T22:10:00Z', 'total_price': '163.37', 'financial_status': 'authorized'},
        ]
        
        mock_transactions_processed = [
            {'transaction_id': 'tx_001', 'order_reference': 'order_999', 'gross_amount': 145.75, 'order_created_at': '2025-07-28T23:45:00Z'},
            {'transaction_id': 'tx_002', 'order_reference': 'order_1002', 'gross_amount': 125.50, 'order_created_at': f'{target_date}T11:45:00Z'},
            {'transaction_id': 'tx_003', 'order_reference': 'order_998', 'gross_amount': 234.99, 'order_created_at': '2025-07-28T22:30:00Z'},
            {'transaction_id': 'tx_004', 'order_reference': 'order_1004', 'gross_amount': 89.99, 'order_created_at': f'{target_date}T16:15:00Z'},
            {'transaction_id': 'tx_005', 'order_reference': 'order_997', 'gross_amount': 78.22, 'order_created_at': '2025-07-28T21:15:00Z'},
        ]
        
        mock_mismatches = [
            {
                'type': 'order_created_no_payment_today',
                'order_number': '1001',
                'order_total': 299.99,
                'explanation': 'Order created July 29 but payment pending'
            },
            {
                'type': 'order_created_no_payment_today',
                'order_number': '1003',
                'order_total': 456.75,
                'explanation': 'Order created July 29 but only authorized, not captured'
            },
            {
                'type': 'payment_today_order_different_day',
                'order_number': '999',
                'payment_amount': 145.75,
                'explanation': 'Payment processed July 29 but order created July 28'
            }
        ]
        
        orders_total = sum(float(order['total_price']) for order in mock_orders_created)
        transactions_total = sum(tx['gross_amount'] for tx in mock_transactions_processed)
        
        return {
            'target_date': target_date,
            'orders_by_creation_date': mock_orders_created,
            'transactions_by_processing_date': mock_transactions_processed,
            'date_mismatches': mock_mismatches,
            'summary': {
                'target_date': target_date,
                'shopify_reported_sales': 2049.00,
                'orders_created_count': len(mock_orders_created),
                'orders_created_total': round(orders_total, 2),
                'transactions_processed_count': len(mock_transactions_processed),
                'transactions_processed_total': round(transactions_total, 2),
                'primary_discrepancy': round(2049.00 - transactions_total, 2),
                'order_vs_transaction_discrepancy': round(orders_total - transactions_total, 2),
                'potential_explanation': 'Shopify includes orders created on July 29 regardless of payment status'
            }
        }
    
    def print_detailed_analysis(self, results: Dict):
        """Print comprehensive analysis of the investigation"""
        
        summary = results['summary']
        
        print(f"\n📊 DETAILED ANALYSIS RESULTS")
        print("=" * 60)
        
        print(f"📅 Target Date: {summary['target_date']}")
        print(f"💰 Shopify Reported Sales: ${summary['shopify_reported_sales']:,.2f}")
        print()
        
        print("🛍️  ORDERS CREATED ON JULY 29:")
        print(f"   Count: {summary['orders_created_count']} orders")
        print(f"   Total: ${summary['orders_created_total']:,.2f}")
        print()
        
        print("💳 TRANSACTIONS PROCESSED ON JULY 29:")
        print(f"   Count: {summary['transactions_processed_count']} transactions")
        print(f"   Total: ${summary['transactions_processed_total']:,.2f}")
        print()
        
        print("🔍 DISCREPANCY ANALYSIS:")
        print(f"   Shopify vs Transactions: ${summary['primary_discrepancy']:,.2f}")
        print(f"   Orders vs Transactions: ${summary['order_vs_transaction_discrepancy']:,.2f}")
        print()
        
        print("💡 LIKELY EXPLANATION:")
        print(f"   {summary.get('potential_explanation', 'Requires further investigation')}")
        
        # Show date mismatches
        if results['date_mismatches']:
            print(f"\n⚠️  DATE MISMATCHES FOUND ({len(results['date_mismatches'])} items):")
            for i, mismatch in enumerate(results['date_mismatches'][:5], 1):  # Show first 5
                print(f"   {i}. {mismatch['explanation']}")
                if 'order_total' in mismatch:
                    print(f"      Amount: ${mismatch['order_total']:,.2f}")
                elif 'payment_amount' in mismatch:
                    print(f"      Amount: ${mismatch['payment_amount']:,.2f}")
            
            if len(results['date_mismatches']) > 5:
                print(f"   ... and {len(results['date_mismatches']) - 5} more mismatches")
    
    def generate_reconciliation_report(self, results: Dict) -> str:
        """Generate a comprehensive reconciliation report"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"shopify_discrepancy_investigation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return filename

def main():
    """Run the Shopify date discrepancy investigation"""
    
    print("🕵️ SHOPIFY DATE DISCREPANCY INVESTIGATOR")
    print("Solving the Mystery: $2,049 vs $674.45")
    print("=" * 60)
    
    investigator = ShopifyDateDiscrepancyInvestigator()
    
    # Run the investigation
    results = investigator.enhanced_order_extraction("2025-07-29")
    
    # Print detailed analysis
    investigator.print_detailed_analysis(results)
    
    # Generate report
    report_file = investigator.generate_reconciliation_report(results)
    
    print(f"\n📄 INVESTIGATION REPORT")
    print("=" * 40)
    print(f"Detailed report saved to: {report_file}")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Review the date mismatches identified above")
    print("2. Check if Shopify report includes pending/authorized orders")
    print("3. Verify timezone settings between systems")
    print("4. Update your extraction logic to handle all scenarios")
    print("5. Set up daily monitoring to catch future discrepancies")
    
    if EXTRACTORS_AVAILABLE:
        print("\n🚀 Run this script with your API credentials to get real data!")
    else:
        print("\n⚠️  Set up your API credentials to run with real Shopify data")

if __name__ == "__main__":
    main()
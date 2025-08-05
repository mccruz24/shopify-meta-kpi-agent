#!/usr/bin/env python3
"""
Financial Reconciliation Script
Automated reconciliation and validation of financial data across multiple sources
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.financial_analytics_extractor import FinancialAnalyticsExtractor
from src.loaders.financial_notion_loader import FinancialNotionLoader

class FinancialReconciliationEngine:
    """Comprehensive financial reconciliation engine"""
    
    def __init__(self):
        self.extractor = FinancialAnalyticsExtractor()
        self.loader = FinancialNotionLoader()
        self.reconciliation_results = {}
    
    def get_transactions_summary(self, date: datetime) -> Dict:
        """Get summary of transactions for a specific date"""
        transactions = self.extractor.extract_single_date(date)
        
        if not transactions:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_transactions': 0,
                'gross_revenue': 0,
                'processing_fees': 0,
                'net_revenue': 0,
                'sales_count': 0,
                'refunds_count': 0,
                'by_gateway': {},
                'by_payment_method': {},
                'transactions': []
            }
        
        # Calculate summaries
        total_gross = sum(tx.get('gross_amount', 0) for tx in transactions)
        total_fees = sum(tx.get('processing_fee', 0) for tx in transactions)
        sales_count = sum(1 for tx in transactions if tx.get('transaction_type') == 'sale')
        refunds_count = sum(1 for tx in transactions if tx.get('transaction_type') == 'refund')
        
        # Group by gateway
        by_gateway = {}
        for tx in transactions:
            gateway = tx.get('payment_gateway', 'unknown')
            if gateway not in by_gateway:
                by_gateway[gateway] = {'count': 0, 'amount': 0, 'fees': 0}
            by_gateway[gateway]['count'] += 1
            by_gateway[gateway]['amount'] += tx.get('gross_amount', 0)
            by_gateway[gateway]['fees'] += tx.get('processing_fee', 0)
        
        # Group by payment method
        by_payment_method = {}
        for tx in transactions:
            method = tx.get('payment_method', 'unknown')
            if method not in by_payment_method:
                by_payment_method[method] = {'count': 0, 'amount': 0}
            by_payment_method[method]['count'] += 1
            by_payment_method[method]['amount'] += tx.get('gross_amount', 0)
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'total_transactions': len(transactions),
            'gross_revenue': round(total_gross, 2),
            'processing_fees': round(total_fees, 2),
            'net_revenue': round(total_gross - total_fees, 2),
            'sales_count': sales_count,
            'refunds_count': refunds_count,
            'by_gateway': by_gateway,
            'by_payment_method': by_payment_method,
            'transactions': transactions
        }
    
    def validate_processing_fees(self, transactions: List[Dict]) -> List[Dict]:
        """Validate processing fee calculations"""
        discrepancies = []
        
        for tx in transactions:
            # Recalculate fee
            gross_amount = tx.get('gross_amount', 0)
            payment_method = tx.get('payment_method', 'credit_card')
            gateway = tx.get('payment_gateway', 'shopify_payments')
            
            expected_fee = self.extractor._calculate_processing_fee(gross_amount, payment_method, gateway)
            actual_fee = tx.get('processing_fee', 0)
            
            variance = abs(expected_fee - actual_fee)
            if variance > 0.01:  # Variance threshold
                discrepancies.append({
                    'transaction_id': tx.get('transaction_id'),
                    'order_number': tx.get('order_number'),
                    'gross_amount': gross_amount,
                    'expected_fee': round(expected_fee, 2),
                    'actual_fee': round(actual_fee, 2),
                    'variance': round(variance, 2),
                    'payment_method': payment_method,
                    'gateway': gateway
                })
        
        return discrepancies
    
    def detect_duplicate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Detect potential duplicate transactions"""
        duplicates = []
        seen_combinations = {}
        
        for tx in transactions:
            # Create unique key based on order, amount, and time
            key = f"{tx.get('order_reference')}_{tx.get('gross_amount')}_{tx.get('transaction_type')}"
            
            if key in seen_combinations:
                duplicates.append({
                    'transaction_1': seen_combinations[key],
                    'transaction_2': tx,
                    'match_criteria': key
                })
            else:
                seen_combinations[key] = tx
        
        return duplicates
    
    def analyze_transaction_patterns(self, transactions: List[Dict]) -> Dict:
        """Analyze transaction patterns for anomalies"""
        if not transactions:
            return {}
        
        amounts = [tx.get('gross_amount', 0) for tx in transactions]
        
        # Calculate statistics
        total_amount = sum(amounts)
        avg_amount = total_amount / len(amounts) if amounts else 0
        max_amount = max(amounts) if amounts else 0
        min_amount = min(amounts) if amounts else 0
        
        # Identify high-value transactions (> 3 standard deviations from mean)
        if len(amounts) > 1:
            import statistics
            std_dev = statistics.stdev(amounts)
            threshold = avg_amount + (3 * std_dev)
            high_value_transactions = [tx for tx in transactions if tx.get('gross_amount', 0) > threshold]
        else:
            high_value_transactions = []
        
        # Identify failed/pending transactions
        failed_transactions = [tx for tx in transactions if tx.get('status') != 'success']
        
        # Identify high-risk transactions
        high_risk_transactions = [tx for tx in transactions if tx.get('risk_level') == 'high']
        
        return {
            'total_transactions': len(transactions),
            'total_amount': round(total_amount, 2),
            'average_amount': round(avg_amount, 2),
            'max_amount': round(max_amount, 2),
            'min_amount': round(min_amount, 2),
            'high_value_count': len(high_value_transactions),
            'failed_count': len(failed_transactions),
            'high_risk_count': len(high_risk_transactions),
            'high_value_transactions': high_value_transactions[:5],  # Show first 5
            'failed_transactions': failed_transactions,
            'high_risk_transactions': high_risk_transactions
        }
    
    def reconcile_date(self, date: datetime) -> Dict:
        """Perform comprehensive reconciliation for a specific date"""
        print(f"🔍 Starting reconciliation for {date.strftime('%Y-%m-%d')}")
        
        # Get transaction summary
        summary = self.get_transactions_summary(date)
        transactions = summary['transactions']
        
        if not transactions:
            print(f"ℹ️  No transactions found for {date.strftime('%Y-%m-%d')}")
            return {'date': date.strftime('%Y-%m-%d'), 'status': 'no_data'}
        
        print(f"📊 Processing {len(transactions)} transactions")
        
        # Validation checks
        fee_discrepancies = self.validate_processing_fees(transactions)
        duplicates = self.detect_duplicate_transactions(transactions)
        patterns = self.analyze_transaction_patterns(transactions)
        
        # Create reconciliation report
        reconciliation_report = {
            'date': date.strftime('%Y-%m-%d'),
            'summary': summary,
            'validations': {
                'fee_discrepancies': {
                    'count': len(fee_discrepancies),
                    'total_variance': round(sum(d['variance'] for d in fee_discrepancies), 2),
                    'details': fee_discrepancies
                },
                'duplicates': {
                    'count': len(duplicates),
                    'details': duplicates
                },
                'patterns': patterns
            },
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
        
        # Determine overall status
        if fee_discrepancies or duplicates or patterns.get('failed_count', 0) > 0:
            reconciliation_report['status'] = 'discrepancies_found'
        
        # Print summary
        print(f"\n📋 Reconciliation Summary for {date.strftime('%Y-%m-%d')}:")
        print(f"   💰 Total Revenue: ${summary['gross_revenue']:.2f}")
        print(f"   💳 Processing Fees: ${summary['processing_fees']:.2f}")
        print(f"   📈 Net Revenue: ${summary['net_revenue']:.2f}")
        print(f"   📊 Transactions: {summary['sales_count']} sales, {summary['refunds_count']} refunds")
        
        if fee_discrepancies:
            print(f"   ⚠️  Fee Discrepancies: {len(fee_discrepancies)} (${sum(d['variance'] for d in fee_discrepancies):.2f} variance)")
        
        if duplicates:
            print(f"   ⚠️  Potential Duplicates: {len(duplicates)}")
        
        if patterns.get('failed_count', 0) > 0:
            print(f"   ⚠️  Failed Transactions: {patterns['failed_count']}")
        
        if patterns.get('high_risk_count', 0) > 0:
            print(f"   ⚠️  High Risk Transactions: {patterns['high_risk_count']}")
        
        return reconciliation_report
    
    def reconcile_date_range(self, start_date: datetime, end_date: datetime = None) -> Dict:
        """Reconcile multiple dates"""
        if end_date is None:
            end_date = start_date
        
        print(f"🔍 Starting reconciliation for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        current_date = start_date
        all_reports = []
        total_variance = 0
        total_discrepancies = 0
        
        while current_date <= end_date:
            report = self.reconcile_date(current_date)
            all_reports.append(report)
            
            if 'validations' in report:
                total_variance += report['validations']['fee_discrepancies']['total_variance']
                total_discrepancies += report['validations']['fee_discrepancies']['count']
            
            current_date += timedelta(days=1)
        
        # Summary report
        summary_report = {
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'total_days': len(all_reports),
            'total_fee_variance': round(total_variance, 2),
            'total_discrepancies': total_discrepancies,
            'daily_reports': all_reports,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n🎉 Reconciliation completed for {len(all_reports)} days")
        print(f"   💰 Total Fee Variance: ${total_variance:.2f}")
        print(f"   ⚠️  Total Discrepancies: {total_discrepancies}")
        
        return summary_report
    
    def export_reconciliation_report(self, report: Dict, filename: str = None) -> str:
        """Export reconciliation report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reconciliation_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Reconciliation report exported to: {filename}")
        return filename

def main():
    """Main function"""
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        print("💡 This script needs access to your Notion database for validation")
        # Continue without Notion for basic reconciliation
    
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        print("💡 Set SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN to run reconciliation")
        sys.exit(1)
    
    reconciler = FinancialReconciliationEngine()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                report = reconciler.reconcile_date(target_date)
                reconciler.export_reconciliation_report(report)
                
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        elif command == 'range':
            if len(sys.argv) < 4:
                print("❌ Date range requires start and end dates")
                print("💡 Usage: python financial_reconciliation.py range 2025-01-01 2025-01-07")
                sys.exit(1)
            
            try:
                start_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
                end_date = datetime.strptime(sys.argv[3], '%Y-%m-%d')
                report = reconciler.reconcile_date_range(start_date, end_date)
                reconciler.export_reconciliation_report(report)
                
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        elif command == 'last7':
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=6)
            report = reconciler.reconcile_date_range(start_date, end_date)
            reconciler.export_reconciliation_report(report)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python financial_reconciliation.py 2025-01-15              # Single date")
            print("   python financial_reconciliation.py range 2025-01-01 2025-01-07  # Date range")
            print("   python financial_reconciliation.py last7                   # Last 7 days")
            sys.exit(1)
    
    else:
        # Default: reconcile yesterday
        yesterday = datetime.now() - timedelta(days=1)
        report = reconciler.reconcile_date(yesterday)
        reconciler.export_reconciliation_report(report)

if __name__ == "__main__":
    main()
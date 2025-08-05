#!/usr/bin/env python3
"""
Enhanced Financial Analytics System
Complete system providing multi-perspective financial analytics with:
1. Sales Performance (order creation date based)
2. Cash Flow (payment processing date based)
3. Settlement Analytics (payout date with detailed fees)
4. Currency Conversion tracking
5. Detailed fee breakdown per transaction
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from enhanced_financial_analytics_extractor import EnhancedFinancialAnalyticsExtractor
from enhanced_financial_notion_loader import EnhancedFinancialNotionLoader

class EnhancedFinancialAnalyticsSystem:
    """Complete enhanced financial analytics system"""
    
    def __init__(self):
        self.extractor = EnhancedFinancialAnalyticsExtractor()
        self.loader = EnhancedFinancialNotionLoader()
    
    def extract_and_load_comprehensive_data(self, date: datetime = None) -> Dict:
        """Extract and load comprehensive financial data for a date"""
        
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        print(f"🚀 Enhanced Financial Analytics System")
        print(f"Processing comprehensive financial data for {date_str}")
        print("=" * 60)
        
        try:
            # Extract multi-perspective financial data
            print("1️⃣ EXTRACTING MULTI-PERSPECTIVE FINANCIAL DATA")
            financial_data = self.extractor.extract_multi_perspective_financial_data(date)
            
            if not financial_data:
                print("❌ No financial data extracted")
                return {'status': 'no_data', 'date': date_str}
            
            # Print analysis summary
            self._print_comprehensive_analysis(financial_data)
            
            # Load into Notion
            print("\n2️⃣ LOADING INTO NOTION WITH DETAILED BREAKDOWN")
            loading_results = self.loader.load_multi_perspective_data(financial_data)
            
            # Create final report
            report = self._create_comprehensive_report(financial_data, loading_results)
            
            # Export detailed report
            report_file = self._export_comprehensive_report(report, date_str)
            
            print(f"\n📄 Comprehensive report exported to: {report_file}")
            print("✅ Enhanced financial analytics processing completed!")
            
            return report
            
        except Exception as e:
            print(f"❌ Error in enhanced financial analytics: {e}")
            return {'status': 'error', 'date': date_str, 'error': str(e)}
    
    def _print_comprehensive_analysis(self, financial_data: Dict):
        """Print comprehensive analysis of the financial data"""
        
        date = financial_data['date']
        
        print(f"\n📊 COMPREHENSIVE FINANCIAL ANALYSIS FOR {date}")
        print("=" * 60)
        
        # Sales Performance Analysis
        sales = financial_data['sales_performance']['summary']
        print(f"📈 SALES PERFORMANCE (Orders Created {date}):")
        print(f"   Orders Created: {sales['count']}")
        print(f"   Gross Sales: €{sales['gross_sales']:,.2f}")
        print(f"   Net Sales: €{sales['net_sales']:,.2f}")
        print(f"   Total Discounts: €{sales['total_discounts']:,.2f}")
        print(f"   Total Shipping: €{sales['total_shipping']:,.2f}")
        
        # Cash Flow Analysis
        cash = financial_data['cash_flow']['summary']
        print(f"\n💰 CASH FLOW (Payments Processed {date}):")
        print(f"   Transactions Processed: {cash['count']}")
        print(f"   Total Cash Processed: €{cash['total_processed']:,.2f}")
        
        # Fee Breakdown Analysis
        fees = financial_data['fee_breakdown']
        print(f"\n💸 DETAILED FEE BREAKDOWN:")
        print(f"   Total Fees: €{fees['total_fees']:,.2f}")
        
        if fees['shopify_payment_fees']:
            total_shopify_fees = sum(fees['shopify_payment_fees'])
            total_conversion_fees = sum(fees['currency_conversion_fees'])
            total_transaction_fees = sum(fees['transaction_fees'])
            total_vat_fees = sum(fees['vat_on_fees'])
            
            print(f"   Shopify Payment Fees: €{total_shopify_fees:.2f}")
            print(f"   Currency Conversion Fees: €{total_conversion_fees:.2f}")
            print(f"   Transaction Fees: €{total_transaction_fees:.2f}")
            print(f"   VAT on Fees: €{total_vat_fees:.2f}")
        
        # Currency Conversion Analysis
        conversions = financial_data['currency_conversion']
        if conversions['usd_to_eur_transactions']:
            print(f"\n💱 CURRENCY CONVERSIONS:")
            print(f"   USD→EUR Transactions: {len(conversions['usd_to_eur_transactions'])}")
            print(f"   Total Converted: €{conversions['total_converted_amount']:,.2f}")
            print(f"   Conversion Fees: €{conversions['conversion_fees']:,.2f}")
        
        # Settlement Analysis
        settlements = financial_data['settlement_analytics']
        if 'estimated_payout' in settlements:
            print(f"\n🏦 ESTIMATED SETTLEMENT:")
            print(f"   Estimated Payout: €{settlements['estimated_payout']:,.2f}")
            print(f"   Estimated Fees: €{settlements['estimated_fees']:,.2f}")
        
        # Show the key insight about different perspectives
        print(f"\n🔍 PERSPECTIVE COMPARISON:")
        print(f"   Sales Performance (Order Creation): €{sales['gross_sales']:,.2f}")
        print(f"   Cash Flow (Payment Processing): €{cash['total_processed']:,.2f}")
        print(f"   Difference: €{cash['total_processed'] - sales['gross_sales']:,.2f}")
        
        if cash['total_processed'] > sales['gross_sales']:
            print(f"   → More payments processed than orders created (includes previous days' orders)")
        elif sales['gross_sales'] > cash['total_processed']:
            print(f"   → More orders created than payments processed (includes pending payments)")
        else:
            print(f"   → Perfect match between order creation and payment processing")
    
    def _create_comprehensive_report(self, financial_data: Dict, loading_results: Dict) -> Dict:
        """Create comprehensive report with all perspectives"""
        
        date = financial_data['date']
        
        # Calculate key metrics
        sales = financial_data['sales_performance']['summary']
        cash = financial_data['cash_flow']['summary']
        fees = financial_data['fee_breakdown']
        
        # Effective fee rate
        effective_fee_rate = 0
        if cash['total_processed'] > 0:
            effective_fee_rate = (fees['total_fees'] / cash['total_processed']) * 100
        
        # Net payout calculation
        net_payout = cash['total_processed'] - fees['total_fees']
        
        return {
            'date': date,
            'perspectives': {
                'sales_performance': {
                    'orders_created': sales['count'],
                    'gross_sales': sales['gross_sales'],
                    'net_sales': sales['net_sales'],
                    'discounts': sales['total_discounts'],
                    'shipping': sales['total_shipping']
                },
                'cash_flow': {
                    'transactions_processed': cash['count'],
                    'total_processed': cash['total_processed'],
                    'net_payout': round(net_payout, 2)
                },
                'fee_analysis': {
                    'total_fees': fees['total_fees'],
                    'effective_fee_rate': round(effective_fee_rate, 2),
                    'shopify_payment_fees': sum(fees.get('shopify_payment_fees', [])),
                    'currency_conversion_fees': sum(fees.get('currency_conversion_fees', [])),
                    'transaction_fees': sum(fees.get('transaction_fees', [])),
                    'vat_on_fees': sum(fees.get('vat_on_fees', []))
                }
            },
            'currency_conversions': financial_data['currency_conversion'],
            'settlement_analytics': financial_data['settlement_analytics'],
            'notion_loading': loading_results,
            'insights': {
                'perspective_difference': round(cash['total_processed'] - sales['gross_sales'], 2),
                'cash_vs_orders_ratio': round(cash['total_processed'] / sales['gross_sales'] if sales['gross_sales'] > 0 else 0, 2),
                'average_order_value': round(sales['gross_sales'] / sales['count'] if sales['count'] > 0 else 0, 2),
                'average_transaction_value': round(cash['total_processed'] / cash['count'] if cash['count'] > 0 else 0, 2)
            },
            'raw_data': financial_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def _export_comprehensive_report(self, report: Dict, date_str: str) -> str:
        """Export comprehensive report to JSON"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"enhanced_financial_report_{date_str}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filename
    
    def compare_with_shopify_report(self, date: datetime, shopify_reported_amount: float) -> Dict:
        """Compare enhanced analytics with Shopify's reported amount"""
        
        print(f"🔍 COMPARING WITH SHOPIFY REPORT")
        print("=" * 40)
        
        # Extract our data
        financial_data = self.extractor.extract_multi_perspective_financial_data(date)
        
        if not financial_data:
            return {'status': 'no_data'}
        
        sales = financial_data['sales_performance']['summary']
        cash = financial_data['cash_flow']['summary']
        
        # Calculate discrepancies
        sales_vs_shopify = sales['gross_sales'] - shopify_reported_amount
        cash_vs_shopify = cash['total_processed'] - shopify_reported_amount
        
        comparison = {
            'date': date.strftime('%Y-%m-%d'),
            'shopify_reported': shopify_reported_amount,
            'our_sales_performance': sales['gross_sales'],
            'our_cash_flow': cash['total_processed'],
            'discrepancies': {
                'sales_vs_shopify': round(sales_vs_shopify, 2),
                'cash_vs_shopify': round(cash_vs_shopify, 2)
            },
            'analysis': {
                'closest_match': 'sales_performance' if abs(sales_vs_shopify) < abs(cash_vs_shopify) else 'cash_flow',
                'explanation': self._explain_discrepancy(sales_vs_shopify, cash_vs_shopify, shopify_reported_amount)
            }
        }
        
        print(f"Shopify Reported: €{shopify_reported_amount:,.2f}")
        print(f"Our Sales Performance: €{sales['gross_sales']:,.2f} (difference: €{sales_vs_shopify:,.2f})")
        print(f"Our Cash Flow: €{cash['total_processed']:,.2f} (difference: €{cash_vs_shopify:,.2f})")
        print(f"\nClosest Match: {comparison['analysis']['closest_match']}")
        print(f"Explanation: {comparison['analysis']['explanation']}")
        
        return comparison
    
    def _explain_discrepancy(self, sales_diff: float, cash_diff: float, shopify_amount: float) -> str:
        """Explain the most likely cause of discrepancy"""
        
        if abs(sales_diff) < 10:
            return "Sales performance matches Shopify report - Shopify likely reports by order creation date"
        elif abs(cash_diff) < 10:
            return "Cash flow matches Shopify report - Shopify likely reports by payment processing date"
        elif sales_diff > 0 and cash_diff < 0:
            return "Orders created exceed Shopify report, but cash flow is less - mixed timing scenario"
        elif sales_diff < 0 and cash_diff > 0:
            return "Cash flow exceeds Shopify report, but fewer orders created - includes previous days' payments"
        else:
            return "Complex discrepancy requiring detailed investigation of individual transactions"
    
    def test_system(self) -> bool:
        """Test the enhanced financial analytics system"""
        
        print("🧪 Testing Enhanced Financial Analytics System")
        print("=" * 60)
        
        # Test extractor connection
        print("1️⃣ Testing Shopify connection...")
        if self.extractor.test_connection():
            print("   ✅ Shopify connection successful")
        else:
            print("   ❌ Shopify connection failed")
            return False
        
        # Test loader connection
        print("2️⃣ Testing Notion connection...")
        if self.loader.test_connection():
            print("   ✅ Notion connection successful")
        else:
            print("   ❌ Notion connection failed")
            return False
        
        # Test data extraction
        print("3️⃣ Testing data extraction...")
        test_date = datetime.now() - timedelta(days=1)
        try:
            financial_data = self.extractor.extract_multi_perspective_financial_data(test_date)
            if financial_data:
                print("   ✅ Data extraction successful")
                
                # Show sample of what would be captured
                sales = financial_data['sales_performance']['summary']
                cash = financial_data['cash_flow']['summary']
                
                print(f"   📊 Sample Results:")
                print(f"      Orders Created: {sales['count']}")
                print(f"      Payments Processed: {cash['count']}")
                print(f"      Sales Performance: €{sales['gross_sales']:,.2f}")
                print(f"      Cash Flow: €{cash['total_processed']:,.2f}")
            else:
                print("   ⚠️  No data extracted (normal if no recent transactions)")
        except Exception as e:
            print(f"   ❌ Data extraction failed: {e}")
            return False
        
        print("\n✅ Enhanced Financial Analytics System test completed successfully!")
        return True

def main():
    """Main function"""
    
    # Validate environment
    if not os.getenv('NOTION_TOKEN'):
        print("❌ NOTION_TOKEN not found in environment")
        sys.exit(1)
    
    if not os.getenv('SHOPIFY_SHOP_URL') or not os.getenv('SHOPIFY_ACCESS_TOKEN'):
        print("❌ Shopify credentials not found in environment")
        sys.exit(1)
    
    system = EnhancedFinancialAnalyticsSystem()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = system.test_system()
            sys.exit(0 if success else 1)
        
        elif command == 'compare':
            if len(sys.argv) < 4:
                print("❌ Compare requires date and Shopify amount")
                print("💡 Usage: python enhanced_financial_analytics_system.py compare 2025-07-29 2049.00")
                sys.exit(1)
            
            try:
                target_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
                shopify_amount = float(sys.argv[3])
                comparison = system.compare_with_shopify_report(target_date, shopify_amount)
                print(f"\n📊 Comparison completed!")
                
            except ValueError:
                print("❌ Invalid date format or amount")
                sys.exit(1)
        
        elif command.startswith('20'):  # Date format YYYY-MM-DD
            try:
                target_date = datetime.strptime(command, '%Y-%m-%d')
                report = system.extract_and_load_comprehensive_data(target_date)
                
                if report['status'] == 'error':
                    sys.exit(1)
                
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        
        else:
            print("❌ Invalid command")
            print("💡 Usage:")
            print("   python enhanced_financial_analytics_system.py                    # Yesterday's data")
            print("   python enhanced_financial_analytics_system.py test              # Test system")
            print("   python enhanced_financial_analytics_system.py 2025-07-29       # Specific date")
            print("   python enhanced_financial_analytics_system.py compare 2025-07-29 2049.00  # Compare with Shopify")
            sys.exit(1)
    
    else:
        # Default: process yesterday's data
        report = system.extract_and_load_comprehensive_data()
        if report.get('status') == 'error':
            sys.exit(1)

if __name__ == "__main__":
    main()
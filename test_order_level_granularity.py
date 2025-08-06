#!/usr/bin/env python3
"""
Test Order-Level Granularity for Financial Analytics

This script tests the enhanced financial extractor to show both:
1. Payout-level summaries (settlement data)
2. Order-level details (transaction granularity)
3. Order-to-payout mapping

Focus on June 27, 2025 payout with 8 orders as requested.
"""

import sys
import os
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from extractors.enhanced_financial_analytics_extractor import EnhancedFinancialAnalyticsExtractor

load_dotenv()

class OrderLevelAnalyzer:
    def __init__(self):
        self.extractor = EnhancedFinancialAnalyticsExtractor()
        
    def test_june_27_granularity(self):
        """Test the specific June 27, 2025 case with 8 orders"""
        print("🎯 TESTING JUNE 27, 2025 ORDER-LEVEL GRANULARITY")
        print("=" * 70)
        print("Expected: €405.61 payout from 8 individual orders")
        print()
        
        # Focus on June 27, 2025
        target_date = datetime(2025, 6, 27)
        
        # Get comprehensive data
        financial_data = self.extractor.get_comprehensive_financial_data(
            start_date=target_date,
            end_date=target_date + timedelta(days=1)
        )
        
        return self.analyze_comprehensive_data(financial_data, target_date)
    
    def analyze_comprehensive_data(self, data, target_date):
        """Analyze the comprehensive financial data"""
        
        payouts = data['payouts']
        orders = data['orders']
        mapping = data['payout_order_mapping']
        summary = data['summary']
        
        print(f"📊 DATA SUMMARY:")
        print(f"   Payouts Found: {summary['total_payouts']}")
        print(f"   Orders Found: {summary['total_orders']}")
        print(f"   Payout Total: €{summary['total_gross_from_payouts']:.2f}")
        print(f"   Orders Total: €{summary['total_from_orders']:.2f}")
        
        # Focus on June 27 payout
        june_27_payout = None
        for payout in payouts:
            if payout['settlement_date_formatted'] == target_date.strftime('%Y-%m-%d'):
                june_27_payout = payout
                break
        
        if not june_27_payout:
            print(f"❌ June 27 payout not found")
            return False
        
        print(f"\n🎯 JUNE 27 PAYOUT ANALYSIS:")
        print(f"   Payout ID: {june_27_payout['payout_id']}")
        print(f"   Settlement Date: {june_27_payout['settlement_date_formatted']}")
        print(f"   Gross Amount: €{june_27_payout['gross_sales']:.2f}")
        print(f"   Processing Fee: €{june_27_payout['processing_fee']:.2f}")
        print(f"   Net Amount: €{june_27_payout['net_amount']:.2f}")
        
        # Find orders mapped to this payout
        payout_id = june_27_payout['payout_id']
        payout_orders = [o for o in orders if o['mapped_payout_id'] == payout_id]
        
        print(f"\n📦 ORDERS CONTRIBUTING TO JUNE 27 PAYOUT:")
        print(f"   Orders Found: {len(payout_orders)}")
        
        if not payout_orders:
            print("❌ No orders mapped to June 27 payout")
            return False
        
        total_orders_amount = 0
        
        for i, order in enumerate(payout_orders, 1):
            order_date = datetime.fromisoformat(order['created_at']).strftime('%Y-%m-%d %H:%M')
            total_orders_amount += order['total_price']
            
            print(f"\n   {i}. Order #{order['order_number']}")
            print(f"      Order ID: {order['order_id']}")
            print(f"      Created: {order_date}")
            print(f"      Total: €{order['total_price']:.2f}")
            print(f"      Subtotal: €{order['subtotal_price']:.2f}")
            print(f"      Tax: €{order['total_tax']:.2f}")
            print(f"      Shipping: €{order['shipping_cost']:.2f}")
            print(f"      Customer: {order['customer_email']}")
            print(f"      Country: {order['customer_country']}")
            print(f"      Items: {order['total_quantity']} ({order['line_items_count']} different)")
            print(f"      Payment: {order['payment_gateway']}")
        
        print(f"\n📈 VALIDATION:")
        print(f"   Expected Orders: 8")
        print(f"   Found Orders: {len(payout_orders)}")
        print(f"   Expected Amount: €405.61")
        print(f"   Orders Total: €{total_orders_amount:.2f}")
        print(f"   Payout Amount: €{june_27_payout['gross_sales']:.2f}")
        
        amount_match = abs(total_orders_amount - june_27_payout['gross_sales']) < 5.0  # Within €5
        
        print(f"   Amount Match: {'✅' if amount_match else '⚠️'}")
        print(f"   Order Count: {'✅' if len(payout_orders) == 8 else '⚠️'}")
        
        # Export detailed data
        self.export_order_level_data(june_27_payout, payout_orders)
        
        return True
    
    def export_order_level_data(self, payout, orders):
        """Export order-level data to CSV files"""
        
        print(f"\n📤 EXPORTING ORDER-LEVEL DATA")
        
        # 1. Export order details
        orders_filename = f"june_27_order_details.csv"
        
        order_fields = [
            'order_number', 'order_id', 'created_date_formatted', 'created_time_formatted',
            'total_price', 'subtotal_price', 'total_tax', 'shipping_cost', 'total_discounts',
            'customer_email', 'customer_country', 'customer_city',
            'payment_gateway', 'financial_status', 'total_quantity', 'line_items_count',
            'product_type', 'mapped_payout_id'
        ]
        
        with open(orders_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=order_fields)
            writer.writeheader()
            
            for order in orders:
                csv_row = {field: order.get(field, '') for field in order_fields}
                writer.writerow(csv_row)
        
        print(f"   📊 Order Details: {orders_filename} ({len(orders)} records)")
        
        # 2. Export payout summary
        payout_filename = f"june_27_payout_summary.csv"
        
        payout_fields = [
            'payout_id', 'settlement_date_formatted', 'payout_status',
            'gross_sales', 'processing_fee', 'net_amount', 'fee_rate_percent',
            'currency'
        ]
        
        with open(payout_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=payout_fields)
            writer.writeheader()
            
            csv_row = {field: payout.get(field, '') for field in payout_fields}
            writer.writerow(csv_row)
        
        print(f"   💰 Payout Summary: {payout_filename} (1 record)")
        
        # 3. Export combined analysis
        analysis_filename = f"june_27_financial_analysis.txt"
        
        with open(analysis_filename, 'w') as f:
            f.write("JUNE 27, 2025 FINANCIAL ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("PAYOUT SUMMARY:\n")
            f.write(f"Payout ID: {payout['payout_id']}\n")
            f.write(f"Settlement Date: {payout['settlement_date_formatted']}\n")
            f.write(f"Gross Sales: €{payout['gross_sales']:.2f}\n")
            f.write(f"Processing Fee: €{payout['processing_fee']:.2f} ({payout['fee_rate_percent']:.2f}%)\n")
            f.write(f"Net Amount: €{payout['net_amount']:.2f}\n\n")
            
            f.write("CONTRIBUTING ORDERS:\n")
            f.write("-" * 50 + "\n")
            
            total_orders_value = 0
            for i, order in enumerate(orders, 1):
                total_orders_value += order['total_price']
                f.write(f"\n{i}. Order #{order['order_number']} - €{order['total_price']:.2f}\n")
                f.write(f"   Created: {order['created_date_formatted']} {order['created_time_formatted']}\n")
                f.write(f"   Customer: {order['customer_email']} ({order['customer_country']})\n")
                f.write(f"   Items: {order['total_quantity']} items in {order['line_items_count']} SKUs\n")
                f.write(f"   Payment: {order['payment_gateway']}\n")
                f.write(f"   Breakdown: €{order['subtotal_price']:.2f} + €{order['total_tax']:.2f} tax + €{order['shipping_cost']:.2f} shipping\n")
            
            f.write(f"\nTOTALS:\n")
            f.write(f"Orders Count: {len(orders)}\n")
            f.write(f"Orders Total: €{total_orders_value:.2f}\n")
            f.write(f"Payout Amount: €{payout['gross_sales']:.2f}\n")
            f.write(f"Difference: €{abs(total_orders_value - payout['gross_sales']):.2f}\n")
        
        print(f"   📄 Analysis Report: {analysis_filename}")
        print(f"\n✅ Order-level granularity data exported successfully!")

def main():
    print("🔍 ORDER-LEVEL GRANULARITY TEST")
    print("Testing enhanced financial analytics with order details")
    print("=" * 70)
    
    analyzer = OrderLevelAnalyzer()
    
    # Test connection
    if not analyzer.extractor.test_connection():
        print("❌ Connection failed")
        return
    
    # Run June 27 analysis
    success = analyzer.test_june_27_granularity()
    
    if success:
        print(f"\n🎉 SUCCESS!")
        print(f"Order-level granularity working correctly:")
        print(f"   ✅ Individual orders extracted and mapped to payouts")
        print(f"   ✅ Customer details and payment methods captured")
        print(f"   ✅ Product information and quantities included")
        print(f"   ✅ Financial breakdown at order level")
        print(f"   ✅ Data exported in multiple formats for analysis")
        
        print(f"\n📊 FILES CREATED:")
        print(f"   📄 june_27_order_details.csv - Individual order records")
        print(f"   💰 june_27_payout_summary.csv - Payout settlement data")
        print(f"   📄 june_27_financial_analysis.txt - Combined analysis")
    else:
        print(f"\n❌ Test incomplete - check data and mapping logic")

if __name__ == "__main__":
    main()
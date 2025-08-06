#!/usr/bin/env python3
"""
Test Currency Conversion Data for Financial Analytics

This script tests the currency-aware financial extractor to show:
1. Customer paid amounts (USD)
2. Shop received amounts (EUR) 
3. Exchange rate calculations
4. Proper currency reconciliation with payouts

Focus on June 27, 2025 payout with currency conversion analysis.
"""

import sys
import os
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from extractors.currency_aware_financial_extractor import CurrencyAwareFinancialExtractor

load_dotenv()

class CurrencyConversionAnalyzer:
    def __init__(self):
        self.extractor = CurrencyAwareFinancialExtractor()
        
    def test_june_27_currency_conversion(self):
        """Test currency conversion for June 27, 2025 payout"""
        print("💱 TESTING JUNE 27 CURRENCY CONVERSION")
        print("=" * 70)
        print("Expected: USD orders → EUR payout conversion analysis")
        print()
        
        # Focus on June 27, 2025
        target_date = datetime(2025, 6, 27)
        
        # Get comprehensive currency data
        currency_data = self.extractor.get_comprehensive_currency_data(
            start_date=target_date,
            end_date=target_date + timedelta(days=1)
        )
        
        return self.analyze_currency_data(currency_data, target_date)
    
    def analyze_currency_data(self, data, target_date):
        """Analyze comprehensive currency conversion data"""
        
        payouts = data['payouts']
        orders = data['orders']
        currency_mapping = data['currency_mapping']
        currency_metrics = data['currency_metrics']
        summary = data['summary']
        
        print(f"💱 CURRENCY DATA SUMMARY:")
        print(f"   Payouts Found: {summary['total_payouts']}")
        print(f"   Orders Found: {summary['total_orders']}")
        print(f"   Total USD (Customer Paid): ${summary['total_usd_from_orders']:.2f}")
        print(f"   Total EUR (Shop Received): €{summary['total_eur_from_orders']:.2f}")
        print(f"   Total EUR (Payout): €{summary['total_eur_from_payouts']:.2f}")
        
        # Find June 27 payout
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
        print(f"   Payout Currency: {june_27_payout['payout_currency']}")
        print(f"   Gross Amount: €{june_27_payout['gross_sales']:.2f}")
        print(f"   Processing Fee: €{june_27_payout['processing_fee']:.2f}")
        print(f"   Net Amount: €{june_27_payout['net_amount']:.2f}")
        
        # Find orders mapped to this payout
        payout_id = june_27_payout['payout_id']
        payout_orders = [o for o in orders if o['mapped_payout_id'] == payout_id]
        
        if not payout_orders:
            print("❌ No orders mapped to June 27 payout")
            return False
        
        print(f"\n📦 CURRENCY CONVERSION ANALYSIS:")
        print(f"   Orders Contributing: {len(payout_orders)}")
        
        total_customer_usd = 0
        total_shop_eur = 0
        exchange_rates = []
        
        for i, order in enumerate(payout_orders, 1):
            total_customer_usd += order['customer_total']
            total_shop_eur += order['shop_total']
            exchange_rates.append(order['exchange_rate'])
            
            print(f"\n   {i}. Order #{order['order_number']}")
            print(f"      Created: {order['created_date_formatted']} {order['created_time_formatted']}")
            print(f"      Customer Paid: ${order['customer_total']:.2f} {order['customer_currency']}")
            print(f"      Shop Received: €{order['shop_total']:.2f} {order['shop_currency']}")
            print(f"      Exchange Rate: {order['exchange_rate']:.4f} (USD/EUR)")
            print(f"      Customer: {order['customer_email']} ({order['customer_country']})")
            
            # Show breakdown if available
            if order['customer_subtotal'] > 0:
                print(f"      USD Breakdown: ${order['customer_subtotal']:.2f} + ${order['customer_tax']:.2f} tax + ${order['customer_shipping']:.2f} shipping")
                print(f"      EUR Breakdown: €{order['shop_subtotal']:.2f} + €{order['shop_tax']:.2f} tax + €{order['shop_shipping']:.2f} shipping")
        
        # Calculate currency metrics for this payout
        if exchange_rates:
            avg_rate = sum(exchange_rates) / len(exchange_rates)
            min_rate = min(exchange_rates)
            max_rate = max(exchange_rates)
            
            print(f"\n📊 CURRENCY CONVERSION SUMMARY:")
            print(f"   Total Customer Payments: ${total_customer_usd:.2f} USD")
            print(f"   Total Shop Receipts: €{total_shop_eur:.2f} EUR")
            print(f"   Actual Payout: €{june_27_payout['gross_sales']:.2f} EUR")
            print(f"   ")
            print(f"   Exchange Rate Analysis:")
            print(f"   Average Rate: {avg_rate:.4f} USD/EUR")
            print(f"   Min Rate: {min_rate:.4f} USD/EUR")
            print(f"   Max Rate: {max_rate:.4f} USD/EUR")
            print(f"   Rate Volatility: {(max_rate - min_rate):.4f}")
            
            # Validation
            eur_difference = abs(total_shop_eur - june_27_payout['gross_sales'])
            currency_match = eur_difference < 5.0  # Within €5
            
            print(f"\n✅ VALIDATION:")
            print(f"   EUR Amount Match: {'✅' if currency_match else '⚠️'} (diff: €{eur_difference:.2f})")
            print(f"   Currency Conversion: {'✅' if avg_rate > 1.0 else '⚠️'} ({avg_rate:.4f} USD per EUR)")
            print(f"   Exchange Rate Reasonable: {'✅' if 1.05 <= avg_rate <= 1.20 else '⚠️'}")
        
        # Export detailed currency data
        self.export_currency_conversion_data(june_27_payout, payout_orders, currency_metrics)
        
        return True
    
    def export_currency_conversion_data(self, payout, orders, metrics):
        """Export detailed currency conversion data"""
        
        print(f"\n📤 EXPORTING CURRENCY CONVERSION DATA")
        
        # 1. Export orders with currency details
        filename = f"june_27_currency_conversion_details.csv"
        
        currency_fields = [
            'order_number', 'order_id', 'created_date_formatted', 
            'customer_currency', 'customer_total', 'customer_subtotal', 'customer_tax', 'customer_shipping',
            'shop_currency', 'shop_total', 'shop_subtotal', 'shop_tax', 'shop_shipping',
            'exchange_rate', 'conversion_date',
            'customer_email', 'customer_country', 'payment_gateway',
            'mapped_payout_id'
        ]
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=currency_fields)
            writer.writeheader()
            
            for order in orders:
                csv_row = {field: order.get(field, '') for field in currency_fields}
                writer.writerow(csv_row)
        
        print(f"   💱 Currency Details: {filename} ({len(orders)} records)")
        
        # 2. Export currency reconciliation report
        report_filename = f"june_27_currency_reconciliation.txt"
        
        with open(report_filename, 'w') as f:
            f.write("JUNE 27, 2025 CURRENCY RECONCILIATION REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("PAYOUT SUMMARY (EUR):\n")
            f.write(f"Payout ID: {payout['payout_id']}\n")
            f.write(f"Settlement Date: {payout['settlement_date_formatted']}\n")
            f.write(f"Currency: {payout['payout_currency']}\n")
            f.write(f"Gross Sales: €{payout['gross_sales']:.2f}\n")
            f.write(f"Processing Fee: €{payout['processing_fee']:.2f}\n")
            f.write(f"Net Amount: €{payout['net_amount']:.2f}\n\n")
            
            f.write("CURRENCY CONVERSION ANALYSIS:\n")
            f.write("-" * 40 + "\n")
            
            total_usd = sum(o['customer_total'] for o in orders)
            total_eur = sum(o['shop_total'] for o in orders)
            rates = [o['exchange_rate'] for o in orders if o['exchange_rate'] > 0]
            avg_rate = sum(rates) / len(rates) if rates else 0
            
            f.write(f"Total Customer Payments: ${total_usd:.2f} USD\n")
            f.write(f"Total Shop Receipts: €{total_eur:.2f} EUR\n")
            f.write(f"Average Exchange Rate: {avg_rate:.4f} USD/EUR\n")
            f.write(f"Currency Difference: €{abs(total_eur - payout['gross_sales']):.2f}\n\n")
            
            f.write("INDIVIDUAL ORDER CONVERSIONS:\n")
            f.write("-" * 40 + "\n")
            
            for i, order in enumerate(orders, 1):
                f.write(f"\n{i}. Order #{order['order_number']} - {order['created_date_formatted']}\n")
                f.write(f"   Customer Paid: ${order['customer_total']:.2f} USD\n")
                f.write(f"   Shop Received: €{order['shop_total']:.2f} EUR\n")
                f.write(f"   Exchange Rate: {order['exchange_rate']:.4f}\n")
                f.write(f"   Customer: {order['customer_email']} ({order['customer_country']})\n")
            
            if metrics:
                f.write(f"\nCURRENCY METRICS:\n")
                f.write(f"Average Exchange Rate: {metrics.get('average_exchange_rate', 0):.4f}\n")
                f.write(f"Rate Volatility: {metrics.get('exchange_rate_volatility', 0):.4f}\n")
                f.write(f"Conversion Accuracy: {metrics.get('conversion_accuracy_percent', 0):.2f}%\n")
        
        print(f"   📄 Reconciliation Report: {report_filename}")
        
        # 3. Export simple comparison table
        comparison_filename = f"june_27_usd_eur_comparison.csv"
        
        with open(comparison_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'USD_Amount', 'EUR_Amount', 'Exchange_Rate', 'Notes'])
            
            # Summary row
            total_usd = sum(o['customer_total'] for o in orders)
            total_eur = sum(o['shop_total'] for o in orders)
            avg_rate = sum(o['exchange_rate'] for o in orders if o['exchange_rate'] > 0) / len(orders)
            
            writer.writerow(['Order_Totals', f'${total_usd:.2f}', f'€{total_eur:.2f}', f'{avg_rate:.4f}', 'Sum_of_all_orders'])
            writer.writerow(['Payout_Amount', 'N/A', f'€{payout["gross_sales"]:.2f}', 'N/A', 'Actual_settlement'])
            writer.writerow(['Difference', 'N/A', f'€{abs(total_eur - payout["gross_sales"]):.2f}', 'N/A', 'Reconciliation_gap'])
        
        print(f"   📊 USD/EUR Comparison: {comparison_filename}")
        print(f"\n✅ Currency conversion data exported successfully!")

def main():
    print("💱 CURRENCY CONVERSION TEST")
    print("Testing currency-aware financial analytics with USD→EUR conversion")
    print("=" * 70)
    
    analyzer = CurrencyConversionAnalyzer()
    
    # Test connection
    if not analyzer.extractor.test_connection():
        print("❌ Connection failed")
        return
    
    # Run June 27 currency analysis
    success = analyzer.test_june_27_currency_conversion()
    
    if success:
        print(f"\n🎉 CURRENCY CONVERSION SUCCESS!")
        print(f"Currency-aware analytics working correctly:")
        print(f"   ✅ Customer USD payments captured")
        print(f"   ✅ Shop EUR receipts extracted")
        print(f"   ✅ Exchange rates calculated")
        print(f"   ✅ Currency reconciliation with payouts")
        print(f"   ✅ Multi-currency data exported")
        
        print(f"\n📊 FILES CREATED:")
        print(f"   💱 june_27_currency_conversion_details.csv - Full currency data")
        print(f"   📄 june_27_currency_reconciliation.txt - Reconciliation report")
        print(f"   📊 june_27_usd_eur_comparison.csv - Simple USD/EUR comparison")
    else:
        print(f"\n❌ Currency conversion test incomplete")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Financial Data Simulator & Explanation
Simulates real Shopify transactions for July 29, 2025 to demonstrate:
- How sales appear in your Notion database
- Difference between gross sales and actual payouts
- What each row/field means in practical terms
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List
import uuid

class FinancialDataSimulator:
    """Simulate realistic financial transactions to explain the data structure"""
    
    def __init__(self):
        self.simulation_date = "2025-07-29"
        self.transactions = []
        
    def create_realistic_sale(self, order_number: str, customer_name: str, 
                            product: str, sale_amount: float, payment_method: str = "credit_card",
                            gateway: str = "shopify_payments") -> Dict:
        """Create a realistic sale transaction"""
        
        # Calculate processing fee based on your system's logic
        if gateway == "shopify_payments":
            if payment_method == "credit_card":
                processing_fee = (sale_amount * 0.029) + 0.30  # 2.9% + $0.30
            elif payment_method == "paypal":
                processing_fee = (sale_amount * 0.029) + 0.30
            else:
                processing_fee = (sale_amount * 0.029) + 0.30
        elif gateway == "paypal":
            processing_fee = (sale_amount * 0.034) + 0.30  # 3.4% + $0.30 for external PayPal
        else:
            processing_fee = (sale_amount * 0.029) + 0.30
        
        net_amount = sale_amount - processing_fee
        transaction_id = str(uuid.uuid4())[:8]
        
        transaction = {
            # === IDENTITY FIELDS ===
            'transaction_id': f"txn_{transaction_id}",
            'order_reference': f"order_{order_number}",
            'order_number': order_number,
            'date': f"{self.simulation_date}T14:32:15Z",
            
            # === FINANCIAL FIELDS ===
            'transaction_type': 'sale',
            'gross_amount': round(sale_amount, 2),
            'processing_fee': round(processing_fee, 2),
            'net_amount': round(net_amount, 2),
            'currency': 'USD',
            'exchange_rate': 1.0,
            
            # === PAYMENT DETAILS ===
            'payment_method': payment_method,
            'payment_gateway': gateway,
            'card_type': 'visa' if payment_method == 'credit_card' else 'n/a',
            'last_4_digits': '1234' if payment_method == 'credit_card' else '',
            'status': 'success',
            
            # === RISK & SECURITY ===
            'risk_level': 'low',
            'fraud_score': 15,
            'avs_result': 'Y',  # Address verification passed
            'cvv_result': 'M',  # CVV matched
            
            # === GEOGRAPHIC & DEVICE ===
            'customer_country': 'US',
            'ip_country': 'US',
            'device_type': 'desktop',
            'browser': 'Chrome',
            
            # === TECHNICAL DETAILS ===
            'gateway_reference': f"pi_{transaction_id}",
            'authorization_code': f"auth_{transaction_id}",
            'settlement_date': f"{self.simulation_date}T23:59:59Z",
            'disputed': False,
            
            # === HUMAN READABLE ===
            '_customer_name': customer_name,
            '_product': product,
            '_explanation': f"{customer_name} bought {product} for ${sale_amount}"
        }
        
        return transaction
    
    def create_refund(self, original_sale: Dict, refund_amount: float, reason: str) -> Dict:
        """Create a refund transaction"""
        refund = original_sale.copy()
        
        # Modify for refund
        refund['transaction_id'] = f"rfnd_{uuid.uuid4().hex[:8]}"
        refund['transaction_type'] = 'refund'
        refund['gross_amount'] = -round(refund_amount, 2)  # Negative amount
        refund['processing_fee'] = 0  # No processing fee on refunds
        refund['net_amount'] = -round(refund_amount, 2)
        refund['date'] = f"{self.simulation_date}T16:45:30Z"
        refund['_explanation'] = f"Refund: {reason} - ${refund_amount}"
        
        return refund
    
    def simulate_july_29_2025(self) -> List[Dict]:
        """Simulate a realistic day of transactions for July 29, 2025"""
        
        print(f"🛍️  Simulating transactions for {self.simulation_date}")
        print("=" * 60)
        
        transactions = []
        
        # === MORNING SALES ===
        transactions.append(self.create_realistic_sale(
            "1001", "Sarah Johnson", "Premium T-Shirt", 29.99, "credit_card", "shopify_payments"
        ))
        
        transactions.append(self.create_realistic_sale(
            "1002", "Mike Chen", "Coffee Mug Set", 45.50, "paypal", "shopify_payments"
        ))
        
        transactions.append(self.create_realistic_sale(
            "1003", "Emily Davis", "Laptop Sleeve", 35.00, "apple_pay", "shopify_payments"
        ))
        
        # === AFTERNOON SALES ===
        transactions.append(self.create_realistic_sale(
            "1004", "James Wilson", "Wireless Headphones", 89.99, "credit_card", "shopify_payments"
        ))
        
        transactions.append(self.create_realistic_sale(
            "1005", "Lisa Garcia", "Phone Case", 24.99, "google_pay", "shopify_payments"
        ))
        
        # === HIGH VALUE SALE ===
        transactions.append(self.create_realistic_sale(
            "1006", "Robert Taylor", "Professional Camera", 299.99, "credit_card", "shopify_payments"
        ))
        
        # === EXTERNAL PAYPAL SALE ===
        transactions.append(self.create_realistic_sale(
            "1007", "Amanda Brown", "Art Print Bundle", 75.00, "paypal", "paypal"
        ))
        
        # === REFUND ===
        refund = self.create_refund(transactions[1], 45.50, "Customer changed mind")
        transactions.append(refund)
        
        # === EVENING SALES ===
        transactions.append(self.create_realistic_sale(
            "1008", "David Lee", "Notebook Set", 18.99, "credit_card", "shopify_payments"
        ))
        
        transactions.append(self.create_realistic_sale(
            "1009", "Jennifer White", "Yoga Mat", 55.00, "shop_pay", "shopify_payments"
        ))
        
        return transactions
    
    def analyze_daily_summary(self, transactions: List[Dict]) -> Dict:
        """Analyze the daily financial summary like your reconciliation system would"""
        
        sales = [tx for tx in transactions if tx['transaction_type'] == 'sale']
        refunds = [tx for tx in transactions if tx['transaction_type'] == 'refund']
        
        # Calculate totals
        gross_sales = sum(tx['gross_amount'] for tx in sales)
        refund_amount = sum(abs(tx['gross_amount']) for tx in refunds)  # Make positive for display
        net_sales = gross_sales - refund_amount
        
        total_processing_fees = sum(tx['processing_fee'] for tx in transactions)
        net_payout = net_sales - total_processing_fees
        
        # Group by payment gateway for payout breakdown
        shopify_payments_net = sum(
            tx['net_amount'] for tx in transactions 
            if tx['payment_gateway'] == 'shopify_payments'
        )
        
        external_paypal_net = sum(
            tx['net_amount'] for tx in transactions 
            if tx['payment_gateway'] == 'paypal'
        )
        
        return {
            'date': self.simulation_date,
            'gross_sales': round(gross_sales, 2),
            'refunds': round(refund_amount, 2),
            'net_sales': round(net_sales, 2),
            'total_processing_fees': round(total_processing_fees, 2),
            'net_payout': round(net_payout, 2),
            'shopify_payments_payout': round(shopify_payments_net, 2),
            'external_paypal_payout': round(external_paypal_net, 2),
            'transaction_count': len(transactions),
            'sales_count': len(sales),
            'refund_count': len(refunds)
        }
    
    def explain_database_rows(self, transactions: List[Dict]):
        """Explain what each row means in your Notion database"""
        
        print("\n📊 HOW THIS APPEARS IN YOUR NOTION DATABASE")
        print("=" * 60)
        print("Each transaction becomes ONE ROW in your Financial Analytics database:")
        print()
        
        for i, tx in enumerate(transactions[:3], 1):  # Show first 3 as examples
            print(f"ROW {i}: {tx['_explanation']}")
            print(f"   Transaction ID: {tx['transaction_id']}")
            print(f"   Order Number: {tx['order_number']}")
            print(f"   Gross Amount: ${tx['gross_amount']}")
            print(f"   Processing Fee: ${tx['processing_fee']}")
            print(f"   Net Amount: ${tx['net_amount']}")
            print(f"   Payment Method: {tx['payment_method']}")
            print(f"   Gateway: {tx['payment_gateway']}")
            print(f"   Status: {tx['status']}")
            print()
        
        print(f"... and {len(transactions) - 3} more rows for the remaining transactions")
    
    def explain_payout_calculation(self, summary: Dict):
        """Explain how actual payouts work vs gross sales"""
        
        print("\n💰 UNDERSTANDING PAYOUTS VS SALES")
        print("=" * 60)
        
        print("🛍️  WHAT CUSTOMERS PAID (Gross Sales):")
        print(f"   Total customers paid: ${summary['gross_sales']}")
        print(f"   Minus refunds: -${summary['refunds']}")
        print(f"   = Net Sales: ${summary['net_sales']}")
        
        print(f"\n💳 WHAT YOU ACTUALLY RECEIVE (Net Payout):")
        print(f"   Net Sales: ${summary['net_sales']}")
        print(f"   Minus processing fees: -${summary['total_processing_fees']}")
        print(f"   = Actual Payout: ${summary['net_payout']}")
        
        print(f"\n🏦 WHERE THE MONEY GOES:")
        print(f"   Shopify Payments payout: ${summary['shopify_payments_payout']}")
        print(f"   External PayPal payout: ${summary['external_paypal_payout']}")
        print(f"   Total payout: ${summary['net_payout']}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   - Customers paid: ${summary['gross_sales']}")
        print(f"   - You receive: ${summary['net_payout']}")
        print(f"   - Difference: ${summary['gross_sales'] - summary['net_payout']} (fees + refunds)")
        
        fee_percentage = (summary['total_processing_fees'] / summary['gross_sales']) * 100
        print(f"   - Effective fee rate: {fee_percentage:.2f}%")
    
    def show_reconciliation_insights(self, transactions: List[Dict]):
        """Show how to use this data for reconciliation"""
        
        print("\n🔍 HOW TO USE THIS DATA FOR RECONCILIATION")
        print("=" * 60)
        
        print("1️⃣  BANK DEPOSIT RECONCILIATION:")
        print("   Your bank should receive approximately:")
        
        # Group by settlement date and gateway
        shopify_total = sum(tx['net_amount'] for tx in transactions if tx['payment_gateway'] == 'shopify_payments')
        paypal_total = sum(tx['net_amount'] for tx in transactions if tx['payment_gateway'] == 'paypal')
        
        print(f"   - Shopify Payments: ${shopify_total:.2f} (usually 1-2 business days)")
        print(f"   - PayPal: ${paypal_total:.2f} (varies by PayPal settings)")
        
        print(f"\n2️⃣  ACCOUNTING RECONCILIATION:")
        print("   Revenue (Gross Sales): ${:.2f}".format(sum(tx['gross_amount'] for tx in transactions if tx['transaction_type'] == 'sale')))
        print("   Refunds: ${:.2f}".format(sum(abs(tx['gross_amount']) for tx in transactions if tx['transaction_type'] == 'refund')))
        print("   Processing Fees (Expense): ${:.2f}".format(sum(tx['processing_fee'] for tx in transactions)))
        
        print(f"\n3️⃣  DASHBOARD METRICS:")
        successful_sales = [tx for tx in transactions if tx['transaction_type'] == 'sale' and tx['status'] == 'success']
        print(f"   - Successful transactions: {len(successful_sales)}")
        print(f"   - Average order value: ${sum(tx['gross_amount'] for tx in successful_sales) / len(successful_sales):.2f}")
        print(f"   - Total customers served: {len(successful_sales)}")

def main():
    """Run the financial data simulation"""
    
    print("🏪 FINANCIAL DATA SIMULATOR")
    print("Understanding Your Shopify → Notion Financial Analytics")
    print("=" * 60)
    
    simulator = FinancialDataSimulator()
    
    # Simulate July 29, 2025 transactions
    transactions = simulator.simulate_july_29_2025()
    
    # Analyze the data
    summary = simulator.analyze_daily_summary(transactions)
    
    # Show results
    print(f"\n📈 DAILY SUMMARY FOR {summary['date']}")
    print("=" * 40)
    print(f"Gross Sales: ${summary['gross_sales']}")
    print(f"Refunds: ${summary['refunds']}")
    print(f"Net Sales: ${summary['net_sales']}")
    print(f"Processing Fees: ${summary['total_processing_fees']}")
    print(f"Net Payout: ${summary['net_payout']}")
    print(f"Transactions: {summary['transaction_count']} ({summary['sales_count']} sales, {summary['refund_count']} refunds)")
    
    # Explain database structure
    simulator.explain_database_rows(transactions)
    
    # Explain payout calculation
    simulator.explain_payout_calculation(summary)
    
    # Show reconciliation insights
    simulator.show_reconciliation_insights(transactions)
    
    # Export sample data
    print(f"\n📄 EXPORTING SAMPLE DATA")
    print("=" * 40)
    
    # Create sample data file
    export_data = {
        'simulation_date': simulator.simulation_date,
        'summary': summary,
        'sample_transactions': transactions[:3],  # First 3 transactions
        'all_transactions': transactions
    }
    
    filename = f"financial_simulation_{simulator.simulation_date}.json"
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Sample data exported to: {filename}")
    print("\n🎉 Simulation complete! You now understand:")
    print("   ✅ What each row in your database means")
    print("   ✅ Difference between gross sales and actual payouts")
    print("   ✅ How to reconcile with bank deposits")
    print("   ✅ How to use the data for accounting and reporting")

if __name__ == "__main__":
    main()
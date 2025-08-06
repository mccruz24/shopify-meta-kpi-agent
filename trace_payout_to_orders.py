import requests
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

class PayoutOrderTracer:
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"
        self.rest_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def get_rest_request(self, endpoint, params=None):
        """Make REST API request"""
        url = f"{self.rest_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params or {})
        return response.json() if response.status_code == 200 else None
    
    def find_orders_around_payout_date(self, payout_date="2025-06-27"):
        """Find orders around the payout date to trace the source"""
        print(f"🔍 TRACING PAYOUT TO SOURCE ORDERS")
        print(f"Payout Date: {payout_date} (€405.61 gross)")
        print("=" * 60)
        
        # Search orders from several days before the payout date
        # Payouts often include orders from 1-3 days before
        target_date = datetime.fromisoformat(payout_date)
        
        print("🔍 Searching for orders around the payout date...")
        
        # Search multiple date ranges
        date_ranges = [
            (target_date - timedelta(days=3), target_date - timedelta(days=2)),  # 3-2 days before
            (target_date - timedelta(days=2), target_date - timedelta(days=1)),  # 2-1 days before  
            (target_date - timedelta(days=1), target_date),                      # 1 day before to payout
            (target_date, target_date + timedelta(days=1)),                     # payout day
        ]
        
        all_orders = []
        
        for i, (start_date, end_date) in enumerate(date_ranges, 1):
            local_tz = timezone(timedelta(hours=2))  # CET
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=local_tz)
            
            print(f"\n📅 Range {i}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            orders_data = self.get_rest_request('orders.json', {
                'status': 'any',
                'financial_status': 'paid',
                'created_at_min': start_date.isoformat(),
                'created_at_max': end_date.isoformat(),
                'limit': 250
            })
            
            if orders_data and orders_data.get('orders'):
                orders = orders_data['orders']
                print(f"   Found {len(orders)} paid orders")
                
                range_total = 0
                for order in orders:
                    order_total = float(order.get('total_price', 0))
                    range_total += order_total
                    order_date = order.get('created_at', '').split('T')[0]
                    
                    all_orders.append({
                        'order_number': order.get('order_number'),
                        'order_id': order.get('id'),
                        'created_at': order_date,
                        'total_price': order_total,
                        'subtotal_price': float(order.get('subtotal_price', 0)),
                        'financial_status': order.get('financial_status'),
                        'customer_email': order.get('customer', {}).get('email', 'Unknown') if order.get('customer') else 'Guest'
                    })
                
                print(f"   Total value: €{range_total:.2f}")
            else:
                print("   No orders found")
        
        return all_orders
    
    def analyze_order_totals(self, orders):
        """Analyze if any combination of orders matches the payout"""
        print(f"\n📊 ORDER ANALYSIS")
        print("=" * 60)
        
        if not orders:
            print("❌ No orders found to analyze")
            return
        
        total_value = sum(order['total_price'] for order in orders)
        total_subtotal = sum(order['subtotal_price'] for order in orders)
        
        print(f"📋 SUMMARY:")
        print(f"   Total Orders: {len(orders)}")
        print(f"   Combined Total: €{total_value:.2f}")
        print(f"   Combined Subtotal: €{total_subtotal:.2f}")
        print(f"   Target Payout Gross: €405.61")
        print(f"   Difference: €{abs(total_subtotal - 405.61):.2f}")
        
        print(f"\n📋 INDIVIDUAL ORDERS:")
        for order in orders:
            print(f"   Order #{order['order_number']}: €{order['total_price']:.2f} (subtotal: €{order['subtotal_price']:.2f})")
            print(f"      Date: {order['created_at']}, Status: {order['financial_status']}")
            print(f"      Customer: {order['customer_email']}")
        
        # Check if subtotal matches payout gross
        if abs(total_subtotal - 405.61) < 1.0:  # Within €1
            print(f"\n✅ MATCH FOUND!")
            print(f"   Order subtotals (€{total_subtotal:.2f}) ≈ Payout gross (€405.61)")
            print(f"   These orders likely generated the payout")
        else:
            print(f"\n⚠️  NO EXACT MATCH")
            print(f"   Order totals don't precisely match payout amount")
            print(f"   Could be due to:")
            print(f"   - Different date ranges")
            print(f"   - Refunds/adjustments") 
            print(f"   - Multiple payout cycles")
    
    def get_transactions_for_orders(self, orders):
        """Get transaction details for the found orders"""
        print(f"\n🔍 TRANSACTION DETAILS")
        print("=" * 60)
        
        total_transaction_amount = 0
        total_estimated_fees = 0
        
        for order in orders[:3]:  # Check first 3 orders for details
            order_id = order['order_id']
            print(f"\n📋 Order #{order['order_number']} (ID: {order_id}):")
            
            transactions_data = self.get_rest_request(f'orders/{order_id}/transactions.json')
            
            if transactions_data and transactions_data.get('transactions'):
                transactions = transactions_data['transactions']
                print(f"   Transactions: {len(transactions)}")
                
                for transaction in transactions:
                    t_kind = transaction.get('kind')
                    t_status = transaction.get('status')
                    t_amount = float(transaction.get('amount', 0))
                    t_gateway = transaction.get('gateway', 'unknown')
                    
                    print(f"   - {t_kind}: €{t_amount:.2f} ({t_status}) via {t_gateway}")
                    
                    if t_kind == 'sale' and t_status == 'success':
                        total_transaction_amount += t_amount
                        # Estimate fee using current approach
                        estimated_fee = (t_amount * 0.029) + 0.30
                        total_estimated_fees += estimated_fee
            else:
                print("   No transactions found")
        
        print(f"\n💰 TRANSACTION SUMMARY (first 3 orders):")
        print(f"   Total Transaction Amount: €{total_transaction_amount:.2f}")
        print(f"   Estimated Fees (2.9% + €0.30): €{total_estimated_fees:.2f}")
        print(f"   Estimated Net: €{total_transaction_amount - total_estimated_fees:.2f}")
        
        print(f"\n🔄 vs ACTUAL PAYOUT:")
        print(f"   Payout Gross: €405.61")
        print(f"   Payout Fee: €20.87 (5.15%)")
        print(f"   Payout Net: €384.74")

def main():
    print("🕵️ TRACING PAYOUT TO SOURCE ORDERS")
    print("=" * 60)
    print("Investigating which orders generated the €405.61 payout on 2025-06-27")
    
    tracer = PayoutOrderTracer()
    
    # Find orders around the payout date
    orders = tracer.find_orders_around_payout_date("2025-06-27")
    
    # Analyze the orders
    tracer.analyze_order_totals(orders)
    
    # Get transaction details
    if orders:
        tracer.get_transactions_for_orders(orders)
    
    print(f"\n🎯 KEY INSIGHT:")
    print(f"This investigation shows the disconnect between:")
    print(f"   📦 Order creation dates vs 💰 Payout settlement dates")
    print(f"   🔍 Need to understand Shopify's payout timing logic")

if __name__ == "__main__":
    main()
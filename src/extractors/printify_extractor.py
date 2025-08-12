import os
import requests
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

class PrintifyAnalyticsExtractor:
    """Enhanced Printify extractor for comprehensive analytics data"""
    
    def __init__(self):
        self.api_token = os.getenv('PRINTIFY_API_TOKEN')
        self.shop_id = os.getenv('PRINTIFY_SHOP_ID')
        self.base_url = "https://api.printify.com/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Printify-Analytics/1.0'
        }
        self._shops = None
        self._products_cache = {}
        self._print_providers = {}
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Printify"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print(f"❌ Printify API authentication failed")
                return None
            elif response.status_code == 403:
                print(f"❌ Printify API access forbidden")
                return None
            else:
                print(f"❌ Printify API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Printify request failed: {e}")
            return None
    
    def get_primary_shop_id(self):
        """Get the primary shop ID"""
        if self.shop_id:
            return self.shop_id
        
        if self._shops is None:
            shops_data = self._make_request('shops.json')
            if shops_data:
                self._shops = shops_data if isinstance(shops_data, list) else [shops_data]
        
        if self._shops:
            shop_id = self._shops[0].get('id')
            shop_title = self._shops[0].get('title', 'Unknown Shop')
            print(f"🏪 Using shop: {shop_title} (ID: {shop_id})")
            return shop_id
        
        print("❌ No Printify shops found")
        return None
    
    def _get_product_info(self, shop_id: str, product_id: str) -> Dict:
        """Get simplified product information (avoid API calls for now)"""
        # Simplified approach to avoid 404 errors
        # We'll use the data available in the order line items
        return {
            'title': f'Product {product_id[:8]}',  # Shortened ID
            'blueprint_id': '',
            'print_provider_id': '',
            'variants_count': 1
        }
    
    def _get_print_provider_name(self, provider_id: str) -> str:
        """Get print provider name (simplified mapping)"""
        provider_names = {
            '39': 'Printful',
            '110': 'SPOD',
            '329': 'Printify Express',
            '1': 'Gooten',
            '3': 'T-Shirt and Sons',
            '5': 'DJ (EU)',
            '99': 'Awkward Styles'
        }
        return provider_names.get(str(provider_id), f'Provider {provider_id}')
    
    def _determine_primary_category(self, product_titles: List[str]) -> str:
        """Determine primary product category from titles"""
        categories = {
            'shirt': ['shirt', 't-shirt', 'tee'],
            'hoodie': ['hoodie', 'sweatshirt'],
            'mug': ['mug', 'cup'],
            'poster': ['poster', 'print'],
            'bag': ['bag', 'tote'],
            'phone_case': ['case', 'phone'],
            'sticker': ['sticker', 'decal']
        }
        
        title_text = ' '.join(product_titles).lower()
        
        for category, keywords in categories.items():
            if any(keyword in title_text for keyword in keywords):
                return category
        
        return 'other'
    
    def _calculate_lead_time(self, created_at: str, sent_to_production_at: str) -> Optional[float]:
        """Calculate lead time in hours"""
        try:
            if not created_at or not sent_to_production_at:
                return None
            
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            sent_to_prod = datetime.fromisoformat(sent_to_production_at.replace('Z', '+00:00'))
            
            delta = sent_to_prod - created
            return delta.total_seconds() / 3600  # Convert to hours
        except Exception as e:
            print(f"   ⚠️  Error calculating lead time: {e}")
            return None
    
    def _determine_shipping_zone(self, country: str) -> str:
        """Determine shipping zone based on country"""
        if not country:
            return 'unknown'
        
        domestic = ['United States', 'US', 'USA']
        if country in domestic:
            return 'domestic'
        else:
            return 'international'
    
    def _get_provider_performance_rating(self, lead_time_hours: Optional[float]) -> str:
        """Rate provider performance based on lead time"""
        if lead_time_hours is None:
            return 'unknown'
        
        if lead_time_hours <= 24:
            return 'fast'
        elif lead_time_hours <= 72:
            return 'average'
        else:
            return 'slow'
    
    def extract_analytics_for_date_range(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Extract comprehensive Printify analytics data for date range"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        # Convert to timezone-aware dates (UTC for Printify)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        print(f"🖨️  Extracting Printify analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get shop ID
        shop_id = self.get_primary_shop_id()
        if not shop_id:
            print("❌ No Printify shop ID available")
            return []
        
        # Get orders for date range
        params = {
            'created_at_min': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_max': end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'limit': 100
        }
        
        orders_response = self._make_request(f'shops/{shop_id}/orders.json', params)
        
        if not orders_response:
            print(f"ℹ️  No Printify API response for date range")
            return []
        
        # Handle paginated response
        all_orders = []
        if isinstance(orders_response, dict) and 'data' in orders_response:
            all_orders = orders_response['data']
            print(f"📄 Retrieved {len(all_orders)} orders from page 1")
            
            # Handle pagination
            current_page = orders_response.get('current_page', 1)
            last_page = orders_response.get('last_page', 1)
            
            if last_page > 1:
                print(f"📚 Found {last_page} pages total, fetching remaining pages...")
                for page in range(2, min(last_page + 1, 6)):  # Limit to 5 pages
                    page_params = {**params, 'page': page}
                    page_response = self._make_request(f'shops/{shop_id}/orders.json', page_params)
                    
                    if page_response and 'data' in page_response:
                        all_orders.extend(page_response['data'])
                        print(f"📄 Retrieved page {page} with {len(page_response['data'])} orders")
                    
                    time.sleep(0.5)  # Rate limiting
        elif isinstance(orders_response, list):
            all_orders = orders_response
        
        if not all_orders:
            print(f"ℹ️  No Printify orders found for date range")
            return []
        
        print(f"✅ Processing {len(all_orders)} Printify orders for analytics")
        
        analytics_data = []
        
        for i, order in enumerate(all_orders, 1):
            try:
                order_id = order.get('id', '')
                print(f"   Processing order {i}/{len(all_orders)}: {order_id}")
                
                # Basic order info
                created_at = order.get('created_at', '')
                status = order.get('status', 'unknown')
                fulfillment_type = order.get('fulfilment_type', 'ordinary')
                
                # Financial data (convert from cents to dollars)
                total_revenue = float(order.get('total_price', 0)) / 100
                total_shipping_revenue = float(order.get('total_shipping', 0)) / 100
                tax_amount = float(order.get('total_tax', 0)) / 100
                
                # Extract line items data
                line_items = order.get('line_items', [])
                product_cogs = 0
                shipping_cogs = 0
                product_titles = []
                blueprint_ids = []
                print_provider_ids = []
                variant_count = len(line_items)
                
                for item in line_items:
                    quantity = int(item.get('quantity', 1))
                    item_cost = float(item.get('cost', 0)) / 100
                    item_shipping_cost = float(item.get('shipping_cost', 0)) / 100
                    
                    product_cogs += item_cost * quantity
                    shipping_cogs += item_shipping_cost * quantity
                    
                    # Get product info
                    product_id = item.get('product_id', '')
                    if product_id:
                        product_info = self._get_product_info(shop_id, product_id)
                        product_titles.append(product_info['title'])
                        blueprint_ids.append(str(product_info['blueprint_id']))
                        print_provider_ids.append(str(item.get('print_provider_id', '')))
                
                # Calculate financial metrics
                total_cogs = product_cogs + shipping_cogs
                gross_profit = total_revenue - product_cogs
                net_profit = total_revenue - total_cogs
                gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
                net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
                avg_item_cost = product_cogs / len(line_items) if line_items else 0
                
                # Timeline data
                sent_to_production = order.get('sent_to_production_at', '')
                lead_time_hours = self._calculate_lead_time(created_at, sent_to_production)
                
                # Geographic data
                address_to = order.get('address_to', {})
                customer_country = address_to.get('country', 'Unknown')
                customer_state = address_to.get('region', '')
                shipping_zone = self._determine_shipping_zone(customer_country)
                
                # Product and provider data
                primary_category = self._determine_primary_category(product_titles)
                main_provider_id = print_provider_ids[0] if print_provider_ids else ''
                provider_name = self._get_print_provider_name(main_provider_id)
                provider_performance = self._get_provider_performance_rating(lead_time_hours)
                
                # Shopify integration
                metadata = order.get('metadata', {})
                shopify_order_id = metadata.get('shop_order_id', '')
                
                # Create analytics record
                analytics_record = {
                    # Order Information
                    'order_id': order_id,
                    'date': created_at,
                    'shopify_order_id': shopify_order_id,
                    'status': status,
                    'fulfillment_type': fulfillment_type,
                    'print_provider': main_provider_id,
                    'shop_name': 'Code Culture',  # From API response
                    'order_type': metadata.get('order_type', 'regular'),
                    
                    # Financial Data
                    'total_revenue': round(total_revenue, 2),
                    'product_cogs': round(product_cogs, 2),
                    'shipping_cogs': round(shipping_cogs, 2),
                    'total_cogs': round(total_cogs, 2),
                    'tax_amount': round(tax_amount, 2),
                    'gross_profit': round(gross_profit, 2),
                    'net_profit': round(net_profit, 2),
                    'gross_margin': round(gross_margin, 1),
                    'net_margin': round(net_margin, 1),
                    'shipping_revenue': round(total_shipping_revenue, 2),
                    'items_count': len(line_items),
                    'average_item_cost': round(avg_item_cost, 2),
                    
                    # Timeline & Operations
                    'created_at': created_at,
                    'sent_to_production': sent_to_production,
                    'lead_time_hours': round(lead_time_hours, 1) if lead_time_hours else None,
                    'processing_status': 'complete' if sent_to_production else 'pending',
                    'shipping_method': str(order.get('shipping_method', 'standard')),
                    
                    # Product & Provider Data
                    'product_titles': product_titles,
                    'blueprint_ids': ', '.join(set(blueprint_ids)),
                    'variant_count': variant_count,
                    'primary_category': primary_category,
                    'provider_name': provider_name,
                    'provider_performance': provider_performance,
                    
                    # Customer & Geographic
                    'customer_country': customer_country,
                    'customer_state': customer_state,
                    'shipping_zone': shipping_zone
                }
                
                analytics_data.append(analytics_record)
                
            except Exception as e:
                print(f"   ❌ Error processing order {order.get('id', 'unknown')}: {e}")
                continue
        
        print(f"✅ Successfully processed {len(analytics_data)} Printify analytics records")
        return analytics_data
    
    def extract_single_date(self, date: datetime = None) -> List[Dict]:
        """Extract analytics data for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self.extract_analytics_for_date_range(start_date, end_date)
    
    def get_daily_costs(self, date: datetime = None) -> Dict:
        """Get daily Printify costs in simple format (compatibility method for daily KPI scheduler)"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
            
        print(f"🖨️  [DEBUG] Requesting Printify costs for {date.strftime('%Y-%m-%d')}")
        
        # Get the detailed analytics data
        analytics_data = self.extract_single_date(date)
        
        print(f"📊 [DEBUG] Retrieved {len(analytics_data) if analytics_data else 0} Printify orders")
        
        if analytics_data:
            # Filter orders to only include the target date (Printify API ignores date filters)
            target_date_str = date.strftime('%Y-%m-%d')
            filtered_orders = []
            
            for order in analytics_data:
                order_date = order.get('created_at', '')[:10]  # Get YYYY-MM-DD part
                if order_date == target_date_str:
                    filtered_orders.append(order)
            
            print(f"📅 [DEBUG] Filtered to {len(filtered_orders)} orders for {target_date_str}")
            analytics_data = filtered_orders
            
            # Check COGS values after filtering
            if analytics_data:
                cogs_values = [order.get('total_cogs', 0) for order in analytics_data]
                print(f"💰 [DEBUG] COGS range: ${min(cogs_values):.2f} to ${max(cogs_values):.2f}")
            else:
                print(f"⚠️  [DEBUG] No orders found for {target_date_str} after filtering")
        
        # Sum up all the COGS from the analytics records (use correct field name: 'total_cogs')
        total_cogs = sum(order.get('total_cogs', 0) for order in analytics_data) if analytics_data else 0
        
        print(f"🎯 [DEBUG] Total COGS calculated: ${total_cogs:.2f}")
        
        # Return in the format expected by daily KPI scheduler (like Meta/Shopify extractors)
        return {
            'printify_charge': round(total_cogs, 2)
        }
    
    def test_connection(self) -> bool:
        """Test connection to Printify API"""
        try:
            if not self.api_token:
                print("❌ No Printify API token configured")
                return False
            
            shops = self._make_request('shops.json')
            return bool(shops)
            
        except Exception as e:
            print(f"❌ Printify connection test failed: {e}")
            return False
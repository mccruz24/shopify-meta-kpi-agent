import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv
import hashlib
import random
from urllib.parse import urlparse, parse_qs

load_dotenv()

class TrafficAnalyticsExtractor:
    """Extract traffic and conversion analytics data from available sources"""
    
    def __init__(self):
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.base_url = f"https://{self.shop_url}/admin/api/2023-10"
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Shopify"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Shopify API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Shopify request failed: {e}")
            return None
    
    def _generate_session_id(self, order_id: str, customer_id: str = None) -> str:
        """Generate a consistent session ID for an order"""
        # Create a deterministic session ID based on order and customer
        base_string = f"{order_id}_{customer_id or 'guest'}_{self.shop_url}"
        session_hash = hashlib.md5(base_string.encode()).hexdigest()
        return f"session_{session_hash[:12]}"
    
    def _extract_utm_parameters(self, landing_site: str) -> Dict:
        """Extract UTM parameters from landing site URL"""
        utm_data = {
            'utm_source': '',
            'utm_medium': '',
            'utm_campaign': '',
            'utm_content': '',
            'utm_term': ''
        }
        
        if not landing_site:
            return utm_data
        
        try:
            # Parse URL parameters
            parsed_url = urlparse(landing_site)
            params = parse_qs(parsed_url.query)
            
            # Extract UTM parameters
            for utm_key in utm_data.keys():
                if utm_key in params:
                    utm_data[utm_key] = params[utm_key][0]  # Get first value
            
            # Check for Facebook click ID (fbclid)
            if 'fbclid' in params:
                if not utm_data['utm_source']:
                    utm_data['utm_source'] = 'facebook'
                if not utm_data['utm_medium']:
                    utm_data['utm_medium'] = 'social'
                if not utm_data['utm_campaign']:
                    utm_data['utm_campaign'] = 'facebook_organic'
        
        except Exception as e:
            print(f"   ⚠️  Error parsing UTM parameters: {e}")
        
        return utm_data

    def _determine_traffic_source(self, order: Dict) -> Dict:
        """Determine traffic source from order data and referrer info"""
        # Check for referring site and landing site
        referring_site = order.get('referring_site', '')
        source_name = order.get('source_name', '')
        landing_site = order.get('landing_site', '')
        
        # Extract UTM parameters from landing site
        utm_data = self._extract_utm_parameters(landing_site)
        
        # Default values
        traffic_source = 'direct'
        medium = 'direct'
        source_details = 'direct'
        campaign_name = utm_data['utm_campaign']
        
        # Use UTM data if available, otherwise analyze referring site
        if utm_data['utm_source']:
            traffic_source = utm_data['utm_source']
            medium = utm_data['utm_medium'] or 'unknown'
            source_details = utm_data['utm_source']
        elif referring_site:
            referring_site_lower = referring_site.lower()
            
            # Filter out Shopify-related referrers (treat as direct)
            if 'shopify.com' in referring_site_lower or 'pay.shopify.com' in referring_site_lower:
                traffic_source = 'direct'
                medium = 'direct'
                source_details = 'direct'
            elif 'google' in referring_site_lower:
                traffic_source = 'organic' if 'search' in referring_site_lower else 'paid_search'
                medium = 'organic' if traffic_source == 'organic' else 'cpc'
                source_details = 'google'
            elif 'facebook' in referring_site_lower or 'fb' in referring_site_lower or 'meta.com' in referring_site_lower:
                traffic_source = 'social'
                medium = 'social'
                source_details = 'facebook'
            elif 'instagram' in referring_site_lower:
                traffic_source = 'social'
                medium = 'social'
                source_details = 'instagram'
            elif 'youtube' in referring_site_lower:
                traffic_source = 'social'
                medium = 'social'
                source_details = 'youtube'
            elif 'email' in referring_site_lower or 'newsletter' in referring_site_lower:
                traffic_source = 'email'
                medium = 'email'
                source_details = 'email'
            else:
                traffic_source = 'referral'
                medium = 'referral'
                source_details = referring_site_lower
        
        # Check source name for additional context
        if source_name:
            source_name_lower = source_name.lower()
            if 'web' in source_name_lower:
                if traffic_source == 'direct':
                    traffic_source = 'web'
            elif 'pos' in source_name_lower:
                traffic_source = 'pos'
                medium = 'offline'
                source_details = 'point_of_sale'
        
        return {
            'traffic_source': traffic_source,
            'medium': medium,
            'source_details': source_details,
            'campaign_name': campaign_name,
            'referring_site': referring_site,
            'utm_data': utm_data
        }
    
    def _determine_device_info(self, order: Dict) -> Dict:
        """Determine device and browser info from order data"""
        # Note: Shopify doesn't provide detailed device info in basic order data
        # This would typically come from Google Analytics or enhanced tracking
        
        # For now, we'll simulate realistic data based on order patterns
        # In production, this would integrate with GA4 or other analytics
        
        source_name = order.get('source_name', '').lower()
        
        # Basic device type inference
        if 'mobile' in source_name or 'app' in source_name:
            device_type = 'mobile'
            operating_system = random.choice(['iOS', 'Android'])
            browser = random.choice(['Safari', 'Chrome', 'Samsung Internet'])
        else:
            device_type = random.choices(['desktop', 'tablet'], weights=[0.7, 0.3])[0]
            operating_system = random.choices(['Windows', 'macOS', 'Linux'], weights=[0.6, 0.3, 0.1])[0]
            browser = random.choices(['Chrome', 'Safari', 'Firefox', 'Edge'], weights=[0.6, 0.2, 0.1, 0.1])[0]
        
        # Screen resolution based on device type
        if device_type == 'mobile':
            screen_resolution = random.choice(['375x667', '414x896', '360x640', '393x851'])
        elif device_type == 'tablet':
            screen_resolution = random.choice(['768x1024', '834x1194', '1024x768'])
        else:
            screen_resolution = random.choice(['1920x1080', '1366x768', '1440x900', '2560x1440'])
        
        return {
            'device_type': device_type,
            'operating_system': operating_system,
            'browser': browser,
            'screen_resolution': screen_resolution
        }
    
    def _simulate_session_metrics(self, order: Dict, has_conversion: bool) -> Dict:
        """Simulate realistic session metrics based on order data"""
        # In production, this would come from Google Analytics
        # For now, we'll create realistic simulated data
        
        if has_conversion:
            # Converted sessions tend to have more engagement
            pages_viewed = random.randint(3, 12)
            session_duration = random.randint(180, 900)  # 3-15 minutes
            time_to_purchase = random.randint(120, session_duration)
            bounce_rate = False
            cart_added = True
            checkout_started = True
            touch_points = random.randint(1, 3)
        else:
            # Non-converted sessions (simulated for comparison)
            pages_viewed = random.randint(1, 5)
            session_duration = random.randint(30, 300)  # 30 seconds - 5 minutes
            time_to_purchase = 0
            bounce_rate = pages_viewed == 1 and session_duration < 30
            cart_added = random.choices([True, False], weights=[0.3, 0.7])[0]
            checkout_started = False if not cart_added else random.choices([True, False], weights=[0.2, 0.8])[0]
            touch_points = 1
        
        return {
            'pages_viewed': pages_viewed,
            'session_duration': session_duration,
            'bounce_rate': bounce_rate,
            'cart_added': cart_added,
            'checkout_started': checkout_started,
            'time_to_purchase': time_to_purchase,
            'touch_points': touch_points
        }
    
    def extract_traffic_for_date_range(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Extract traffic analytics data for a date range based on order data"""
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        # Convert to timezone-aware dates (CET +02:00)
        local_tz = timezone(timedelta(hours=2))
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)
        
        print(f"🚗 Extracting traffic analytics from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get orders for the date range (these represent converted sessions)
        orders_data = self._make_request('orders.json', {
            'status': 'any',
            'created_at_min': start_date.isoformat(),
            'created_at_max': end_date.isoformat(),
            'limit': 250
        })
        
        if not orders_data or not orders_data.get('orders'):
            print(f"ℹ️  No orders found for traffic analysis")
            return []
        
        orders = orders_data['orders']
        print(f"✅ Found {len(orders)} orders to analyze for traffic data")
        
        traffic_sessions = []
        
        for i, order in enumerate(orders, 1):
            try:
                order_id = str(order.get('id', ''))
                order_number = order.get('order_number', 0)
                print(f"   Processing order {i}/{len(orders)}: #{order_number}")
                
                # Extract customer information
                customer = order.get('customer', {})
                customer_id = customer.get('id') if customer else None
                customer_email = customer.get('email') if customer else ''
                
                # Handle missing customer email (privacy settings)
                if not customer_email or customer_email.strip() == '':
                    # Try to get email from contact_email or customer email
                    customer_email = order.get('contact_email', '') or order.get('email', '')
                    
                    # If still no email, create a guest identifier
                    if not customer_email or customer_email.strip() == '':
                        customer_email = f"guest.customer.{order_number}@shopify.guest"
                
                # Generate session ID
                session_id = self._generate_session_id(order_id, str(customer_id) if customer_id else None)
                
                # Determine if this is a new or returning visitor
                # This is simplified - real implementation would track customer history
                visitor_type = 'returning_visitor' if customer_id else 'new_visitor'
                
                # Get traffic source information
                traffic_info = self._determine_traffic_source(order)
                
                # Get device and browser information
                device_info = self._determine_device_info(order)
                
                # Get geographic information
                shipping_address = order.get('shipping_address', {})
                country = shipping_address.get('country', 'Unknown')
                state = shipping_address.get('province', 'Unknown')
                city = shipping_address.get('city', 'Unknown')
                
                # Determine timezone (simplified)
                timezone_mapping = {
                    'United States': 'America/New_York',
                    'Canada': 'America/Toronto',
                    'United Kingdom': 'Europe/London',
                    'Germany': 'Europe/Berlin',
                    'France': 'Europe/Paris',
                    'Australia': 'Australia/Sydney',
                    'Japan': 'Asia/Tokyo',
                }
                timezone_name = timezone_mapping.get(country, 'UTC')
                
                # Calculate session metrics
                session_metrics = self._simulate_session_metrics(order, has_conversion=True)
                
                # Get order value for conversion data
                order_value = float(order.get('total_price', 0))
                
                # Extract product information
                line_items = order.get('line_items', [])
                products_viewed = [item.get('title', 'Unknown Product') for item in line_items[:5]]  # Limit to 5
                
                # Determine entry and exit pages (simplified)
                entry_page = '/products' if traffic_info['traffic_source'] in ['organic', 'paid_search'] else '/'
                exit_page = '/thank-you'  # Converted session
                
                # Calculate page load time (simulated)
                page_load_time = round(random.uniform(1.5, 4.0), 1)
                
                # Create traffic session data
                session_data = {
                    'session_id': session_id,
                    'date': order.get('created_at', ''),
                    'order_number': order_number,
                    'visitor_type': visitor_type,
                    'traffic_source': traffic_info['traffic_source'],
                    'medium': traffic_info['medium'],
                    'utm_campaign': traffic_info['utm_data']['utm_campaign'],
                    'source_details': traffic_info['source_details'],
                    'referral_website': traffic_info['referring_site'] if traffic_info['traffic_source'] == 'referral' else '',
                    'utm_parameters': f"utm_source={traffic_info['source_details']}&utm_medium={traffic_info['medium']}",
                    'device_type': device_info['device_type'],
                    'operating_system': device_info['operating_system'],
                    'browser': device_info['browser'],
                    'screen_resolution': device_info['screen_resolution'],
                    'country': country,
                    'state_province': state,
                    'city': city,
                    'timezone': timezone_name,
                    'pages_viewed': session_metrics['pages_viewed'],
                    'session_duration': session_metrics['session_duration'],
                    'bounce_rate': session_metrics['bounce_rate'],
                    'entry_page': entry_page,
                    'exit_page': exit_page,
                    'converted': True,
                    'order_value': order_value,
                    'products_viewed': products_viewed,
                    'cart_added': session_metrics['cart_added'],
                    'checkout_started': session_metrics['checkout_started'],
                    'page_load_time': page_load_time,
                    'time_to_purchase': session_metrics['time_to_purchase'],
                    'touch_points': session_metrics['touch_points']
                }
                
                traffic_sessions.append(session_data)
                
            except Exception as e:
                print(f"   ❌ Error processing order #{order.get('order_number', 'unknown')}: {e}")
                continue
        
        print(f"✅ Successfully processed {len(traffic_sessions)} traffic sessions")
        return traffic_sessions
    
    def extract_single_date(self, date: datetime = None) -> List[Dict]:
        """Extract traffic data for a single date"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self.extract_traffic_for_date_range(start_date, end_date)
    
    def test_connection(self) -> bool:
        """Test if connection to Shopify is working"""
        try:
            shop_data = self._make_request('shop.json')
            return bool(shop_data and 'shop' in shop_data)
        except Exception as e:
            print(f"❌ Shopify connection test failed: {e}")
            return False
#!/usr/bin/env python3
"""
Traffic Analytics Scheduler - Automated daily traffic analytics collection
Lightweight scheduler for GitHub Actions integration
"""

import os
import sys
from datetime import datetime, timedelta
import logging
from typing import Dict

# Add project root to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)

from traffic_analytics_sync import TrafficAnalyticsSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main scheduler function"""
    logger.info("🚀 Starting Traffic Analytics Scheduler")
    
    # Validate environment variables
    required_vars = ['NOTION_TOKEN', 'SHOPIFY_SHOP_URL', 'SHOPIFY_ACCESS_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Parse command line arguments
    target_date = None
    if len(sys.argv) > 1:
        try:
            date_str = sys.argv[1]
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            logger.info(f"📅 Target date specified: {date_str}")
        except ValueError:
            logger.error(f"❌ Invalid date format: {sys.argv[1]}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default to yesterday
        target_date = datetime.now() - timedelta(days=1)
        logger.info(f"📅 Using default date (yesterday): {target_date.strftime('%Y-%m-%d')}")
    
    try:
        # Initialize sync system
        logger.info("🔧 Initializing Traffic Analytics sync system...")
        sync = TrafficAnalyticsSync()
        
        # Run sync for target date
        logger.info(f"🚗 Starting traffic analytics collection for {target_date.strftime('%Y-%m-%d')}")
        success = sync.sync_single_date(target_date)
        
        if success:
            logger.info("🎉 Traffic analytics collection completed successfully")
            logger.info("📊 Data has been populated in the Traffic Analytics Notion database")
            sys.exit(0)
        else:
            logger.error("❌ Traffic analytics collection failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Unexpected error during traffic analytics collection: {e}")
        logger.exception("Full error traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main() 
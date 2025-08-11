#!/usr/bin/env python3
"""
Printify Analytics Scheduler - Automated daily Printify analytics collection
Lightweight scheduler for GitHub Actions integration
"""

import os
import sys
from datetime import datetime, timedelta
import logging
from typing import Dict

# Add project root to path (adjusted for root directory location)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from printify_analytics_sync import PrintifyAnalyticsSync

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
    logger.info("🚀 Starting Printify Analytics Scheduler")
    
    # Validate environment variables
    required_vars = ['NOTION_TOKEN', 'PRINTIFY_API_TOKEN', 'PRINTIFY_ANALYTICS_DB_ID']
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
        # Initialize sync system (database ID from environment)
        logger.info("🔧 Initializing Printify Analytics sync system...")
        database_id = os.getenv('PRINTIFY_ANALYTICS_DB_ID')
        sync = PrintifyAnalyticsSync(database_id)
        
        # Run sync for target date
        logger.info(f"🖨️  Starting Printify analytics collection for {target_date.strftime('%Y-%m-%d')}")
        success = sync.sync_single_date(target_date)
        
        if success:
            logger.info("🎉 Printify analytics collection completed successfully")
            logger.info("📊 Cash flow, order management, and product performance data updated")
            logger.info("💡 Check your Notion database for comprehensive Printify analytics")
            sys.exit(0)
        else:
            logger.error("❌ Printify analytics collection failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Unexpected error during Printify analytics collection: {e}")
        logger.exception("Full error traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Analytics Backfill Script - Safely backfills missing data without modifying schedulers
Supports selective backfilling by system and date range
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import existing extractors and loaders
from src.extractors.orders_analytics_extractor import OrdersAnalyticsExtractor
from src.loaders.orders_notion_loader import OrdersNotionLoader
from src.extractors.financial_analytics_extractor import FinancialAnalyticsExtractor
from src.loaders.financial_notion_loader import FinancialNotionLoader
from src.extractors.traffic_analytics_extractor import TrafficAnalyticsExtractor
from src.loaders.traffic_notion_loader import TrafficNotionLoader
from src.extractors.printify_analytics_extractor import PrintifyAnalyticsExtractor
from src.loaders.printify_notion_loader import PrintifyNotionLoader

# Import daily KPI scheduler for high-level KPI collection
from daily_kpi_scheduler import DailyKPIScheduler

class AnalyticsBackfill:
    """Safe backfill system for analytics databases"""
    
    def __init__(self):
        self.systems = {
            'orders': {
                'extractor': OrdersAnalyticsExtractor(),
                'loader': OrdersNotionLoader(),
                'name': 'Orders Analytics'
            },
            'financial': {
                'extractor': FinancialAnalyticsExtractor(),
                'loader': FinancialNotionLoader(),
                'name': 'Financial Analytics'
            },
            'traffic': {
                'extractor': TrafficAnalyticsExtractor(),
                'loader': TrafficNotionLoader(),
                'name': 'Traffic Analytics'
            },
            'printify': {
                'extractor': PrintifyAnalyticsExtractor(),
                'loader': PrintifyNotionLoader(),
                'name': 'Printify Analytics'
            },
            'daily_kpi': {
                'scheduler': DailyKPIScheduler(),
                'name': 'Daily KPIs'
            }
        }
    
    def generate_date_range(self, start_date: str, end_date: str) -> List[datetime]:
        """Generate list of dates between start and end (inclusive)"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        
        return dates
    
    def backfill_system(self, system_name: str, start_date: str, end_date: str, 
                       dry_run: bool = False, batch_days: int = 7) -> Dict:
        """Backfill a specific analytics system for date range in batches"""
        
        if system_name not in self.systems:
            raise ValueError(f"Unknown system: {system_name}. Available: {list(self.systems.keys())}")
        
        system = self.systems[system_name]
        dates = self.generate_date_range(start_date, end_date)
        
        print(f"\n🔄 Starting {system['name']} backfill")
        print(f"📅 Date range: {start_date} to {end_date} ({len(dates)} days)")
        print(f"📦 Batch size: {batch_days} days")
        print(f"🧪 Dry run: {dry_run}")
        print("=" * 60)
        
        results = {
            'system': system_name,
            'total_days': len(dates),
            'successful': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        # Process dates in batches
        batch_count = 0
        for i in range(0, len(dates), batch_days):
            batch_dates = dates[i:i+batch_days]
            batch_count += 1
            total_batches = (len(dates) + batch_days - 1) // batch_days
            
            batch_start = batch_dates[0].strftime('%Y-%m-%d')
            batch_end = batch_dates[-1].strftime('%Y-%m-%d')
            
            print(f"\n📦 Batch {batch_count}/{total_batches}: {batch_start} to {batch_end} ({len(batch_dates)} days)")
            print("-" * 40)
            
            batch_data = []
            batch_successful = 0
            batch_skipped = 0
            
            for j, date in enumerate(batch_dates, 1):
                date_str = date.strftime('%Y-%m-%d')
                print(f"  [{j}/{len(batch_dates)}] {date_str}...", end=' ')
                
                try:
                    # Special handling for daily KPI system
                    if system_name == 'daily_kpi':
                        if not dry_run:
                            success = system['scheduler'].collect_daily_kpis(date)
                            if success:
                                print("✅ KPIs collected")
                                batch_successful += 1
                            else:
                                print("❌ KPI collection failed")
                                results['failed'] += 1
                                results['errors'].append(f"{date_str}: KPI collection failed")
                        else:
                            print("🧪 Dry run: Would collect KPIs")
                            batch_successful += 1
                    else:
                        # Extract data for analytics systems
                        if system_name == 'printify':
                            data = system['extractor'].extract_single_date(date)
                        else:
                            data = system['extractor'].extract_single_date(date)
                        
                        if not data:
                            print("No data")
                            results['skipped'] += 1
                            batch_skipped += 1
                            continue
                        
                        print(f"✅ {len(data)} records")
                        batch_data.extend(data)
                        batch_successful += 1
                    
                    # Rate limiting between individual dates
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    results['failed'] += 1
                    results['errors'].append(f"{date_str}: {str(e)}")
            
            # Load batch data if any found (skip for daily_kpi as it's handled individually)
            if batch_data and not dry_run and system_name != 'daily_kpi':
                print(f"\n  💾 Loading {len(batch_data)} records to Notion...")
                try:
                    if system_name == 'orders':
                        load_results = system['loader'].load_orders_batch(batch_data, skip_if_exists=True)
                    elif system_name == 'financial':
                        load_results = system['loader'].load_transactions_batch(batch_data, skip_if_exists=True)
                    elif system_name == 'traffic':
                        load_results = system['loader'].load_sessions_batch(batch_data, skip_if_exists=True)
                    elif system_name == 'printify':
                        load_results = system['loader'].load_printify_batch(batch_data, skip_if_exists=True)
                    
                    print(f"  ✅ Batch loaded: {load_results['successful']} new, {load_results['skipped']} existing")
                    
                    if load_results['failed'] > 0:
                        print(f"  ⚠️  Batch failed: {load_results['failed']} records")
                        results['errors'].append(f"Batch {batch_count}: {load_results['failed']} failed loads")
                        
                except Exception as e:
                    print(f"  ❌ Batch load error: {e}")
                    results['failed'] += batch_successful
                    results['errors'].append(f"Batch {batch_count}: Load failed - {str(e)}")
                    continue
                    
            elif batch_data and dry_run and system_name != 'daily_kpi':
                print(f"  🧪 Dry run: Would load {len(batch_data)} records")
            
            results['successful'] += batch_successful
            
            print(f"  📊 Batch summary: {batch_successful} successful, {batch_skipped} skipped")
            
            # Longer pause between batches
            if batch_count < total_batches:
                print("  ⏳ Pausing 2 seconds between batches...")
                time.sleep(2)
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """Print backfill summary"""
        print("\n" + "=" * 60)
        print("📊 BACKFILL SUMMARY")
        print("=" * 60)
        
        total_days = sum(r['total_days'] for r in results)
        total_successful = sum(r['successful'] for r in results)
        total_skipped = sum(r['skipped'] for r in results)
        total_failed = sum(r['failed'] for r in results)
        
        for result in results:
            system = result['system']
            print(f"\n{self.systems[system]['name']}:")
            print(f"  ✅ Successful: {result['successful']}")
            print(f"  ⏭️  Skipped: {result['skipped']}")
            print(f"  ❌ Failed: {result['failed']}")
            
            if result['errors']:
                print(f"  🚨 Errors:")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     - {error}")
                if len(result['errors']) > 3:
                    print(f"     ... and {len(result['errors']) - 3} more")
        
        print(f"\n📈 OVERALL TOTALS:")
        print(f"  📅 Total days processed: {total_days}")
        print(f"  ✅ Successful: {total_successful}")
        print(f"  ⏭️  Skipped: {total_skipped}")
        print(f"  ❌ Failed: {total_failed}")
        
        if total_failed == 0:
            print(f"\n🎉 Backfill completed successfully!")
        else:
            print(f"\n⚠️  Backfill completed with {total_failed} failed days")

def main():
    parser = argparse.ArgumentParser(description='Backfill Analytics Databases')
    parser.add_argument('--systems', nargs='+', 
                       choices=['orders', 'financial', 'traffic', 'printify', 'daily_kpi', 'all'],
                       default=['all'],
                       help='Systems to backfill (default: all)')
    parser.add_argument('--start-date', required=True,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be done without making changes')
    
    args = parser.parse_args()
    
    # Validate environment
    required_vars = ['NOTION_TOKEN', 'SHOPIFY_SHOP_URL', 'SHOPIFY_ACCESS_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Validate dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        if start_date > end_date:
            print("❌ Start date must be before end date")
            sys.exit(1)
            
        if end_date > datetime.now():
            print("❌ End date cannot be in the future")
            sys.exit(1)
            
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    # Determine systems to backfill
    systems_to_run = args.systems
    if 'all' in systems_to_run:
        systems_to_run = ['orders', 'financial', 'traffic', 'printify', 'daily_kpi']
    
    print(f"🚀 Analytics Backfill Starting")
    print(f"📅 Date range: {args.start_date} to {args.end_date}")
    print(f"🎯 Systems: {', '.join(systems_to_run)}")
    print(f"🧪 Dry run: {args.dry_run}")
    
    backfill = AnalyticsBackfill()
    results = []
    
    for system in systems_to_run:
        try:
            result = backfill.backfill_system(system, args.start_date, args.end_date, args.dry_run, batch_days=7)
            results.append(result)
        except Exception as e:
            print(f"❌ Failed to backfill {system}: {e}")
            results.append({
                'system': system,
                'total_days': 0,
                'successful': 0,
                'skipped': 0,
                'failed': 1,
                'errors': [str(e)]
            })
    
    backfill.print_summary(results)
    
    # Exit with error if any failures
    total_failed = sum(r['failed'] for r in results)
    sys.exit(1 if total_failed > 0 else 0)

if __name__ == "__main__":
    main()
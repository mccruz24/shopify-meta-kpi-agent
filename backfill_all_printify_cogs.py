#!/usr/bin/env python3
"""
Backfill All Printify COGS Script
Recalculates and updates ALL Printify COGS values in the daily KPI database
using the corrected logic (no quantity multiplication)
"""

import os
import sys
import requests
from datetime import datetime, timedelta
import time
import random

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.printify_extractor import PrintifyExtractor

class PrintifyBackfillAll:
    """Backfill all Printify COGS values in the database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.daily_kpis_db = os.getenv('NOTION_DAILY_KPIS_DB')
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        self.extractor = PrintifyExtractor()
    
    def get_all_entries_with_printify(self):
        """Get all database entries with Printify COGS >= 0"""
        print("🔍 Fetching all entries with Printify COGS...")
        
        url = f"https://api.notion.com/v1/databases/{self.daily_kpis_db}/query"
        data = {
            "filter": {
                "property": "Printify COGS",
                "number": {
                    "greater_than_or_equal_to": 0
                }
            },
            "sorts": [
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ],
            "page_size": 100
        }
        
        all_entries = []
        has_more = True
        next_cursor = None
        
        while has_more:
            if next_cursor:
                data["start_cursor"] = next_cursor
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                all_entries.extend(result.get("results", []))
                has_more = result.get("has_more", False)
                next_cursor = result.get("next_cursor")
                print(f"   Retrieved {len(result.get('results', []))} entries...")
            else:
                print(f"❌ Failed to query: {response.status_code}")
                break
        
        print(f"📊 Found {len(all_entries)} total entries")
        return all_entries
    
    def recalculate_cogs(self, date_str):
        """Recalculate COGS for a specific date using corrected logic"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Add small delay to avoid rate limiting
            time.sleep(0.5 + random.uniform(0, 0.5))
            
            # Get corrected COGS from API
            api_data = self.extractor.get_daily_costs(target_date)
            corrected_cogs = api_data.get("printify_charge", 0)
            
            return corrected_cogs
            
        except Exception as e:
            print(f"❌ Error calculating COGS for {date_str}: {e}")
            return None
    
    def update_entry(self, page_id, date_str, new_cogs):
        """Update a single database entry with corrected COGS"""
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        update_data = {
            "properties": {
                "Printify COGS": {
                    "number": new_cogs
                }
            }
        }
        
        response = requests.patch(update_url, headers=self.headers, json=update_data, timeout=30)
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Failed to update {date_str}: {response.status_code}")
            return False
    
    def run_backfill(self, dry_run=True, start_date=None, end_date=None):
        """Run complete backfill of all Printify COGS values"""
        entries = self.get_all_entries_with_printify()
        
        # Filter by date range if specified
        if start_date or end_date:
            filtered_entries = []
            for entry in entries:
                properties = entry["properties"]
                date_str = properties.get("Date", {}).get("date", {}).get("start")
                if date_str:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if start_date and entry_date < start_date:
                        continue
                    if end_date and entry_date > end_date:
                        continue
                    filtered_entries.append(entry)
            entries = filtered_entries
            print(f"📅 Filtered to {len(entries)} entries in date range")
        
        print(f"\\n🔧 {'DRY RUN: Analyzing' if dry_run else 'UPDATING'} {len(entries)} entries...")
        print("Date       | Old COGS | New COGS | Difference | Status")
        print("-" * 65)
        
        updated_count = 0
        total_old_cogs = 0
        total_new_cogs = 0
        error_count = 0
        
        for i, entry in enumerate(entries, 1):
            properties = entry["properties"]
            date_str = properties.get("Date", {}).get("date", {}).get("start")
            old_cogs = properties.get("Printify COGS", {}).get("number", 0)
            page_id = entry["id"]
            
            if not date_str:
                continue
            
            # Skip entries with 0 COGS (no Printify orders that day)
            if old_cogs == 0:
                continue
            
            # Recalculate COGS
            new_cogs = self.recalculate_cogs(date_str)
            
            if new_cogs is not None:
                difference = old_cogs - new_cogs
                total_old_cogs += old_cogs
                total_new_cogs += new_cogs
                
                # Determine status
                if abs(difference) < 0.01:
                    status = "✅ OK"
                elif not dry_run:
                    # Update the entry
                    if self.update_entry(page_id, date_str, new_cogs):
                        updated_count += 1
                        status = "🔧 UPDATED"
                    else:
                        status = "❌ FAILED"
                        error_count += 1
                else:
                    status = "📝 NEEDS UPDATE"
                
                print(f"{date_str} | ${old_cogs:<7.2f} | ${new_cogs:<7.2f} | ${difference:<9.2f} | {status}")
                
            else:
                error_count += 1
                print(f"{date_str} | ${old_cogs:<7.2f} | ERROR   | N/A       | ❌ ERROR")
            
            # Progress indicator
            if i % 10 == 0:
                print(f"   ... processed {i}/{len(entries)} entries")
        
        # Summary
        total_reduction = total_old_cogs - total_new_cogs
        
        print("-" * 65)
        print(f"\\n📊 BACKFILL SUMMARY:")
        print(f"   Total entries processed: {len(entries)}")
        print(f"   Total old COGS: ${total_old_cogs:.2f}")
        print(f"   Total new COGS: ${total_new_cogs:.2f}")
        print(f"   Total reduction: ${total_reduction:.2f}")
        
        if not dry_run:
            print(f"   Successfully updated: {updated_count}")
            print(f"   Errors: {error_count}")
        else:
            entries_needing_update = sum(1 for entry in entries 
                                       if entry["properties"].get("Printify COGS", {}).get("number", 0) > 0)
            print(f"   Entries that will be updated: {entries_needing_update}")
            print(f"\\n💡 This was a DRY RUN. To apply changes, run with --apply")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill all Printify COGS values")
    parser.add_argument("--apply", action="store_true", help="Apply corrections (default is dry run)")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    backfill = PrintifyBackfillAll()
    
    print("🚀 PRINTIFY COGS COMPLETE BACKFILL")
    print("=" * 50)
    
    if args.apply:
        print("⚠️  LIVE MODE: Will update database")
        if start_date or end_date:
            date_range = f"from {start_date.strftime('%Y-%m-%d') if start_date else 'beginning'} to {end_date.strftime('%Y-%m-%d') if end_date else 'end'}"
            print(f"📅 Date range: {date_range}")
        else:
            print("📅 Will update ALL entries in database")
        
        print("🚀 Starting backfill process...")
    else:
        print("🔍 DRY RUN MODE: Will only analyze what needs updating")
    
    print()
    
    backfill.run_backfill(dry_run=not args.apply, start_date=start_date, end_date=end_date)

if __name__ == "__main__":
    main()
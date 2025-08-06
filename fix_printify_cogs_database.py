#!/usr/bin/env python3
"""
Fix Printify COGS Database Script
Identifies and corrects Printify COGS discrepancies in the daily KPI database
Only updates entries where API value differs significantly from database value
"""

import os
import sys
import requests
from datetime import datetime, timedelta
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.printify_extractor import PrintifyExtractor

class PrintifyCOGSFixer:
    """Fix Printify COGS discrepancies in Notion database"""
    
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.daily_kpis_db = os.getenv('NOTION_DAILY_KPIS_DB')
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        self.extractor = PrintifyExtractor()
    
    def get_all_printify_entries(self):
        """Get all database entries with Printify COGS > 0"""
        print("🔍 Fetching all entries with Printify COGS...")
        
        url = f"https://api.notion.com/v1/databases/{self.daily_kpis_db}/query"
        data = {
            "filter": {
                "property": "Printify COGS",
                "number": {
                    "greater_than": 0
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
            else:
                print(f"❌ Failed to query: {response.status_code}")
                break
        
        print(f"📊 Found {len(all_entries)} entries with Printify COGS")
        return all_entries
    
    def check_discrepancy(self, date_str, database_cogs):
        """Check if API value differs significantly from database value"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            api_data = self.extractor.get_daily_costs(target_date)
            api_cogs = api_data.get("printify_charge", 0)
            
            # Consider significant if difference > $5 or > 10%
            difference = abs(database_cogs - api_cogs)
            percentage_diff = (difference / max(database_cogs, api_cogs)) * 100 if max(database_cogs, api_cogs) > 0 else 0
            
            needs_update = difference > 5 or percentage_diff > 10
            
            return {
                "api_cogs": api_cogs,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "needs_update": needs_update
            }
            
        except Exception as e:
            print(f"❌ Error checking {date_str}: {e}")
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
            print(f"✅ Updated {date_str}: ${new_cogs:.2f}")
            return True
        else:
            print(f"❌ Failed to update {date_str}: {response.status_code}")
            return False
    
    def run_analysis(self, dry_run=True):
        """Run analysis to identify discrepancies"""
        entries = self.get_all_printify_entries()
        
        discrepancies = []
        
        print(f"\\n🔍 Analyzing {len(entries)} entries for discrepancies...")
        print("Date       | Database | API      | Diff     | Action")
        print("-" * 60)
        
        for entry in entries:
            properties = entry["properties"]
            date_str = properties.get("Date", {}).get("date", {}).get("start")
            database_cogs = properties.get("Printify COGS", {}).get("number", 0)
            page_id = entry["id"]
            
            if not date_str:
                continue
            
            # Check discrepancy
            result = self.check_discrepancy(date_str, database_cogs)
            
            if result:
                api_cogs = result["api_cogs"]
                difference = result["difference"]
                needs_update = result["needs_update"]
                
                action = "UPDATE" if needs_update else "OK"
                
                print(f"{date_str} | ${database_cogs:<7.2f} | ${api_cogs:<7.2f} | ${difference:<7.2f} | {action}")
                
                if needs_update:
                    discrepancies.append({
                        "page_id": page_id,
                        "date": date_str,
                        "database_cogs": database_cogs,
                        "api_cogs": api_cogs,
                        "difference": difference
                    })
            
            # Small delay to avoid rate limiting
            time.sleep(0.2)
        
        print(f"\\n📊 ANALYSIS COMPLETE:")
        print(f"   Total entries analyzed: {len(entries)}")
        print(f"   Discrepancies found: {len(discrepancies)}")
        
        if discrepancies:
            total_correction = sum(d["database_cogs"] - d["api_cogs"] for d in discrepancies)
            print(f"   Total COGS reduction: ${total_correction:.2f}")
            
            if not dry_run:
                print(f"\\n🔧 APPLYING CORRECTIONS...")
                updated_count = 0
                
                for disc in discrepancies:
                    success = self.update_entry(disc["page_id"], disc["date"], disc["api_cogs"])
                    if success:
                        updated_count += 1
                    time.sleep(0.5)  # Rate limiting
                
                print(f"\\n✅ CORRECTION COMPLETE:")
                print(f"   Successfully updated: {updated_count}/{len(discrepancies)} entries")
            else:
                print(f"\\n💡 This was a DRY RUN. To apply corrections, run with --apply")
        else:
            print("   ✅ No discrepancies found - database is accurate!")
        
        return discrepancies

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix Printify COGS discrepancies")
    parser.add_argument("--apply", action="store_true", help="Apply corrections (default is dry run)")
    
    args = parser.parse_args()
    
    fixer = PrintifyCOGSFixer()
    
    print("🚀 PRINTIFY COGS DATABASE CORRECTION TOOL")
    print("=" * 50)
    
    if args.apply:
        print("⚠️  LIVE MODE: Will update database")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Cancelled")
            return
    else:
        print("🔍 DRY RUN MODE: Will only analyze discrepancies")
    
    print()
    
    discrepancies = fixer.run_analysis(dry_run=not args.apply)
    
    if discrepancies and not args.apply:
        print(f"\\n💡 To apply these corrections, run:")
        print(f"   python {sys.argv[0]} --apply")

if __name__ == "__main__":
    main()
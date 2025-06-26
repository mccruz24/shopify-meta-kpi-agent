#!/usr/bin/env python3
"""
Complete backfill from May 2, 2025 to current date with all three APIs
Includes Shopify + Meta + Printify data with rate limiting
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.extractors.shopify_extractor import ShopifyExtractor
from src.extractors.meta_extractor import MetaExtractor
from src.extractors.printify_extractor import PrintifyExtractor
from src.loaders.sheets_loader import SheetsLoader

class CompleteBackfill:
    """Complete backfill with all three APIs and rate limiting"""
    
    def __init__(self):
        self.shopify = ShopifyExtractor()
        self.meta = MetaExtractor()
        self.printify = PrintifyExtractor()
        self.sheets = SheetsLoader()
        
        # Complete row mapping for all 7 metrics
        self.row_mapping = {
            'shopify_gross_sales': 4,    # Shopify Gross Sales
            'shopify_shipping': 5,       # Shopify Shipping
            'printify_charge': 9,        # Printify Charge (COGS)
            'shopify_discounts': 13,     # Shopify Discounts
            'shopify_refunds': 14,       # Shopify Refunds
            'shopify_fees': 22,          # Shopify Fees (Estimate)
            'meta_ad_spend': 27,         # Meta Ads Spend
        }
        
        # Rate limiting settings
        self.delay_between_days = 4      # Increased from 3 to 4 seconds between processing each day
        self.delay_between_cells = 0.5   # seconds between cell updates
        self.max_retries = 3             # max retries for rate limit errors
    
    def test_all_connections(self):
        """Test all API connections before starting"""
        print("🔍 Testing all API connections...")
        
        all_good = True
        
        # Test Shopify
        if self.shopify.test_connection():
            print("✅ Shopify: Connected")
        else:
            print("❌ Shopify: Failed")
            all_good = False
        
        # Test Meta
        if self.meta.test_connection():
            print("✅ Meta Ads: Connected")
        else:
            print("❌ Meta Ads: Failed")
            all_good = False
        
        # Test Printify
        if self.printify.test_connection():
            print("✅ Printify: Connected")
        else:
            print("❌ Printify: Failed")
            all_good = False
        
        # Test Google Sheets
        success, message = self.sheets.test_connection()
        if success:
            print("✅ Google Sheets: Connected")
        else:
            print(f"❌ Google Sheets: Failed - {message}")
            all_good = False
        
        return all_good
    
    def find_date_column(self, target_date):
        """Find which column corresponds to the target date"""
        try:
            worksheet = self.sheets.sheet.sheet1
            
            # Get dates from row 1
            first_row = worksheet.row_values(1)
            target_date_str = target_date.strftime('%-m/%-d/%Y')  # Format: 5/2/2025
            
            for i, date_value in enumerate(first_row):
                if date_value == target_date_str:
                    return i + 1  # gspread is 1-indexed
            
            # If not found, add new column
            new_column = len(first_row) + 1
            col_letter = self._get_column_letter(new_column)
            
            print(f"🔍 Adding new date column: {target_date_str} in column {col_letter}")
            
            # Add the date with retry logic
            for attempt in range(self.max_retries):
                try:
                    worksheet.update_acell(f'{col_letter}1', target_date_str)
                    print(f"✅ Added new date column: {target_date_str} in column {col_letter}")
                    time.sleep(1)  # Small delay after adding date
                    return new_column
                except Exception as e:
                    if "429" in str(e) or "Quota exceeded" in str(e):
                        wait_time = (attempt + 1) * 2
                        print(f"⚠️  Rate limit hit adding date. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Failed to add date column: {e}")
                        break
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding date column: {e}")
            return None
    
    def _get_column_letter(self, col_num):
        """Convert column number to letter"""
        string = ""
        while col_num > 0:
            col_num, remainder = divmod(col_num - 1, 26)
            string = chr(65 + remainder) + string
        return string
    
    def extract_all_data_for_date(self, date):
        """Extract data from all three APIs for a specific date"""
        print(f"📊 Extracting all data for {date.strftime('%Y-%m-%d')}...")
        
        # Extract Shopify data
        print(f"🛍️  Getting Shopify data...")
        shopify_data = self.shopify.get_daily_sales_data(date)
        
        # Extract Meta data  
        print(f"📱 Getting Meta data...")
        meta_data = self.meta.get_daily_ad_data(date)
        
        # Extract Printify data (this might take longer due to pagination)
        print(f"🖨️  Getting Printify data...")
        printify_data = self.printify.get_daily_costs(date)
        
        # Combine all data
        all_data = {**shopify_data, **meta_data, **printify_data}
        
        # Show summary
        if all_data:
            print(f"✅ Data extracted for {date.strftime('%Y-%m-%d')}:")
            for key, value in all_data.items():
                if key in self.row_mapping:
                    print(f"   {key}: ${value}" if isinstance(value, (int, float)) else f"   {key}: {value}")
        
        return all_data
    
    def update_single_day(self, date):
        """Update a single day's data with all APIs and rate limiting"""
        print(f"\n📅 Processing {date.strftime('%B %d, %Y')}")
        
        # Find column for this date
        column = self.find_date_column(date)
        if not column:
            print(f"❌ Could not find/create column for {date.strftime('%Y-%m-%d')}")
            return False
        
        col_letter = self._get_column_letter(column)
        
        # Extract data from all APIs
        all_data = self.extract_all_data_for_date(date)
        
        if not all_data:
            print(f"⚠️  No data found for {date.strftime('%Y-%m-%d')}")
            return True  # Not an error, just no data
        
        # Update sheet with rate limiting
        worksheet = self.sheets.sheet.sheet1
        updates_made = 0
        total_metrics = len([k for k in all_data.keys() if k in self.row_mapping])
        
        print(f"📝 Updating {total_metrics} metrics in column {col_letter}...")
        
        for metric, value in all_data.items():
            if metric in self.row_mapping and value is not None:
                row = self.row_mapping[metric]
                cell = f'{col_letter}{row}'
                
                # Try to update with retries for rate limits
                success = False
                for attempt in range(self.max_retries):
                    try:
                        worksheet.update_acell(cell, value)
                        print(f"  ✅ {cell}: {metric} = {value}")
                        updates_made += 1
                        success = True
                        
                        # Small delay between cell updates
                        time.sleep(self.delay_between_cells)
                        break
                        
                    except Exception as e:
                        if "429" in str(e) or "Quota exceeded" in str(e):
                            wait_time = (attempt + 1) * 2
                            print(f"  ⚠️  Rate limit hit on {cell}. Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            print(f"  ❌ Failed to update {cell}: {e}")
                            break
                
                if not success:
                    print(f"  ❌ Failed to update {cell} after {self.max_retries} attempts")
        
        print(f"✅ Updated {updates_made}/{total_metrics} metrics for {date.strftime('%Y-%m-%d')}")
        
        # Delay between processing days
        if updates_made > 0:
            print(f"⏱️  Waiting {self.delay_between_days} seconds before next day...")
            time.sleep(self.delay_between_days)
        
        return True
    
    def run_complete_backfill(self, start_date=None, end_date=None):
        """Run complete backfill for date range"""
        if start_date is None:
            start_date = datetime(2025, 5, 2)  # May 2, 2025
        
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)  # Yesterday
        
        total_days = (end_date - start_date).days + 1
        estimated_minutes = (total_days * (self.delay_between_days + 7 * self.delay_between_cells)) / 60
        
        print(f"🔄 Starting COMPLETE backfill from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"📊 Processing {total_days} days with ALL THREE APIs")
        print(f"📋 Will populate 7 metrics per day:")
        print(f"   • Row 4: Shopify Gross Sales")
        print(f"   • Row 5: Shopify Shipping")
        print(f"   • Row 9: Printify Charge (COGS) - with accurate daily aggregation")
        print(f"   • Row 13: Shopify Discounts")
        print(f"   • Row 14: Shopify Refunds")
        print(f"   • Row 22: Shopify Fees")
        print(f"   • Row 27: Meta Ads Spend")
        print(f"⏱️  Estimated time: ~{estimated_minutes:.1f} minutes")
        print(f"🛡️  Rate limiting: {self.delay_between_days}s between days, {self.delay_between_cells}s between cells")
        print(f"📄 Note: Printify will fetch multiple pages per day for accurate COGS")
        
        # Test all connections first
        print(f"\n" + "="*60)
        if not self.test_all_connections():
            print("❌ Some API connections failed. Please fix them before continuing.")
            return False
        
        print(f"\n" + "="*60)
        print("🚀 All connections successful! Starting backfill...")
        
        current_date = start_date
        successful_days = 0
        
        start_time = time.time()
        
        while current_date <= end_date:
            if self.update_single_day(current_date):
                successful_days += 1
            
            current_date += timedelta(days=1)
            
            # Progress update every 5 days
            days_completed = (current_date - start_date).days
            if days_completed % 5 == 0 and days_completed > 0:
                elapsed_time = time.time() - start_time
                avg_time_per_day = elapsed_time / days_completed
                remaining_days = total_days - days_completed
                estimated_remaining = (remaining_days * avg_time_per_day) / 60
                
                print(f"\n📊 Progress Update:")
                print(f"   Completed: {days_completed}/{total_days} days ({days_completed/total_days*100:.1f}%)")
                print(f"   Successful: {successful_days}/{days_completed} days")
                print(f"   Estimated time remaining: {estimated_remaining:.1f} minutes")
        
        total_time = time.time() - start_time
        
        print(f"\n🎉 COMPLETE BACKFILL FINISHED!")
        print(f"✅ Successfully processed {successful_days}/{total_days} days")
        print(f"⏱️  Total time: {total_time/60:.1f} minutes")
        print(f"📊 Total metrics populated: ~{successful_days * 7}")
        
        if successful_days < total_days:
            failed_days = total_days - successful_days
            print(f"⚠️  {failed_days} days had issues - check your Google Sheet for any missing data")
        else:
            print(f"🏆 Perfect run! All days completed successfully.")
            print(f"📋 Your P&L sheet now has complete automated data!")
        
        return successful_days == total_days

def main():
    """Main function"""
    backfill = CompleteBackfill()
    
    print("🚀 COMPLETE P&L BACKFILL TOOL")
    print("="*60)
    print("📋 This will populate your Google Sheet with:")
    print("   • Shopify sales data (4 metrics)")
    print("   • Meta advertising data (1 metric)")  
    print("   • Printify costs/COGS (1 metric)")
    print("   • Calculated fees (1 metric)")
    print("="*60)
    
    # Date range
    start_date = datetime(2025, 5, 2)
    end_date = datetime.now() - timedelta(days=1)
    
    total_days = (end_date - start_date).days + 1
    print(f"📅 Will backfill from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
    print(f"📊 Total days: {total_days}")
    print(f"📊 Total API calls: ~{total_days * 3} (across 3 APIs)")
    print(f"📊 Total sheet updates: ~{total_days * 7} cells")
    
    # Confirm before starting
    print(f"\n⚠️  This will OVERWRITE any existing data in these date ranges!")
    response = input("Press Enter to start the complete backfill, or 'q' to quit: ").strip().lower()
    if response == 'q':
        print("👋 Backfill cancelled")
        return
    
    # Run complete backfill
    success = backfill.run_complete_backfill(start_date, end_date)
    
    if success:
        print(f"\n🎉🎉🎉 MISSION ACCOMPLISHED! 🎉🎉🎉")
        print(f"Your P&L automation is now complete!")
    else:
        print(f"\n⚠️  Backfill completed with some issues. Check your sheet.")

if __name__ == "__main__":
    main()
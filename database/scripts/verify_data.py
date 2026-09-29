"""
Data Verification Script
Verifies data quality and completeness in the NWIS database
"""

import sys
import os
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.db_config import get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataVerifier:
    """Verify database data quality and completeness"""
    
    def __init__(self):
        self.db = get_db()
        self.issues = []
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def check_table_counts(self) -> dict:
        """Check record counts for all tables"""
        self.print_header("TABLE RECORD COUNTS")
        
        tables = {
            'wells': 'Well Master Data',
            'telemetry_data': 'Time-Series Telemetry',
            'daily_operations': 'Daily Operations Reports',
            'equipment': 'Equipment Records',
            'npt_events': 'NPT Events',
            'kpi_metrics': 'Calculated KPIs'
        }
        
        counts = {}
        for table, description in tables.items():
            try:
                count = self.db.get_table_count(table)
                counts[table] = count
                
                status = "✓" if count > 0 else "⚠"
                print(f"  {status} {description:35s} {count:>10,} records")
                
                if count == 0:
                    self.issues.append(f"Table '{table}' is empty")
                    
            except Exception as e:
                counts[table] = 0
                print(f"  ✗ {description:35s} Error: {e}")
                self.issues.append(f"Cannot access table '{table}': {e}")
        
        return counts
    
    def check_data_quality(self):
        """Check data quality metrics"""
        self.print_header("DATA QUALITY CHECKS")
        
        checks = [
            ("Telemetry timestamps", "SELECT COUNT(*) FROM telemetry_data WHERE timestamp IS NULL"),
            ("Null bit depths", "SELECT COUNT(*) FROM telemetry_data WHERE bit_depth IS NULL"),
            ("Negative ROP values", "SELECT COUNT(*) FROM telemetry_data WHERE rate_of_penetration < 0"),
            ("Missing well references", "SELECT COUNT(*) FROM telemetry_data WHERE well_id NOT IN (SELECT well_id FROM wells)"),
            ("Duplicate timestamps", "SELECT COUNT(*) - COUNT(DISTINCT (well_id, timestamp)) FROM telemetry_data"),
        ]
        
        for check_name, query in checks:
            try:
                result = self.db.execute_query(query, fetch=True)
                count = result[0]['count'] if result else 0
                
                status = "✓" if count == 0 else "⚠"
                print(f"  {status} {check_name:40s} {count:>10,} issues")
                
                if count > 0:
                    self.issues.append(f"{check_name}: {count} issues found")
                    
            except Exception as e:
                print(f"  ✗ {check_name:40s} Error: {e}")
    
    def check_date_ranges(self):
        """Check date ranges in data"""
        self.print_header("DATE RANGE ANALYSIS")
        
        try:
            # Telemetry date range
            query = """
                SELECT 
                    MIN(timestamp) as min_date,
                    MAX(timestamp) as max_date,
                    MAX(timestamp) - MIN(timestamp) as duration
                FROM telemetry_data
            """
            result = self.db.execute_query(query, fetch=True)
            
            if result and result[0]['min_date']:
                row = result[0]
                print(f"  Telemetry Data Range:")
                print(f"    Start: {row['min_date']}")
                print(f"    End:   {row['max_date']}")
                print(f"    Duration: {row['duration']}")
            else:
                print(f"  ⚠ No telemetry data found")
                
        except Exception as e:
            print(f"  ✗ Error checking date ranges: {e}")
        
        try:
            # Daily operations date range
            query = """
                SELECT 
                    MIN(report_date) as min_date,
                    MAX(report_date) as max_date,
                    COUNT(*) as report_count
                FROM daily_operations
            """
            result = self.db.execute_query(query, fetch=True)
            
            if result and result[0]['min_date']:
                row = result[0]
                print(f"\n  Daily Operations:")
                print(f"    Start: {row['min_date']}")
                print(f"    End:   {row['max_date']}")
                print(f"    Reports: {row['report_count']}")
            else:
                print(f"\n  ⚠ No daily operations found")
                
        except Exception as e:
            print(f"  ✗ Error checking operations: {e}")
    
    def check_sample_data(self):
        """Display sample records"""
        self.print_header("SAMPLE DATA")
        
        try:
            # Latest telemetry
            query = """
                SELECT 
                    w.well_name,
                    t.timestamp,
                    t.bit_depth,
                    t.rate_of_penetration,
                    t.weight_on_bit
                FROM telemetry_data t
                JOIN wells w ON t.well_id = w.well_id
                ORDER BY t.timestamp DESC
                LIMIT 5
            """
            result = self.db.execute_query(query, fetch=True)
            
            if result:
                print("\n  Latest Telemetry Records:")
                print(f"    {'Well':<15} {'Timestamp':<20} {'Depth':<10} {'ROP':<10} {'WOB':<10}")
                print("    " + "-" * 65)
                
                for row in result:
                    well = row['well_name'] or 'N/A'
                    timestamp = str(row['timestamp']) if row['timestamp'] else 'N/A'
                    depth = f"{row['bit_depth']:.2f}" if row['bit_depth'] else 'N/A'
                    rop = f"{row['rate_of_penetration']:.2f}" if row['rate_of_penetration'] else 'N/A'
                    wob = f"{row['weight_on_bit']:.2f}" if row['weight_on_bit'] else 'N/A'
                    
                    print(f"    {well:<15} {timestamp:<20} {depth:<10} {rop:<10} {wob:<10}")
            else:
                print("\n  ⚠ No telemetry data found")
                
        except Exception as e:
            print(f"\n  ✗ Error fetching sample data: {e}")
    
    def check_statistics(self):
        """Calculate and display statistics"""
        self.print_header("DATA STATISTICS")
        
        try:
            query = """
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT well_id) as unique_wells,
                    AVG(bit_depth) as avg_depth,
                    AVG(rate_of_penetration) as avg_rop,
                    AVG(weight_on_bit) as avg_wob
                FROM telemetry_data
                WHERE bit_depth IS NOT NULL
            """
            result = self.db.execute_query(query, fetch=True)
            
            if result:
                row = result[0]
                print(f"  Total Records:    {row['total_records']:>15,}")
                print(f"  Unique Wells:     {row['unique_wells']:>15,}")
                print(f"  Average Depth:    {row['avg_depth']:>15.2f} ft" if row['avg_depth'] else "  Average Depth:    N/A")
                print(f"  Average ROP:      {row['avg_rop']:>15.2f} ft/hr" if row['avg_rop'] else "  Average ROP:      N/A")
                print(f"  Average WOB:      {row['avg_wob']:>15.2f} klbs" if row['avg_wob'] else "  Average WOB:      N/A")
                
        except Exception as e:
            print(f"  ✗ Error calculating statistics: {e}")
    
    def generate_summary(self):
        """Generate verification summary"""
        self.print_header("VERIFICATION SUMMARY")
        
        if not self.issues:
            print("\n  ✓ All checks passed!")
            print("  ✓ Database is ready for use")
        else:
            print(f"\n  ⚠ Found {len(self.issues)} issues:")
            for i, issue in enumerate(self.issues, 1):
                print(f"    {i}. {issue}")
            
            print("\n  Recommendations:")
            print("    • Review data loading logs")
            print("    • Re-run failed loaders if needed")
            print("    • Check data file integrity")
        
        print("\n" + "=" * 70)
    
    def run(self):
        """Run all verification checks"""
        print("\n" + "=" * 70)
        print("  NWIS DATABASE VERIFICATION")
        print("=" * 70)
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all checks
        self.check_table_counts()
        self.check_data_quality()
        self.check_date_ranges()
        self.check_sample_data()
        self.check_statistics()
        self.generate_summary()
        
        return len(self.issues) == 0


def main():
    """Main execution function"""
    try:
        verifier = DataVerifier()
        success = verifier.run()
        
        return success
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

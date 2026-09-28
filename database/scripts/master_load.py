"""
Master Data Loading Script
Orchestrates the complete data loading process for NWIS database
"""

import sys
import os
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.db_config import get_db, initialize_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MasterDataLoader:
    """Master orchestrator for all data loading operations"""
    
    def __init__(self):
        self.db = get_db()
        self.start_time = None
        self.results = {}
        
    def print_header(self, title: str):
        """Print formatted header"""
        logger.info("\n" + "=" * 70)
        logger.info(f"  {title}")
        logger.info("=" * 70)
    
    def print_step(self, step_num: int, title: str):
        """Print step header"""
        logger.info(f"\n{'─' * 70}")
        logger.info(f"  Step {step_num}: {title}")
        logger.info(f"{'─' * 70}")
    
    def check_database_connection(self) -> bool:
        """Check if database is accessible"""
        try:
            if self.db.test_connection():
                logger.info("✓ Database connection successful")
                return True
            else:
                logger.error("✗ Database connection failed")
                return False
        except Exception as e:
            logger.error(f"✗ Database connection error: {e}")
            return False
    
    def initialize_schema(self, schema_file: str) -> bool:
        """Initialize database schema"""
        try:
            if os.path.exists(schema_file):
                logger.info(f"Executing schema file: {schema_file}")
                self.db.execute_script_file(schema_file)
                logger.info("✓ Schema initialized successfully")
                return True
            else:
                logger.error(f"✗ Schema file not found: {schema_file}")
                return False
        except Exception as e:
            logger.error(f"✗ Schema initialization failed: {e}")
            return False
    
    def create_sample_wells(self) -> bool:
        """Create sample well records"""
        try:
            wells_data = [
                ("16A(78)-32", "Production", "Completed", "2020-10-25", "2021-03-09"),
                ("56-32", "Production", "Completed", "2021-02-05", "2021-03-09"),
                ("78B-32", "Production", "Completed", None, None),
                ("16-32", "Production", "Completed", None, None),
                ("56A-32", "Production", "Completed", None, None),
            ]
            
            for well_name, well_type, status, spud_date, completion_date in wells_data:
                try:
                    insert_query = """
                        INSERT INTO wells (well_name, well_type, well_status, spud_date, completion_date)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (well_name) DO NOTHING
                    """
                    self.db.execute_query(insert_query, (well_name, well_type, status, spud_date, completion_date))
                    logger.info(f"  ✓ Created/verified well: {well_name}")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not create well {well_name}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"✗ Error creating wells: {e}")
            return False
    
    def load_telemetry_data(self) -> bool:
        """Load CSV telemetry data"""
        try:
            # Import and run telemetry loader
            from load_csv_telemetry import TelemetryLoader
            
            csv_file = r"c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\data\raw\16A(78)-32_time_data_10s_intervals_standard.csv"
            
            if not os.path.exists(csv_file):
                logger.warning(f"⚠ CSV file not found: {csv_file}")
                return False
            
            loader = TelemetryLoader(csv_file, "16A(78)-32")
            loader.create_well_if_not_exists()
            
            count = loader.load_csv_data(chunk_size=5000)
            self.results['telemetry_records'] = count
            
            logger.info(f"✓ Loaded {count} telemetry records")
            return True
            
        except Exception as e:
            logger.error(f"✗ Telemetry loading failed: {e}")
            return False
    
    def load_pdf_reports(self) -> bool:
        """Load PDF daily reports"""
        try:
            from load_pdf_reports import PDFReportLoader
            
            pdf_dir = r"c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\data\raw\well_1\56-32 Daily Drilling Reports"
            
            if not os.path.exists(pdf_dir):
                logger.warning(f"⚠ PDF directory not found: {pdf_dir}")
                return False
            
            loader = PDFReportLoader(pdf_dir, "56-32")
            
            if loader.get_well_id():
                count = loader.load_all_reports()
                self.results['daily_reports'] = count
                logger.info(f"✓ Loaded {count} daily reports")
                return True
            else:
                logger.warning("⚠ Could not find well in database")
                return False
                
        except Exception as e:
            logger.error(f"✗ PDF loading failed: {e}")
            return False
    
    def calculate_initial_kpis(self) -> bool:
        """Calculate initial KPIs from loaded data"""
        try:
            # Simple KPI calculation for demonstration
            query = """
                INSERT INTO kpi_metrics (
                    well_id,
                    calculation_date,
                    avg_rop,
                    total_footage
                )
                SELECT 
                    well_id,
                    DATE(timestamp) as calc_date,
                    AVG(rate_of_penetration) as avg_rop,
                    MAX(bit_depth) - MIN(bit_depth) as footage
                FROM telemetry_data
                WHERE rate_of_penetration IS NOT NULL
                GROUP BY well_id, DATE(timestamp)
                ON CONFLICT (well_id, calculation_date) DO UPDATE
                SET avg_rop = EXCLUDED.avg_rop,
                    total_footage = EXCLUDED.total_footage
            """
            
            self.db.execute_query(query)
            logger.info("✓ Calculated initial KPIs")
            return True
            
        except Exception as e:
            logger.error(f"✗ KPI calculation failed: {e}")
            return False
    
    def verify_data_loading(self) -> dict:
        """Verify all data was loaded correctly"""
        verification = {}
        
        tables = [
            'wells',
            'telemetry_data',
            'daily_operations',
            'equipment',
            'npt_events',
            'kpi_metrics'
        ]
        
        logger.info("\nData Verification:")
        logger.info(f"{'─' * 70}")
        
        for table in tables:
            try:
                count = self.db.get_table_count(table)
                verification[table] = count
                status = "✓" if count > 0 else "⚠"
                logger.info(f"  {status} {table:30s} {count:>10,} records")
            except Exception as e:
                verification[table] = 0
                logger.warning(f"  ✗ {table:30s} Error: {e}")
        
        return verification
    
    def generate_summary_report(self):
        """Generate final summary report"""
        self.print_header("DATA LOADING SUMMARY")
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        logger.info(f"\n📊 Results:")
        logger.info(f"  • Telemetry records:   {self.results.get('telemetry_records', 0):>10,}")
        logger.info(f"  • Daily reports:       {self.results.get('daily_reports', 0):>10,}")
        logger.info(f"  • KPI calculations:    {'Completed' if self.results.get('kpis_calculated') else 'Skipped'}")
        
        logger.info(f"\n⏱️  Processing Time: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        
        verification = self.verify_data_loading()
        
        total_records = sum(verification.values())
        logger.info(f"\n📈 Total Records in Database: {total_records:,}")
        
        logger.info("\n" + "=" * 70)
        logger.info("  ✓ Database setup and data loading complete!")
        logger.info("=" * 70)
        
        logger.info("\n🚀 Next Steps:")
        logger.info("  1. Verify data: python -m database.scripts.verify_data")
        logger.info("  2. Start backend API server")
        logger.info("  3. Start frontend dashboard")
    
    def run(self, schema_file: str):
        """Run complete data loading pipeline"""
        self.start_time = datetime.now()
        
        self.print_header("NWIS DATABASE INITIALIZATION & DATA LOADING")
        
        # Step 1: Check connection
        self.print_step(1, "Database Connection")
        if not self.check_database_connection():
            logger.error("Cannot proceed without database connection")
            return False
        
        # Step 2: Initialize schema
        self.print_step(2, "Initialize Database Schema")
        if not self.initialize_schema(schema_file):
            logger.error("Schema initialization failed")
            return False
        
        # Step 3: Create sample wells
        self.print_step(3, "Create Sample Well Records")
        self.create_sample_wells()
        
        # Step 4: Load telemetry data
        self.print_step(4, "Load Telemetry Data (CSV)")
        telemetry_loaded = self.load_telemetry_data()
        
        # Step 5: Load PDF reports
        self.print_step(5, "Load Daily Reports (PDF)")
        pdf_loaded = self.load_pdf_reports()
        
        # Step 6: Calculate KPIs
        if telemetry_loaded:
            self.print_step(6, "Calculate Initial KPIs")
            self.results['kpis_calculated'] = self.calculate_initial_kpis()
        
        # Step 7: Generate summary
        self.generate_summary_report()
        
        return True


def main():
    """Main entry point"""
    try:
        # Schema file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_file = os.path.join(base_dir, "schema", "create_tables.sql")
        
        # Run master loader
        loader = MasterDataLoader()
        success = loader.run(schema_file)
        
        return success
        
    except KeyboardInterrupt:
        logger.warning("\n\n⚠ Process interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\n✗ Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

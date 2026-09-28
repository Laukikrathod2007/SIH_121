"""
Load telemetry data from CSV file into PostgreSQL database
Handles the 16A(78)-32_time_data_10s_intervals_standard.csv file
"""

import sys
import os
import pandas as pd
import numpy as np
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


class TelemetryLoader:
    """Load CSV telemetry data into database"""
    
    def __init__(self, csv_file: str, well_name: str = "16A(78)-32"):
        self.csv_file = csv_file
        self.well_name = well_name
        self.db = get_db()
        self.well_id = None
        
    def create_well_if_not_exists(self):
        """Create well record if it doesn't exist"""
        try:
            # Check if well exists
            query = "SELECT well_id FROM wells WHERE well_name = %s"
            result = self.db.execute_query(query, (self.well_name,), fetch=True)
            
            if result:
                self.well_id = result[0]['well_id']
                logger.info(f"Well '{self.well_name}' exists with ID: {self.well_id}")
            else:
                # Insert new well
                insert_query = """
                    INSERT INTO wells (well_name, well_type, well_status)
                    VALUES (%s, %s, %s)
                    RETURNING well_id
                """
                result = self.db.execute_query(
                    insert_query,
                    (self.well_name, 'Production', 'Completed'),
                    fetch=True
                )
                self.well_id = result[0]['well_id']
                logger.info(f"Created well '{self.well_name}' with ID: {self.well_id}")
                
        except Exception as e:
            logger.error(f"Error creating well: {e}")
            raise
    
    def clean_numeric_value(self, value):
        """Clean and convert numeric values"""
        if pd.isna(value) or value == '' or value == ' ':
            return None
        try:
            num_val = float(value)
            # Handle extreme values or zeros that might be null indicators
            if abs(num_val) < 1e-10:
                return None
            return num_val
        except (ValueError, TypeError):
            return None
    
    def clean_boolean_value(self, value):
        """Clean boolean values"""
        if pd.isna(value) or value == '':
            return None
        try:
            num_val = float(value)
            return num_val > 0
        except:
            return None
    
    def load_csv_data(self, chunk_size: int = 10000):
        """Load CSV data in chunks"""
        try:
            logger.info(f"Loading CSV file: {self.csv_file}")
            
            if not os.path.exists(self.csv_file):
                raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
            
            # Read CSV file (skip the units row)
            df = pd.read_csv(self.csv_file, skiprows=[1], low_memory=False)
            logger.info(f"Loaded {len(df)} rows from CSV")
            logger.info(f"Columns: {len(df.columns)}")
            
            # Convert date column
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            # Remove rows with invalid dates
            df = df.dropna(subset=['Date'])
            logger.info(f"After date filtering: {len(df)} rows")
            
            # Process in chunks
            total_rows = len(df)
            inserted_count = 0
            
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk = df.iloc[start_idx:end_idx]
                
                inserted = self.insert_chunk(chunk)
                inserted_count += inserted
                
                logger.info(
                    f"Processed {end_idx}/{total_rows} rows "
                    f"({(end_idx/total_rows)*100:.1f}%) - "
                    f"Inserted: {inserted_count}"
                )
            
            logger.info(f"Total rows inserted: {inserted_count}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            raise
    
    def insert_chunk(self, chunk_df):
        """Insert chunk of data into database"""
        try:
            # Prepare insert query
            insert_query = """
                INSERT INTO telemetry_data (
                    well_id, timestamp, bit_depth, hole_depth, block_position,
                    weight_on_bit, rate_of_penetration, rotary_rpm, top_drive_torque,
                    pump_pressure, flow_in, return_flow, spm,
                    hookload, hookload_string, inclination, azimuth,
                    differential_pressure, downhole_torque, motor_rpm,
                    gamma_ray, gas_co2, gas_h2s,
                    mud_temperature, tool_temperature,
                    mechanical_specific_energy, mse_downhole, mse_surface,
                    rig_state, rig_mode, on_bottom, stick_slip,
                    bit_diameter, running_speed_down, running_speed_up,
                    dogleg_severity
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            # Prepare data tuples
            data_tuples = []
            for _, row in chunk_df.iterrows():
                try:
                    data_tuple = (
                        self.well_id,
                        row.get('Date'),
                        self.clean_numeric_value(row.get('Bit Depth')),
                        self.clean_numeric_value(row.get('Depth Hole Total Vertical Depth')),
                        self.clean_numeric_value(row.get('Block Position')),
                        self.clean_numeric_value(row.get('Weight on Bit')),
                        self.clean_numeric_value(row.get('Rate of Penetration (Depth/Hour)')),
                        self.clean_numeric_value(row.get('Bit Revolutions per Minute')),
                        self.clean_numeric_value(row.get('Top Drive Torque')),
                        self.clean_numeric_value(row.get('Pump Pressure')),
                        self.clean_numeric_value(row.get('Flow In')),
                        self.clean_numeric_value(row.get('Return Flow')),
                        self.clean_numeric_value(row.get('Total Strokes per Minute')),
                        self.clean_numeric_value(row.get('Hookload')),
                        self.clean_numeric_value(row.get('Hookload String')),
                        self.clean_numeric_value(row.get('Inclination')),
                        self.clean_numeric_value(row.get('Azimuth')),
                        self.clean_numeric_value(row.get('Differential Pressure')),
                        self.clean_numeric_value(row.get('Downhole Torque')),
                        self.clean_numeric_value(row.get('Mud Motor Revolutions per Minute')),
                        self.clean_numeric_value(row.get('Gamma Measured while Drilling')),
                        self.clean_numeric_value(row.get('Gas Carbon Dioxide')),
                        self.clean_numeric_value(row.get('H2S 01')),
                        self.clean_numeric_value(row.get('Mud Temperature')),
                        self.clean_numeric_value(row.get('Tool Temperature')),
                        self.clean_numeric_value(row.get('Mechanical Specific Energy')),
                        self.clean_numeric_value(row.get('Mechanical Specific Energy - Downhole')),
                        self.clean_numeric_value(row.get('Mechanical Specific Energy - Surface')),
                        str(row.get('Rig State', ''))[:50] if pd.notna(row.get('Rig State')) else None,
                        str(row.get('Rig Mode', ''))[:50] if pd.notna(row.get('Rig Mode')) else None,
                        self.clean_boolean_value(row.get('On Bottom')),
                        self.clean_numeric_value(row.get('Stick Slip')),
                        self.clean_numeric_value(row.get('Bit Diameter')),
                        self.clean_numeric_value(row.get('Running Speed Down')),
                        self.clean_numeric_value(row.get('Running Speed Up')),
                        self.clean_numeric_value(row.get('Dog-Leg Severity Measured while Drilling'))
                    )
                    data_tuples.append(data_tuple)
                except Exception as e:
                    logger.warning(f"Error preparing row: {e}")
                    continue
            
            if data_tuples:
                row_count = self.db.execute_many(insert_query, data_tuples)
                return len(data_tuples)
            return 0
            
        except Exception as e:
            logger.error(f"Error inserting chunk: {e}")
            raise


def main():
    """Main execution function"""
    try:
        # Configuration
        CSV_FILE = r"c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\data\raw\16A(78)-32_time_data_10s_intervals_standard.csv"
        WELL_NAME = "16A(78)-32"
        
        logger.info("=" * 60)
        logger.info("Starting Telemetry Data Loading Process")
        logger.info("=" * 60)
        
        # Initialize loader
        loader = TelemetryLoader(CSV_FILE, WELL_NAME)
        
        # Create well record
        loader.create_well_if_not_exists()
        
        # Load data
        start_time = datetime.now()
        inserted_count = loader.load_csv_data(chunk_size=5000)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("Loading Complete!")
        logger.info(f"Total records inserted: {inserted_count}")
        logger.info(f"Time taken: {duration:.2f} seconds")
        logger.info(f"Average rate: {inserted_count/duration:.0f} records/second")
        logger.info("=" * 60)
        
        # Verify data
        db = get_db()
        count = db.get_table_count('telemetry_data')
        logger.info(f"Verification: telemetry_data table has {count} total records")
        
        return True
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

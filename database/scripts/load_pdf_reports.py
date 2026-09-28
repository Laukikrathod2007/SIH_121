"""
Extract data from PDF daily drilling reports and load into database
"""

import sys
import os
import re
from datetime import datetime
from pathlib import Path
import logging

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not installed. Installing...")
    os.system("pip install PyPDF2")
    import PyPDF2

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.db_config import get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFReportLoader:
    """Extract and load data from daily drilling report PDFs"""
    
    def __init__(self, pdf_directory: str, well_name: str):
        self.pdf_directory = pdf_directory
        self.well_name = well_name
        self.db = get_db()
        self.well_id = None
        
    def get_well_id(self):
        """Get well_id from database"""
        try:
            query = "SELECT well_id FROM wells WHERE well_name = %s"
            result = self.db.execute_query(query, (self.well_name,), fetch=True)
            
            if result:
                self.well_id = result[0]['well_id']
                logger.info(f"Found well ID: {self.well_id}")
                return True
            else:
                logger.error(f"Well '{self.well_name}' not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Error getting well ID: {e}")
            return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            return ""
    
    def parse_report_date(self, filename: str) -> datetime:
        """Extract report date from filename"""
        # Format: DailyReportDetailRpt_YYMMDDHHMMSS.pdf
        try:
            match = re.search(r'(\d{6})\d{6}', filename)
            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, '%y%m%d')
        except:
            pass
        return None
    
    def extract_depth_info(self, text: str) -> dict:
        """Extract depth information from report text"""
        depth_info = {}
        
        # Try to extract depth values (flexible patterns)
        patterns = {
            'start_depth': r'(?:Start|Begin|From)\s*Depth[:\s]+(\d+(?:\.\d+)?)',
            'end_depth': r'(?:End|Final|To)\s*Depth[:\s]+(\d+(?:\.\d+)?)',
            'depth_drilled': r'(?:Drilled|Footage)[:\s]+(\d+(?:\.\d+)?)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    depth_info[key] = float(match.group(1))
                except:
                    pass
        
        return depth_info
    
    def extract_time_breakdown(self, text: str) -> dict:
        """Extract time breakdown from report"""
        time_info = {}
        
        patterns = {
            'drilling_time': r'(?:Drilling|Rotating)[:\s]+(\d+(?:\.\d+)?)',
            'trip_time': r'Trip[:\s]+(\d+(?:\.\d+)?)',
            'connection_time': r'Connection[:\s]+(\d+(?:\.\d+)?)',
            'npt_time': r'(?:NPT|Non[- ]Productive)[:\s]+(\d+(?:\.\d+)?)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    time_info[key] = float(match.group(1))
                except:
                    pass
        
        return time_info
    
    def process_pdf_report(self, pdf_path: str) -> dict:
        """Process a single PDF report"""
        try:
            filename = os.path.basename(pdf_path)
            logger.info(f"Processing: {filename}")
            
            # Extract date from filename
            report_date = self.parse_report_date(filename)
            if not report_date:
                logger.warning(f"Could not parse date from: {filename}")
                return None
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                logger.warning(f"No text extracted from: {filename}")
                return None
            
            # Extract data
            depth_info = self.extract_depth_info(text)
            time_info = self.extract_time_breakdown(text)
            
            # Calculate depth drilled if possible
            if 'start_depth' in depth_info and 'end_depth' in depth_info:
                depth_info['depth_drilled'] = depth_info['end_depth'] - depth_info['start_depth']
            
            # Build report data
            report_data = {
                'well_id': self.well_id,
                'report_date': report_date,
                'start_depth': depth_info.get('start_depth'),
                'end_depth': depth_info.get('end_depth'),
                'depth_drilled': depth_info.get('depth_drilled'),
                'drilling_time': time_info.get('drilling_time'),
                'trip_time': time_info.get('trip_time'),
                'connection_time': time_info.get('connection_time'),
                'npt_time': time_info.get('npt_time'),
                'operations_summary': text[:500]  # First 500 chars as summary
            }
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return None
    
    def insert_daily_operation(self, report_data: dict):
        """Insert daily operation record"""
        try:
            insert_query = """
                INSERT INTO daily_operations (
                    well_id, report_date, start_depth, end_depth, depth_drilled,
                    drilling_time, trip_time, connection_time, npt_time,
                    operations_summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (well_id, report_date, shift) DO NOTHING
            """
            
            params = (
                report_data['well_id'],
                report_data['report_date'],
                report_data.get('start_depth'),
                report_data.get('end_depth'),
                report_data.get('depth_drilled'),
                report_data.get('drilling_time'),
                report_data.get('trip_time'),
                report_data.get('connection_time'),
                report_data.get('npt_time'),
                report_data.get('operations_summary')
            )
            
            self.db.execute_query(insert_query, params)
            return True
            
        except Exception as e:
            logger.error(f"Error inserting daily operation: {e}")
            return False
    
    def load_all_reports(self):
        """Load all PDF reports from directory"""
        try:
            pdf_files = list(Path(self.pdf_directory).glob('*.pdf'))
            logger.info(f"Found {len(pdf_files)} PDF files")
            
            processed = 0
            inserted = 0
            
            for pdf_file in pdf_files:
                report_data = self.process_pdf_report(str(pdf_file))
                if report_data:
                    if self.insert_daily_operation(report_data):
                        inserted += 1
                    processed += 1
            
            logger.info(f"Processed: {processed}, Inserted: {inserted}")
            return inserted
            
        except Exception as e:
            logger.error(f"Error loading reports: {e}")
            return 0


def main():
    """Main execution function"""
    try:
        # Configuration
        WELL_DIRECTORIES = {
            "56-32": r"c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\data\raw\well_1\56-32 Daily Drilling Reports",
        }
        
        logger.info("=" * 60)
        logger.info("Starting PDF Reports Loading Process")
        logger.info("=" * 60)
        
        total_inserted = 0
        
        for well_name, pdf_dir in WELL_DIRECTORIES.items():
            if os.path.exists(pdf_dir):
                logger.info(f"\nProcessing well: {well_name}")
                logger.info(f"Directory: {pdf_dir}")
                
                loader = PDFReportLoader(pdf_dir, well_name)
                
                if loader.get_well_id():
                    inserted = loader.load_all_reports()
                    total_inserted += inserted
                else:
                    logger.warning(f"Skipping well {well_name} - not found in database")
            else:
                logger.warning(f"Directory not found: {pdf_dir}")
        
        logger.info("=" * 60)
        logger.info(f"Total daily operation records inserted: {total_inserted}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

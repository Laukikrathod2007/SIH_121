"""
Database Configuration for NWIS
Handles PostgreSQL connection settings and utilities
"""

import os
from dataclasses import dataclass
from typing import Optional
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "nwis_db")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")  # Will be loaded from .env
    min_connections: int = 1
    max_connections: int = 10


class DatabaseConnection:
    """Manage PostgreSQL database connections with connection pooling"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._pool = None
        
    def initialize_pool(self):
        """Initialize connection pool"""
        try:
            self._pool = psycopg2.pool.SimpleConnectionPool(
                self.config.min_connections,
                self.config.max_connections,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            logger.info(f"Connection pool created for database: {self.config.database}")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        if self._pool is None:
            self.initialize_pool()
        return self._pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool"""
        if self._pool:
            self._pool.putconn(conn)
    
    def close_all_connections(self):
        """Close all connections in pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("All connections closed")
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute a query and optionally fetch results"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                    conn.commit()
                    return result
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query execution error: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_many(self, query: str, data: list):
        """Execute batch insert/update"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.executemany(query, data)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch execution error: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_script_file(self, filepath: str):
        """Execute SQL script from file"""
        conn = None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                script = f.read()
            
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(script)
                conn.commit()
            logger.info(f"Successfully executed script: {filepath}")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Script execution error: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def create_database(self, db_name: str):
        """Create database if it doesn't exist"""
        # Connect to default postgres database
        temp_config = DatabaseConfig(
            host=self.config.host,
            port=self.config.port,
            database='postgres',
            user=self.config.user,
            password=self.config.password
        )
        
        try:
            conn = psycopg2.connect(
                host=temp_config.host,
                port=temp_config.port,
                database=temp_config.database,
                user=temp_config.user,
                password=temp_config.password
            )
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                exists = cursor.fetchone()
                
                if not exists:
                    cursor.execute(f'CREATE DATABASE {db_name}')
                    logger.info(f"Database '{db_name}' created successfully")
                else:
                    logger.info(f"Database '{db_name}' already exists")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                logger.info(f"Connected to: {version[0]}")
            self.return_connection(conn)
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query, fetch=True)
        return result[0]['count'] if result else 0
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
        """
        result = self.execute_query(query, (table_name,), fetch=True)
        return result[0]['exists'] if result else False


# Global database instance
db = DatabaseConnection()


def get_db() -> DatabaseConnection:
    """Get database instance"""
    return db


def initialize_database(schema_file: str = None):
    """Initialize database with schema"""
    try:
        # Create database if it doesn't exist
        db.create_database(db.config.database)
        
        # Test connection
        if not db.test_connection():
            raise Exception("Database connection test failed")
        
        # Execute schema file if provided
        if schema_file and os.path.exists(schema_file):
            logger.info(f"Executing schema file: {schema_file}")
            db.execute_script_file(schema_file)
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    print("Testing database connection...")
    
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="nwis_db",
        user="postgres",
        password="postgres"
    )
    
    db_test = DatabaseConnection(config)
    
    if db_test.test_connection():
        print("✓ Connection successful!")
        
        # Test query
        try:
            result = db_test.execute_query(
                "SELECT current_database(), current_user",
                fetch=True
            )
            print(f"✓ Current database: {result[0]}")
        except Exception as e:
            print(f"✗ Query test failed: {e}")
    else:
        print("✗ Connection failed!")

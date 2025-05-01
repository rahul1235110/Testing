import os
import json
import pandas as pd
from datetime import datetime
import streamlit as st
import sqlite3

# Try to import psycopg2, but handle the case when it's not available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    print("psycopg2 not available, PostgreSQL support disabled")
    PSYCOPG2_AVAILABLE = False

class Database:
    """Database class that can use either PostgreSQL or SQLite."""
    
    def __init__(self, sqlite_db_path="crop_irrigation.db"):
        """Initialize the database connection."""
        self.sqlite_db_path = sqlite_db_path
        
        # Check if PostgreSQL is available and DATABASE_URL is set
        self.use_postgres = PSYCOPG2_AVAILABLE and 'DATABASE_URL' in os.environ
        
        if self.use_postgres:
            # Create connection pool for PostgreSQL
            try:
                self.pool = pool.ThreadedConnectionPool(
                    1, 10,  # min/max connections
                    os.environ.get("DATABASE_URL")
                )
                # Create tables if they don't exist
                self.create_tables()
            except Exception as e:
                st.error(f"Could not connect to PostgreSQL: {str(e)}")
                self.use_postgres = False
                # Fall back to SQLite
        
        if not self.use_postgres:
            # Fallback to SQLite
            self.create_tables()
    
    def get_connection(self):
        """Create and return a database connection."""
        if self.use_postgres:
            try:
                conn = self.pool.getconn()
                return conn
            except Exception as e:
                st.error(f"Error getting PostgreSQL connection: {str(e)}")
                return None
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def release_connection(self, conn):
        """Release a connection back to the pool."""
        if self.use_postgres and conn:
            self.pool.putconn(conn)
    
    def create_tables(self):
        """Create necessary database tables if they don't exist."""
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            # PostgreSQL tables
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create field_data table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS field_data (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                lat FLOAT NOT NULL,
                lon FLOAT NOT NULL,
                field_capacity FLOAT NOT NULL,
                crop_type VARCHAR(50) NOT NULL,
                sowing_date VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create irrigation_records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS irrigation_records (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                date VARCHAR(20) NOT NULL,
                et0 FLOAT,
                aet FLOAT,
                irrigation_required FLOAT,
                adjusted_irrigation FLOAT,
                soil_moisture FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (field_id) REFERENCES field_data (id)
            )
            ''')
            
        else:
            # SQLite tables
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create field_data table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS field_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                field_capacity REAL NOT NULL,
                crop_type TEXT NOT NULL,
                sowing_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create irrigation_records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS irrigation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                et0 REAL,
                aet REAL,
                irrigation_required REAL,
                adjusted_irrigation REAL,
                soil_moisture REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (field_id) REFERENCES field_data (id)
            )
            ''')
        
        conn.commit()
        
        if self.use_postgres:
            self.release_connection(conn)
        else:
            conn.close()
    
    def add_user(self, username, email, password):
        """Add a new user to the database."""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        success = False  # Default value in case of error
        try:
            if self.use_postgres:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                    (username, email, password)
                )
                conn.commit()
                success = True
            else:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                    (username, email, password)
                )
                conn.commit()
                success = True
        except Exception as e:
            # Check if it's an integrity error (username or email already exists)
            if isinstance(e, sqlite3.IntegrityError) or \
               (PSYCOPG2_AVAILABLE and isinstance(e, psycopg2.IntegrityError)) or \
               ('duplicate key' in str(e).lower()):
                # Username or email already exists
                success = False
        finally:
            if self.use_postgres:
                self.release_connection(conn)
            else:
                conn.close()
        
        return success
    
    def get_user_by_username(self, username):
        """Retrieve user by username."""
        conn = self.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            self.release_connection(conn)
            
            if user:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, user))
            return None
        else:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            return None
    
    def get_user_by_email(self, email):
        """Retrieve user by email."""
        conn = self.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            self.release_connection(conn)
            
            if user:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, user))
            return None
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            return None
    
    def save_field_data(self, user_id, lat, lon, field_capacity, crop_type, sowing_date):
        """Save or update field data for a user."""
        conn = self.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        # Check if user already has field data
        if self.use_postgres:
            cursor.execute(
                "SELECT id FROM field_data WHERE user_id = %s", 
                (user_id,)
            )
        else:
            cursor.execute(
                "SELECT id FROM field_data WHERE user_id = ?", 
                (user_id,)
            )
        
        existing_field = cursor.fetchone()
        
        if existing_field:
            # Update existing field data
            if self.use_postgres:
                cursor.execute(
                    """
                    UPDATE field_data 
                    SET lat = %s, lon = %s, field_capacity = %s, crop_type = %s, sowing_date = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s RETURNING id
                    """,
                    (lat, lon, field_capacity, crop_type, sowing_date, user_id)
                )
                result = cursor.fetchone()
                field_id = result[0] if result else None
            else:
                cursor.execute(
                    """
                    UPDATE field_data 
                    SET lat = ?, lon = ?, field_capacity = ?, crop_type = ?, sowing_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (lat, lon, field_capacity, crop_type, sowing_date, user_id)
                )
                field_id = existing_field['id'] if isinstance(existing_field, sqlite3.Row) else existing_field[0]
        else:
            # Insert new field data
            if self.use_postgres:
                cursor.execute(
                    """
                    INSERT INTO field_data (user_id, lat, lon, field_capacity, crop_type, sowing_date)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (user_id, lat, lon, field_capacity, crop_type, sowing_date)
                )
                result = cursor.fetchone()
                field_id = result[0] if result else None
            else:
                cursor.execute(
                    """
                    INSERT INTO field_data (user_id, lat, lon, field_capacity, crop_type, sowing_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, lat, lon, field_capacity, crop_type, sowing_date)
                )
                field_id = cursor.lastrowid
        
        conn.commit()
        
        if self.use_postgres:
            self.release_connection(conn)
        else:
            conn.close()
        
        return field_id
    
    def get_field_data(self, user_id):
        """Retrieve field data for a user."""
        conn = self.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("SELECT * FROM field_data WHERE user_id = %s", (user_id,))
            field_data = cursor.fetchone()
            self.release_connection(conn)
            
            if field_data:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, field_data))
            return None
        else:
            cursor.execute("SELECT * FROM field_data WHERE user_id = ?", (user_id,))
            field_data = cursor.fetchone()
            conn.close()
            
            if field_data:
                return dict(field_data)
            return None
    
    def save_irrigation_record(self, user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture):
        """Save irrigation calculation records."""
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute(
                """
                INSERT INTO irrigation_records 
                (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
            )
        else:
            cursor.execute(
                """
                INSERT INTO irrigation_records 
                (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
            )
        
        conn.commit()
        
        if self.use_postgres:
            self.release_connection(conn)
        else:
            conn.close()
    
    def get_irrigation_history(self, user_id, limit=10):
        """Retrieve irrigation history for a user."""
        conn = self.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute(
                """
                SELECT * FROM irrigation_records 
                WHERE user_id = %s 
                ORDER BY date DESC LIMIT %s
                """, 
                (user_id, limit)
            )
            
            records = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            history = [dict(zip(column_names, record)) for record in records]
            self.release_connection(conn)
        else:
            cursor.execute(
                """
                SELECT * FROM irrigation_records 
                WHERE user_id = ? 
                ORDER BY date DESC LIMIT ?
                """, 
                (user_id, limit)
            )
            
            history = [dict(row) for row in cursor.fetchall()]
            conn.close()
        
        return history
    
    def get_irrigation_data_as_df(self, user_id):
        """Retrieve irrigation data as a pandas DataFrame for plotting."""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
        
        query = """
        SELECT date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture
        FROM irrigation_records 
        WHERE user_id = {} 
        ORDER BY date ASC
        """.format(user_id if self.use_postgres else '?')
        
        if self.use_postgres:
            df = pd.read_sql_query(query, conn)
            self.release_connection(conn)
        else:
            df = pd.read_sql_query(query, conn, params=(user_id,))
            conn.close()
        
        return df
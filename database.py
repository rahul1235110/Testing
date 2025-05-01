import sqlite3
import json
import os
from datetime import datetime
import pandas as pd

class Database:
    def __init__(self, db_path="crop_irrigation.db"):
        """Initialize the database connection."""
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """Create and return a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """Create necessary database tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
        
        # Create field_data table to store user's field information
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
        
        # Create irrigation_records table to store irrigation history
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
        conn.close()
    
    def add_user(self, username, email, password):
        """Add a new user to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Username or email already exists
            return False
        finally:
            conn.close()
    
    def get_user_by_username(self, username):
        """Retrieve user by username."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None
    
    def get_user_by_email(self, email):
        """Retrieve user by email."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None
    
    def save_field_data(self, user_id, lat, lon, field_capacity, crop_type, sowing_date):
        """Save or update field data for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if user already has field data
        cursor.execute(
            "SELECT id FROM field_data WHERE user_id = ?", 
            (user_id,)
        )
        existing_field = cursor.fetchone()
        
        if existing_field:
            # Update existing field data
            cursor.execute(
                """
                UPDATE field_data 
                SET lat = ?, lon = ?, field_capacity = ?, crop_type = ?, sowing_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (lat, lon, field_capacity, crop_type, sowing_date, user_id)
            )
            field_id = existing_field['id']
        else:
            # Insert new field data
            cursor.execute(
                """
                INSERT INTO field_data (user_id, lat, lon, field_capacity, crop_type, sowing_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, lat, lon, field_capacity, crop_type, sowing_date)
            )
            field_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return field_id
    
    def get_field_data(self, user_id):
        """Retrieve field data for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM field_data WHERE user_id = ?", (user_id,))
        field_data = cursor.fetchone()
        conn.close()
        
        if field_data:
            return dict(field_data)
        return None
    
    def save_irrigation_record(self, user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture):
        """Save irrigation calculation records."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO irrigation_records 
            (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture)
        )
        
        conn.commit()
        conn.close()
    
    def get_irrigation_history(self, user_id, limit=10):
        """Retrieve irrigation history for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
        
        query = """
        SELECT date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture
        FROM irrigation_records 
        WHERE user_id = ? 
        ORDER BY date ASC
        """
        
        df = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()
        
        return df

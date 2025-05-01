import os
import json
import datetime
import sqlite3

# Try to import psycopg2, but handle the case when it's not available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    print("psycopg2 not available, PostgreSQL support in DataBackup disabled")
    PSYCOPG2_AVAILABLE = False

from database_pg import Database

class DataBackup:
    """
    Utility class to backup PostgreSQL data to JSON files in the data/ directory.
    This ensures data is not lost if the PostgreSQL database is reset.
    """
    
    def __init__(self):
        """Initialize the backup system with database connection."""
        self.db = Database()
        self.data_dir = "data"
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def backup_users(self):
        """Backup users table to users.json."""
        conn = self.db.get_connection()
        if not conn:
            print("Could not connect to database")
            return False
        
        cursor = conn.cursor()
        users = []
        
        try:
            if self.db.use_postgres:
                # Use RealDictCursor for PostgreSQL to get dictionary-like results if available
                if PSYCOPG2_AVAILABLE:
                    dict_cursor = conn.cursor(cursor_factory=RealDictCursor)
                    dict_cursor.execute("SELECT * FROM users")
                    users = [dict(row) for row in dict_cursor.fetchall()]
                else:
                    # Fallback if PostgreSQL is used but RealDictCursor not available
                    cursor.execute("SELECT * FROM users")
                    users_data = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    users = [dict(zip(column_names, user)) for user in users_data]
            else:
                # For SQLite
                cursor.execute("SELECT * FROM users")
                users_data = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                users = [dict(zip(column_names, user)) for user in users_data]
            
            # Convert any non-serializable types
            for user in users:
                for key, value in user.items():
                    if isinstance(value, datetime.datetime):
                        user[key] = value.isoformat()
            
            # Write to JSON file
            with open(os.path.join(self.data_dir, 'users.json'), 'w') as f:
                json.dump(users, f, indent=4)
            
            print(f"Backed up {len(users)} users to users.json")
            return True
            
        except Exception as e:
            print(f"Error backing up users: {str(e)}")
            return False
        finally:
            if self.db.use_postgres:
                self.db.release_connection(conn)
            else:
                conn.close()
    
    def backup_field_data(self):
        """Backup field_data table to field_data.json."""
        conn = self.db.get_connection()
        if not conn:
            print("Could not connect to database")
            return False
        
        cursor = conn.cursor()
        fields = []
        
        try:
            if self.db.use_postgres:
                # Use RealDictCursor for PostgreSQL to get dictionary-like results if available
                if PSYCOPG2_AVAILABLE:
                    dict_cursor = conn.cursor(cursor_factory=RealDictCursor)
                    dict_cursor.execute("SELECT * FROM field_data")
                    fields = [dict(row) for row in dict_cursor.fetchall()]
                else:
                    # Fallback if PostgreSQL is used but RealDictCursor not available
                    cursor.execute("SELECT * FROM field_data")
                    fields_data = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    fields = [dict(zip(column_names, field)) for field in fields_data]
            else:
                # For SQLite
                cursor.execute("SELECT * FROM field_data")
                fields_data = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                fields = [dict(zip(column_names, field)) for field in fields_data]
            
            # Convert any non-serializable types
            for field in fields:
                for key, value in field.items():
                    if isinstance(value, datetime.datetime):
                        field[key] = value.isoformat()
            
            # Write to JSON file
            with open(os.path.join(self.data_dir, 'field_data.json'), 'w') as f:
                json.dump(fields, f, indent=4)
            
            print(f"Backed up {len(fields)} fields to field_data.json")
            return True
            
        except Exception as e:
            print(f"Error backing up field data: {str(e)}")
            return False
        finally:
            if self.db.use_postgres:
                self.db.release_connection(conn)
            else:
                conn.close()
    
    def backup_irrigation_records(self):
        """Backup irrigation_records table to irrigation_records.json."""
        conn = self.db.get_connection()
        if not conn:
            print("Could not connect to database")
            return False
        
        cursor = conn.cursor()
        records = []
        
        try:
            if self.db.use_postgres:
                # Use RealDictCursor for PostgreSQL to get dictionary-like results if available
                if PSYCOPG2_AVAILABLE:
                    dict_cursor = conn.cursor(cursor_factory=RealDictCursor)
                    dict_cursor.execute("SELECT * FROM irrigation_records")
                    records = [dict(row) for row in dict_cursor.fetchall()]
                else:
                    # Fallback if PostgreSQL is used but RealDictCursor not available
                    cursor.execute("SELECT * FROM irrigation_records")
                    records_data = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    records = [dict(zip(column_names, record)) for record in records_data]
            else:
                # For SQLite
                cursor.execute("SELECT * FROM irrigation_records")
                records_data = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                records = [dict(zip(column_names, record)) for record in records_data]
            
            # Convert any non-serializable types
            for record in records:
                for key, value in record.items():
                    if isinstance(value, datetime.datetime):
                        record[key] = value.isoformat()
            
            # Write to JSON file
            with open(os.path.join(self.data_dir, 'irrigation_records.json'), 'w') as f:
                json.dump(records, f, indent=4)
            
            print(f"Backed up {len(records)} irrigation records to irrigation_records.json")
            return True
            
        except Exception as e:
            print(f"Error backing up irrigation records: {str(e)}")
            return False
        finally:
            if self.db.use_postgres:
                self.db.release_connection(conn)
            else:
                conn.close()
    
    def backup_all(self):
        """Backup all tables to JSON files."""
        print(f"Starting database backup at {datetime.datetime.now()}")
        
        success_users = self.backup_users()
        success_fields = self.backup_field_data()
        success_records = self.backup_irrigation_records()
        
        print(f"Database backup completed at {datetime.datetime.now()}")
        return success_users and success_fields and success_records
    
    def restore_from_json_if_empty(self):
        """
        Check if the database is empty, and if so, restore data from JSON files.
        This is useful when the PostgreSQL database is reset but JSON backups exist.
        """
        # First check if database is empty
        conn = self.db.get_connection()
        if not conn:
            print("Could not connect to database")
            return False
        
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # If database already has users, don't restore
            if user_count > 0:
                print(f"Database already has {user_count} users, skipping restore")
                return False
            
            # Database is empty, try to restore from JSON files
            print("Database appears to be empty. Attempting to restore from JSON backups...")
            
            # Restore users
            try:
                with open(os.path.join(self.data_dir, 'users.json'), 'r') as f:
                    users = json.load(f)
                
                for user in users:
                    # Execute insert for each user
                    if self.db.use_postgres:
                        cursor.execute(
                            "INSERT INTO users (id, username, email, password, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (user['id'], user['username'], user['email'], user['password'], 
                             user.get('created_at', datetime.datetime.now().isoformat()))
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO users (id, username, email, password, created_at) VALUES (?, ?, ?, ?, ?)",
                            (user['id'], user['username'], user['email'], user['password'], 
                             user.get('created_at', datetime.datetime.now().isoformat()))
                        )
                
                print(f"Restored {len(users)} users from backup")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"No valid users backup found: {str(e)}")
            
            # Restore field data
            try:
                with open(os.path.join(self.data_dir, 'field_data.json'), 'r') as f:
                    fields = json.load(f)
                
                for field in fields:
                    # Execute insert for each field
                    if self.db.use_postgres:
                        cursor.execute(
                            """
                            INSERT INTO field_data 
                            (id, user_id, lat, lon, field_capacity, crop_type, sowing_date, created_at, updated_at) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (field['id'], field['user_id'], field['lat'], field['lon'], 
                             field['field_capacity'], field['crop_type'], field['sowing_date'],
                             field.get('created_at', datetime.datetime.now().isoformat()),
                             field.get('updated_at', datetime.datetime.now().isoformat()))
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO field_data 
                            (id, user_id, lat, lon, field_capacity, crop_type, sowing_date, created_at, updated_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (field['id'], field['user_id'], field['lat'], field['lon'], 
                             field['field_capacity'], field['crop_type'], field['sowing_date'],
                             field.get('created_at', datetime.datetime.now().isoformat()),
                             field.get('updated_at', datetime.datetime.now().isoformat()))
                        )
                
                print(f"Restored {len(fields)} fields from backup")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"No valid field data backup found: {str(e)}")
            
            # Restore irrigation records
            try:
                with open(os.path.join(self.data_dir, 'irrigation_records.json'), 'r') as f:
                    records = json.load(f)
                
                for record in records:
                    # Execute insert for each record
                    if self.db.use_postgres:
                        cursor.execute(
                            """
                            INSERT INTO irrigation_records 
                            (id, user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture, created_at) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (record['id'], record['user_id'], record['field_id'], record['date'], 
                             record['et0'], record['aet'], record['irrigation_required'], 
                             record['adjusted_irrigation'], record['soil_moisture'],
                             record.get('created_at', datetime.datetime.now().isoformat()))
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO irrigation_records 
                            (id, user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture, created_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (record['id'], record['user_id'], record['field_id'], record['date'], 
                             record['et0'], record['aet'], record['irrigation_required'], 
                             record['adjusted_irrigation'], record['soil_moisture'],
                             record.get('created_at', datetime.datetime.now().isoformat()))
                        )
                
                print(f"Restored {len(records)} irrigation records from backup")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"No valid irrigation records backup found: {str(e)}")
            
            # Commit all changes
            conn.commit()
            print("Database restore completed successfully")
            return True
            
        except Exception as e:
            print(f"Error during database restore: {str(e)}")
            return False
        finally:
            if self.db.use_postgres:
                self.db.release_connection(conn)
            else:
                conn.close()


if __name__ == "__main__":
    # This script can be run directly for testing
    backup = DataBackup()
    backup.backup_all()
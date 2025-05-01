import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

class GitDB:
    """Database class that stores data in JSON files which can be committed to GitHub.
    This approach allows storing data directly in the Git repository.
    """
    
    def __init__(self):
        """Initialize the database by loading data from JSON files."""
        # Create data directory if it doesn't exist
        if not os.path.exists("data"):
            os.makedirs("data")
        
        # Initialize session state variables for caching
        if 'users' not in st.session_state:
            st.session_state.users = self._load_from_file("data/users.json")
            
        if 'field_data' not in st.session_state:
            st.session_state.field_data = self._load_from_file("data/field_data.json")
            
        if 'irrigation_records' not in st.session_state:
            st.session_state.irrigation_records = self._load_from_file("data/irrigation_records.json")
    
    def _load_from_file(self, file_path):
        """Load data from a JSON file."""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    return json.load(file)
            return []
        except Exception as e:
            st.warning(f"Error loading data from {file_path}: {str(e)}")
            return []
    
    def _save_to_file(self, data, file_path):
        """Save data to a JSON file."""
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=2)
            return True
        except Exception as e:
            st.error(f"Error saving data to {file_path}: {str(e)}")
            return False
    
    def add_user(self, username, email, password):
        """Add a new user to the database."""
        # Check if username or email already exists
        if any(user['username'] == username for user in st.session_state.users) or \
           any(user['email'] == email for user in st.session_state.users):
            return False
        
        # Generate a new user ID (max ID + 1)
        user_id = 1
        if st.session_state.users:
            user_id = max(user['id'] for user in st.session_state.users) + 1
        
        # Create and add new user
        new_user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password': password,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        st.session_state.users.append(new_user)
        self._save_to_file(st.session_state.users, "data/users.json")
        return True
    
    def get_user_by_username(self, username):
        """Retrieve user by username."""
        for user in st.session_state.users:
            if user['username'] == username:
                return user
        return None
    
    def get_user_by_email(self, email):
        """Retrieve user by email."""
        for user in st.session_state.users:
            if user['email'] == email:
                return user
        return None
    
    def save_field_data(self, user_id, lat, lon, field_capacity, crop_type, sowing_date):
        """Save or update field data for a user."""
        # Find existing field data for user
        existing_field = None
        field_index = -1
        for i, field in enumerate(st.session_state.field_data):
            if field['user_id'] == user_id:
                existing_field = field
                field_index = i
                break
        
        if existing_field:
            # Update existing field data
            st.session_state.field_data[field_index].update({
                'lat': lat,
                'lon': lon,
                'field_capacity': field_capacity,
                'crop_type': crop_type,
                'sowing_date': sowing_date,
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            field_id = existing_field['id']
        else:
            # Generate a new field ID
            field_id = 1
            if st.session_state.field_data:
                field_id = max(field['id'] for field in st.session_state.field_data) + 1
            
            # Create new field data
            new_field = {
                'id': field_id,
                'user_id': user_id,
                'lat': lat,
                'lon': lon,
                'field_capacity': field_capacity,
                'crop_type': crop_type,
                'sowing_date': sowing_date,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.session_state.field_data.append(new_field)
        
        # Save to file
        self._save_to_file(st.session_state.field_data, "data/field_data.json")
        return field_id
    
    def get_field_data(self, user_id):
        """Retrieve field data for a user."""
        for field in st.session_state.field_data:
            if field['user_id'] == user_id:
                return field
        return None
    
    def save_irrigation_record(self, user_id, field_id, date, et0, aet, irrigation_required, adjusted_irrigation, soil_moisture):
        """Save irrigation calculation records."""
        # Generate a new record ID
        record_id = 1
        if st.session_state.irrigation_records:
            record_id = max(record['id'] for record in st.session_state.irrigation_records) + 1
        
        # Create new irrigation record
        new_record = {
            'id': record_id,
            'user_id': user_id,
            'field_id': field_id,
            'date': date,
            'et0': et0,
            'aet': aet,
            'irrigation_required': irrigation_required,
            'adjusted_irrigation': adjusted_irrigation,
            'soil_moisture': soil_moisture,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        st.session_state.irrigation_records.append(new_record)
        
        # Save to file
        self._save_to_file(st.session_state.irrigation_records, "data/irrigation_records.json")
    
    def get_irrigation_history(self, user_id, limit=10):
        """Retrieve irrigation history for a user."""
        # Filter records by user_id and sort by date (newest first)
        user_records = [record for record in st.session_state.irrigation_records if record['user_id'] == user_id]
        user_records.sort(key=lambda x: x['date'], reverse=True)
        
        # Limit the number of records
        return user_records[:limit] if limit else user_records
    
    def get_irrigation_data_as_df(self, user_id):
        """Retrieve irrigation data as a pandas DataFrame for plotting."""
        # Filter records by user_id
        user_records = [record for record in st.session_state.irrigation_records if record['user_id'] == user_id]
        
        if not user_records:
            return pd.DataFrame()
        
        # Convert to DataFrame and sort by date
        df = pd.DataFrame(user_records)
        
        # Select only needed columns
        if 'date' in df and not df.empty:
            df = df[['date', 'et0', 'aet', 'irrigation_required', 'adjusted_irrigation', 'soil_moisture']]
            df.sort_values('date', inplace=True)
        
        return df
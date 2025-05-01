import streamlit as st
import pandas as pd
import json
from datetime import datetime

class StreamlitDB:
    """Database class that stores data in Streamlit's session state.
    This is a simplified database that persists during the session and can save to Streamlit Cloud's secrets.
    """
    
    def __init__(self):
        """Initialize the database in session state."""
        # Initialize database tables in session state if they don't exist
        if 'users' not in st.session_state:
            st.session_state.users = []
            
        if 'field_data' not in st.session_state:
            st.session_state.field_data = []
            
        if 'irrigation_records' not in st.session_state:
            st.session_state.irrigation_records = []
            
        # Load data from secrets if available
        self._load_from_secrets()
    
    def _load_from_secrets(self):
        """Load data from Streamlit secrets if available."""
        try:
            if "database" in st.secrets:
                if "users" in st.secrets["database"]:
                    st.session_state.users = json.loads(st.secrets["database"]["users"])
                    
                if "field_data" in st.secrets["database"]:
                    st.session_state.field_data = json.loads(st.secrets["database"]["field_data"])
                    
                if "irrigation_records" in st.secrets["database"]:
                    st.session_state.irrigation_records = json.loads(st.secrets["database"]["irrigation_records"])
        except Exception as e:
            # If there's an error loading data, just continue with empty tables
            st.error(f"Error loading data from secrets: {str(e)}")
    
    def _save_to_secrets(self):
        """Save data to Streamlit secrets (this will only work in development, not in Streamlit Cloud).
        For Streamlit Cloud, you'll need to manually update the secrets from the Streamlit Cloud dashboard.
        """
        try:
            # This is just a placeholder to show what would need to be saved
            # In reality, users would need to manually add this to their Streamlit Cloud secrets
            st.warning("""
            To save your data permanently in Streamlit Cloud, you'll need to add the following to your Streamlit Cloud secrets:
            
            [database]
            users = '""" + json.dumps(st.session_state.users) + """'
            field_data = '""" + json.dumps(st.session_state.field_data) + """'
            irrigation_records = '""" + json.dumps(st.session_state.irrigation_records) + """'
            """)
        except Exception as e:
            st.error(f"Error generating secrets string: {str(e)}")
    
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
            return existing_field['id']
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
        
        # For demo purposes, show how to save the data to secrets
        # In a real app, you'd save periodically or on important changes
        self._save_to_secrets()
    
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
import streamlit as st

# Set page config (must be the first Streamlit command)
st.set_page_config(
    page_title="Crop Irrigation Tracker",
    page_icon="🌾",
    layout="wide"
)

import os
import json
from datetime import datetime, timedelta
import pandas as pd
import base64

# Import local modules
from database_pg import Database  # Using PostgreSQL for persistent storage
from auth import Auth
from utils import (
    calculate_crop_stage, fetch_weather_data, fetch_soil_data,
    kelvin_to_celsius, jensen_haise_et0, calculate_aet,
    calculate_irrigation_requirement, kc_values, plot_irrigation_history
)
from data_backup import DataBackup

# Initialize database and authentication
db = Database()  # Will automatically connect to PostgreSQL if DATABASE_URL is available
auth = Auth()

# Initialize data backup system
backup_system = DataBackup()

# Check if database is empty and needs restoration from JSON backups
backup_system.restore_from_json_if_empty()

# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user' not in st.session_state:
    st.session_state.user = None

# Main application logic
def main():
    # Check if user is authenticated
    if not st.session_state.authenticated:
        auth.display_auth_page()
        return
    
    # User is authenticated, get user info
    user = st.session_state.user
    user_id = user['id']
    
    # Display logout button in sidebar
    auth.logout_user()
    
    # Add admin panel
    is_admin = user['username'] == 'admin'  # Simple check for admin user
    
    # Display main application
    st.title("🌾 Crop Irrigation and Growth Tracker 🌦️💧")
    st.sidebar.write(f"Welcome, {user['username']}!")
    
    # Add admin panel in sidebar if user is admin
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Admin Panel")
        
        # Get database statistics
        if st.sidebar.button("📊 View Database Statistics"):
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                
                try:
                    # Count users
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    
                    # Count fields
                    cursor.execute("SELECT COUNT(*) FROM field_data")
                    field_count = cursor.fetchone()[0]
                    
                    # Count irrigation records
                    cursor.execute("SELECT COUNT(*) FROM irrigation_records")
                    record_count = cursor.fetchone()[0]
                    
                    # Display statistics
                    st.sidebar.markdown("### Database Statistics")
                    st.sidebar.markdown(f"👥 **Total Users**: {user_count}")
                    st.sidebar.markdown(f"🌾 **Total Fields**: {field_count}")
                    st.sidebar.markdown(f"💧 **Total Irrigation Records**: {record_count}")
                    
                    # Get most recent irrigation record date
                    cursor.execute("SELECT MAX(date) FROM irrigation_records")
                    latest_record = cursor.fetchone()[0]
                    if latest_record:
                        st.sidebar.markdown(f"📅 **Latest Calculation**: {latest_record}")
                        
                except Exception as e:
                    st.sidebar.error(f"Error fetching database statistics: {str(e)}")
                finally:
                    if db.use_postgres:
                        db.release_connection(conn)
                    else:
                        conn.close()
            else:
                st.sidebar.error("Could not connect to database")
        
        # Add button to manually trigger irrigation calculations for all users
        if st.sidebar.button("🔄 Run Calculations for All Users"):
            try:
                from scheduler import run_scheduled_calculations
                run_scheduled_calculations()
                st.sidebar.success("✅ Calculations completed for all users!")
            except Exception as e:
                st.sidebar.error(f"❌ Error: {str(e)}")
                
        # Add backup to JSON button
        if st.sidebar.button("💾 Backup Database to JSON"):
            with st.sidebar.spinner("Backing up database to JSON files..."):
                if backup_system.backup_all():
                    st.sidebar.success("✅ Database successfully backed up to JSON files in the data/ directory")
                    
                    # Create download links for the backup files
                    st.sidebar.markdown("### Download Backup Files")
                    
                    # Function to create download links
                    def get_download_link(file_path, link_text):
                        try:
                            with open(file_path, 'r') as f:
                                data = f.read()
                            b64 = base64.b64encode(data.encode()).decode()
                            href = f'<a href="data:file/json;base64,{b64}" download="{os.path.basename(file_path)}">📥 {link_text}</a>'
                            return href
                        except FileNotFoundError:
                            return f"❌ File not found: {file_path}"
                    
                    # Create download links for each data file
                    data_files = {
                        "Users Data": "data/users.json",
                        "Field Data": "data/field_data.json",
                        "Irrigation Records": "data/irrigation_records.json"
                    }
                    
                    for name, path in data_files.items():
                        st.sidebar.markdown(get_download_link(path, name), unsafe_allow_html=True)
                else:
                    st.sidebar.error("❌ Failed to backup database")
        
        # Add information about database persistence
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Data Persistence Info")
        if db.use_postgres:
            st.sidebar.success("✅ **Using PostgreSQL Database**")
            st.sidebar.markdown("""
            Data is stored in PostgreSQL and backed up to JSON files. 
            
            **If the free PostgreSQL database resets:**
            1. Data will be automatically restored from JSON backup files 
            2. Make sure to download backups regularly using the 'Backup Database to JSON' button
            3. Keep these JSON files safe as they contain all your data
            """)
        else:
            st.sidebar.warning("⚠️ **Using SQLite Database**")
            st.sidebar.markdown("Data is stored in a local SQLite database. Regular backups are recommended.")
    
    # Get user's field data if available
    field_data = db.get_field_data(user_id)
    
    # Input for Latitude and Longitude
    st.write("📍 Please enter your location (latitude and longitude):")
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Enter Latitude 📍", 
            value=float(field_data['lat']) if field_data else 35.0, 
            format="%.6f"
        )
    with col2:
        lon = st.number_input(
            "Enter Longitude 📍", 
            value=float(field_data['lon']) if field_data else 139.0, 
            format="%.6f"
        )
    
    # Input for Max Water Holding Capacity (Field Capacity)
    field_capacity = st.number_input(
        "💧 Enter Max Water Holding Capacity (Field Capacity) as a fraction (e.g., 0.50 for 50%)",
        value=float(field_data['field_capacity']) if field_data else 0.50,
        min_value=0.10,
        max_value=1.0,
        step=0.01
    )
    
    # Crop Selection
    crop_type = st.selectbox(
        "🌱 Select Crop Type 🌾", 
        options=list(kc_values.keys()),
        index=list(kc_values.keys()).index(field_data['crop_type']) if field_data else 0
    )
    
    # Input for Crop Sowing Date
    default_date = datetime.strptime(field_data['sowing_date'], "%Y-%m-%d").date() if field_data else datetime.today()
    sowing_date = st.date_input("📅 Enter Sowing Date", default_date)
    
    # Save field data when any input changes
    current_field_data = {
        'lat': lat,
        'lon': lon,
        'field_capacity': field_capacity,
        'crop_type': crop_type,
        'sowing_date': str(sowing_date)
    }
    
    # Save field data to database
    if field_data is None or any(current_field_data[k] != field_data.get(k, None) for k in current_field_data):
        field_id = db.save_field_data(
            user_id, lat, lon, field_capacity, crop_type, str(sowing_date)
        )
    else:
        field_id = field_data['id']
    
    # Calculate Crop Growth Stage
    stage, days_since_sowing = calculate_crop_stage(str(sowing_date))
    
    st.write(f"🌱 **Crop Stage**: {stage}")
    st.write(f"📅 **Days Since Sowing**: {days_since_sowing} days")
    
    # Display Kc Values for the Selected Crop and Stage
    current_kc = kc_values[crop_type]
    if stage == "🌱 Initial Stage":
        kc = current_kc[0]
    elif stage == "🌾 Mid-Season Stage":
        kc = current_kc[1]
    else:
        kc = current_kc[2]
    
    st.write(f"🌿 **Current Kc Value for {crop_type}**: {kc}")
    
    # Calculate PWP (Permanent Wilting Point) based on field capacity
    pwp = field_capacity / 2.5
    st.write(f"💧 **Calculated PWP (Permanent Wilting Point)**: {pwp:.2f}")
    
    # Run button to trigger the calculations
    if st.button('Run Calculations'):
        with st.spinner("Fetching data and performing calculations..."):
            # Fetch weather and soil data based on user input
            weather_data = fetch_weather_data(lat, lon)
            soil_data = fetch_soil_data(lat, lon)
            
            # Process and display weather data
            if weather_data:
                st.markdown("### 🌤️ **Weather Forecast Data**:")
                temp_max = kelvin_to_celsius(weather_data[0]['main']['temp_max'])
                
                # Calculate ET₀ using the Jensen-Haise equation
                et_0 = jensen_haise_et0(T_max=temp_max)
                
                st.markdown(f"🌡️ **Max Temperature (T_max):** {temp_max:.2f} °C")
                st.markdown(f"🌞 **Estimated ET₀ (from Jensen-Haise Method):** {et_0:.2f} mm/day")
            else:
                st.error("Could not fetch weather data. Please check your coordinates and try again.")
                return
            
            # Process and display soil data
            if soil_data:
                st.markdown("### 🌱 **Soil Data**:")
                soil_moisture = soil_data['moisture']  # Soil moisture from the API (as a fraction)
                st.markdown(f"💧 **Current Soil Moisture from API**: {soil_moisture * 100:.2f} %")
                
                soil_moisture_max = field_capacity  # Use field capacity as max soil moisture
                
                # Calculate AET based on soil moisture and ET₀
                aet = calculate_aet(et_0, soil_moisture, soil_moisture_max, pwp)
                st.markdown(f"💧 **Estimated AET (Actual Evapotranspiration)**: {aet:.2f} mm/day")
                
                # Calculate irrigation requirement based on crop stage and Kc value
                irrigation = calculate_irrigation_requirement(et_0, kc)
                st.markdown(f"💧 **Recommended Irrigation Requirement for {crop_type}**: {irrigation:.2f} mm/day")
                
                # Now, adjust irrigation recommendation based on soil moisture and rain forecast
                soil_moisture_example = soil_moisture
                
                # Check if weather forecast includes precipitation
                rain_forecast = 0.0
                if weather_data and 'rain' in weather_data[0]:
                    rain_forecast = weather_data[0]['rain'].get('3h', 0.0)  # mm in next 3 hours
                
                # Adjust irrigation recommendation
                adjusted_irrigation = max(0, irrigation * (1 - soil_moisture_example) - rain_forecast)
                
                st.markdown(f"🌧️ **Adjusted Irrigation Requirement (considering soil moisture and rainfall)**: {adjusted_irrigation:.2f} mm/day")
                
                # Save irrigation record to database
                today = datetime.now().strftime("%Y-%m-%d")
                db.save_irrigation_record(
                    user_id, field_id, today, et_0, aet, 
                    irrigation, adjusted_irrigation, soil_moisture
                )
                
                st.success("✅ Calculations completed and data saved successfully!")
            else:
                st.error("Could not fetch soil data. Please check your coordinates and try again.")
    
    # Display irrigation history
    st.markdown("---")
    st.subheader("📜 Irrigation History")
    
    # Get irrigation history from database
    irrigation_history = db.get_irrigation_history(user_id)
    
    if irrigation_history:
        # Create a more detailed history display
        history_df = pd.DataFrame(irrigation_history)
        
        # Reformat date
        history_df['formatted_date'] = pd.to_datetime(history_df['date']).dt.strftime('%b %d, %Y')
        
        # Display as a table
        st.dataframe(
            history_df[['formatted_date', 'et0', 'aet', 'irrigation_required', 'adjusted_irrigation', 'soil_moisture']].rename(
                columns={
                    'formatted_date': 'Date',
                    'et0': 'ET₀ (mm/day)',
                    'aet': 'AET (mm/day)',
                    'irrigation_required': 'Required Irrigation (mm/day)',
                    'adjusted_irrigation': 'Adjusted Irrigation (mm/day)',
                    'soil_moisture': 'Soil Moisture (fraction)'
                }
            )
        )
        
        # Get irrigation data as DataFrame for plotting
        irrigation_df = db.get_irrigation_data_as_df(user_id)
        
        # Plot irrigation history
        plot_irrigation_history(irrigation_df)
    else:
        st.info("No irrigation history found. Run calculations to generate data.")

def check_auto_calculate():
    """Check if it's time to run automatic calculations for all users."""
    from datetime import datetime
    
    # If it's between 1:00 PM and 1:15 PM, run the calculations
    now = datetime.now()
    if now.hour == 13 and now.minute < 15:
        # Only run once during this time window
        if 'auto_calc_today' not in st.session_state or st.session_state.auto_calc_today != now.date():
            st.session_state.auto_calc_today = now.date()
            
            try:
                # Import and run the scheduled calculations
                from scheduler import run_scheduled_calculations
                run_scheduled_calculations()
                
                # Show a success message (will appear on next refresh)
                st.session_state.show_scheduler_success = True
            except Exception as e:
                st.error(f"Failed to run scheduled calculations: {str(e)}")

if __name__ == "__main__":
    # Check if we should run auto calculations
    check_auto_calculate()
    
    # Show success message if calculations were run
    if st.session_state.get("show_scheduler_success", False):
        st.success("Daily irrigation calculations have been automatically run for all users!")
        # Reset the flag
        st.session_state.show_scheduler_success = False
    
    # Run the main app
    main()

import os
import time
import datetime
import pytz
import json
import requests
import psycopg2
from database_pg import Database
from data_backup import DataBackup
from utils import (
    calculate_crop_stage, fetch_weather_data, fetch_soil_data,
    kelvin_to_celsius, jensen_haise_et0, calculate_aet,
    calculate_irrigation_requirement, kc_values
)

def run_scheduled_calculations():
    """
    Run automatic calculations for all users and save results.
    This function should be called daily at 1 PM.
    """
    print(f"Starting scheduled calculations at {datetime.datetime.now()}")
    
    # Initialize database
    db = Database()
    
    # Get all users from the database
    conn = db.get_connection()
    if not conn:
        print("Could not connect to database")
        return
    
    cursor = conn.cursor()
    users = []
    
    try:
        cursor.execute("SELECT id, username FROM users")
        
        if db.use_postgres:
            # PostgreSQL
            users_data = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            users = [dict(zip(column_names, user)) for user in users_data]
        else:
            # SQLite
            users = [{'id': row[0], 'username': row[1]} for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
    finally:
        if db.use_postgres:
            db.release_connection(conn)
        else:
            conn.close()
    
    # For each user, load their field data and run calculations
    for user in users:
        user_id = user['id']
        print(f"Processing user: {user['username']} (ID: {user_id})")
        
        # Get user's field data
        field_data = db.get_field_data(user_id)
        if not field_data:
            print(f"No field data for user {user_id}, skipping")
            continue
        
        # Extract field data
        lat = field_data['lat']
        lon = field_data['lon']
        field_capacity = field_data['field_capacity']
        crop_type = field_data['crop_type']
        sowing_date = field_data['sowing_date']
        field_id = field_data['id']
        
        # Calculate PWP (Permanent Wilting Point) based on field capacity
        pwp = field_capacity / 2.5
        
        # Calculate crop stage
        stage, days_since_sowing = calculate_crop_stage(sowing_date)
        
        # Determine Kc values for the crop stage
        current_kc = kc_values[crop_type]
        if stage == "🌱 Initial Stage":
            kc = current_kc[0]
        elif stage == "🌾 Mid-Season Stage":
            kc = current_kc[1]
        else:
            kc = current_kc[2]
        
        try:
            # Fetch weather data
            weather_data = fetch_weather_data(lat, lon)
            if not weather_data:
                print(f"Could not fetch weather data for user {user_id}, skipping")
                continue
                
            # Fetch soil data
            soil_data = fetch_soil_data(lat, lon)
            if not soil_data:
                print(f"Could not fetch soil data for user {user_id}, skipping")
                continue
            
            # Process weather data
            temp_max = kelvin_to_celsius(weather_data[0]['main']['temp_max'])
            
            # Calculate ET₀ using the Jensen-Haise equation
            et_0 = jensen_haise_et0(T_max=temp_max)
            
            # Process soil data
            soil_moisture = soil_data['moisture']  # Soil moisture from the API (as a fraction)
            soil_moisture_max = field_capacity  # Use field capacity as max soil moisture
            
            # Calculate AET based on soil moisture and ET₀
            aet = calculate_aet(et_0, soil_moisture, soil_moisture_max, pwp)
            
            # Calculate irrigation requirement based on crop stage and Kc value
            irrigation = calculate_irrigation_requirement(et_0, kc)
            
            # Check if weather forecast includes precipitation
            rain_forecast = 0.0
            if weather_data and 'rain' in weather_data[0]:
                rain_forecast = weather_data[0]['rain'].get('3h', 0.0)  # mm in next 3 hours
            
            # Adjust irrigation recommendation
            adjusted_irrigation = max(0, irrigation * (1 - soil_moisture) - rain_forecast)
            
            # Save irrigation record to database
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            db.save_irrigation_record(
                user_id, field_id, today, et_0, aet, 
                irrigation, adjusted_irrigation, soil_moisture
            )
            
            print(f"Successfully saved irrigation data for user {user_id}")
            
        except Exception as e:
            print(f"Error processing calculations for user {user_id}: {str(e)}")
    
    print(f"Completed scheduled calculations at {datetime.datetime.now()}")
    
    # After completing calculations, backup the database to JSON files
    print("Starting database backup...")
    backup = DataBackup()
    if backup.backup_all():
        print("Database backup completed successfully")
    else:
        print("Database backup failed")

def is_time_to_run():
    """Check if it's 1 PM (13:00) in the local timezone."""
    now = datetime.datetime.now()
    return now.hour == 13 and now.minute < 15  # Run between 1:00 PM and 1:15 PM

if __name__ == "__main__":
    # This script can be run directly for testing
    run_scheduled_calculations()
import streamlit as st
import requests
from datetime import datetime, timedelta
import math
import pandas as pd
import os

# Crop Kc values
kc_values = {
    "Cotton": [0.3, 1.15, 0.45],  # [Initial, Mid-Season, Late-Season]
    "Redgram": [0.3, 1.2, 0.5],
    "Wheat": [0.3, 1.15, 0.45],
    "Rice": [0.3, 1.2, 0.5],
    "Corn": [0.3, 1.15, 0.6],
}

def calculate_crop_stage(sowing_date):
    """Calculate crop growth stage based on sowing date."""
    today = datetime.now()
    sowing_date = datetime.strptime(sowing_date, "%Y-%m-%d")
    days_since_sowing = (today - sowing_date).days

    if days_since_sowing < 30:
        stage = "🌱 Initial Stage"
    elif 30 <= days_since_sowing < 70:
        stage = "🌾 Mid-Season Stage"
    else:
        stage = "🌿 Late-Season Stage"
    return stage, days_since_sowing

def fetch_weather_data(lat, lon):
    """Fetch weather data from agromonitoring API."""
    weather_url = "http://api.agromonitoring.com/agro/1.0/weather/forecast"
    
    # Try to get API key from Streamlit secrets first, then environment variable, then fallback to default
    try:
        api_key = st.secrets["AGROMONITORING_API_KEY"]
    except:
        api_key = os.getenv('AGROMONITORING_API_KEY', '71fc994579e122b13072be4dc2e06eb7')
    
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key
    }
    try:
        response = requests.get(weather_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"⚠️ Failed to fetch weather data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"⚠️ Error fetching weather data: {str(e)}")
        return None

def fetch_soil_data(lat, lon):
    """Fetch soil data from agromonitoring API."""
    soil_url = "http://api.agromonitoring.com/agro/1.0/soil"
    
    # Try to get API key from Streamlit secrets first, then environment variable, then fallback to default
    try:
        api_key = st.secrets["AGROMONITORING_API_KEY"]
    except:
        api_key = os.getenv('AGROMONITORING_API_KEY', '71fc994579e122b13072be4dc2e06eb7')
    
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key
    }
    try:
        response = requests.get(soil_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"⚠️ Failed to fetch soil data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"⚠️ Error fetching soil data: {str(e)}")
        return None

def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15

def jensen_haise_et0(T_max):
    """Calculate ET₀ using the Jensen-Haise method."""
    return 0.025 * (T_max + 273 - 2.5)

def calculate_aet(et_0, soil_moisture, soil_moisture_max, pwp):
    """Calculate AET based on soil moisture and ET₀."""
    # If soil moisture is less than PWP, AET is zero
    if soil_moisture < pwp:
        return 0
    else:
        return et_0 * (soil_moisture / soil_moisture_max)

def calculate_irrigation_requirement(et_0, kc_value):
    """Calculate irrigation requirement based on Kc value."""
    irrigation_requirement = et_0 * kc_value
    return irrigation_requirement

def plot_irrigation_history(df):
    """Plot irrigation history data."""
    if df is not None and not df.empty:
        # Convert date string to datetime for better plotting
        df['date'] = pd.to_datetime(df['date'])
        
        # Plot irrigation data
        st.subheader("📊 Irrigation History")
        
        # Irrigation requirements plot
        st.line_chart(
            df.set_index('date')[['irrigation_required', 'adjusted_irrigation']]
        )
        
        # ET and AET plot
        st.subheader("📊 Evapotranspiration History")
        st.line_chart(
            df.set_index('date')[['et0', 'aet']]
        )
        
        # Soil moisture plot
        st.subheader("📊 Soil Moisture History")
        st.line_chart(
            df.set_index('date')['soil_moisture'] * 100  # Convert to percentage
        )
    else:
        st.info("No irrigation history available yet. Run calculations to generate data.")

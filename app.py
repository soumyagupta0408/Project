import streamlit as st
import random

st.title("🌫️ AQI Early Warning Prediction")
st.write("Welcome to Environmental montioring dashboard")
st.sidebar.header("Settings")
city = st.sidebar.selectbox(
    "Select City",
    ["Indore","Delhi","Jaipur","Banglore","Hyderabad","Mysore","Noida","Chandigarh","Bhopal"], index = 0
)

city_aqi = {
    "Indore":85,
    "Delhi":156,
    "Jaipur":101,
    "Banglore":145,
    "Hyderabad":120,
    "Mysore":56,
    "Noida":200,
    "Chandigarh":140,
    "Bhopal":94
}
current_aqi = city_aqi[city]
st.metric("Current AQI",current_aqi)
st.write("📍 Selected City:", city)
aqi = st.number_input("AQI calculator",min_value=0,max_value=500)
if aqi<=100:
    st.success("Air is Safe")
elif aqi<=200:
    st.warning("Air quality is Moderate")
else:
    st.error("Air quality is Dangerous")
st.button("Click Me")
    
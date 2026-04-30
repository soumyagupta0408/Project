import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(layout="wide")
st.title("🌫️ AQI Early Warning prediction System")

#load dataset
data = pd.read_csv("aqi_data.csv")
data["datetime"] = pd.to_datetime(data["datetime"])

#sidebar
st.sidebar.header("Settings")
city = st.sidebar.selectbox(
    "Select city",
    data["city"].unique()
)
threshold = st.sidebar.slider("Danger Threshold", 100, 300, 150)

# Filter data by selected city
city_data = data[data["city"] == city]

# Get latest AQI
current_aqi = city_data["aqi"].iloc[-1]

# Dummy prediction logic (later replace with ML)
predicted_aqi = current_aqi + np.random.randint(-10, 25)

# Layout
col1, col2 = st.columns(2)

col1.metric("📊 Current AQI", current_aqi)
col2.metric("🔮 Predicted AQI", predicted_aqi)

# Alert System
if predicted_aqi > threshold:
    st.error("🚨 Warning: AQI expected to cross threshold!")
else:
    st.success("✅ Air Quality Stable")

# Graph
st.subheader(f"📈 AQI Trend - {city}")

fig, ax = plt.subplots()
ax.plot(city_data["datetime"], city_data["aqi"], marker="o")
ax.axhline(threshold, linestyle="--")
ax.set_xlabel("Time")
ax.set_ylabel("AQI")

st.pyplot(fig)

# Anomaly Detection (Basic Demo)
if predicted_aqi - current_aqi > 20:
    st.warning("⚠ Sudden Pollution Spike Detected (Anomaly)")
else:
    st.info("No abnormal spike detected.")
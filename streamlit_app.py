import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="SUMO Traffic Dashboard", layout="wide")
st.title("SUMO Traffic Control Dashboard")

default_path = "output/multi_tls_log.csv"
uploaded = st.file_uploader("Upload multi_tls_log.csv (optional)", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
elif os.path.exists(default_path):
    df = pd.read_csv(default_path)
else:
    st.warning("No CSV found. Upload multi_tls_log.csv or keep it at output/multi_tls_log.csv")
    st.stop()

st.subheader("Raw Data")
st.dataframe(df, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(df["step"], df["activeVeh"], label="Active Vehicles")
    ax1.plot(df["step"], df["arrivedTotal"], label="Arrived Total")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Count")
    ax1.set_title("Vehicle Activity")
    ax1.grid(True)
    ax1.legend()
    st.pyplot(fig1)

with col2:
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(df["step"], df["sum_qA"], label="Queue A")
    ax2.plot(df["step"], df["sum_qB"], label="Queue B")
    ax2.plot(df["step"], df["sum_switches"], label="TLS Switches")
    ax2.set_xlabel("Step")
    ax2.set_ylabel("Count")
    ax2.set_title("Queues and Signal Switching")
    ax2.grid(True)
    ax2.legend()
    st.pyplot(fig2)

st.subheader("Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Max Active Vehicles", int(df["activeVeh"].max()))
c2.metric("Final Arrived Vehicles", int(df["arrivedTotal"].iloc[-1]))
c3.metric("Max Queue A", int(df["sum_qA"].max()))
c4.metric("Max Queue B", int(df["sum_qB"].max()))
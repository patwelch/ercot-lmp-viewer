import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from io import StringIO

st.set_page_config(page_title="ERCOT LMP Viewer", layout="wide")
st.title("ERCOT LMP Viewer")

#sidebar inputs

node = st.sidebar.text_input("Enter Node/Bus/Hub:", "HB_HOUSTON")
market = st.sidebar.selectbox("Select Market:", ["DAM", "RTM", "Both"])
start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")

if st.sidebar.button("Fetch Data"):
    try:
        st.info(f"Fetching data for {node} from {start_date} to {end_date}...")

        # TODO: Replace with ERCOT API call

        date_rng = pd.date_range(start=start_date, end=end_date, freq='H')
        lmp_values = 50 + 10 * np.sin(np.arange(len(date_rng)))
        df = pd.DataFrame({
            "datetime": date_rng,
            "LMP": lmp_values
        })

        fig = px.line(df, x="datetime", y="LMP", title=f"{market} LMP for {node}")
        st.plotly_chart(fig, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=f"{node}_{market}_LMP_{start_date}_to_{end_date}.csv",
            mime="text/csv",
        )
    except Exception:
        st.error("Failed to fetch or render data. See details below:")
        st.text(traceback.format_exc())
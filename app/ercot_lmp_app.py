import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import traceback
from io import StringIO
from datetime import date, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="ERCOT Price Viewer", layout="wide")
st.title("ERCOT Price Viewer")

# --- Session State Initialization ---
if 'ercot_access_token' not in st.session_state:
    st.session_state.ercot_access_token = None

# --- ERCOT API Communication ---

def get_ercot_token(username, password):
    """
    Get an access token from the ERCOT API using the ROPC flow.
    """
    # This URL is taken directly from the ERCOT example
    auth_url = (
        "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
        f"?username={username}"
        f"&password={password}"
        "&grant_type=password"
        "&scope=openid+fec253ea-0d06-4272-a5e6-b478baeecd70+offline_access"
        "&client_id=fec253ea-0d06-4272-a5e6-b478baeecd70"
        "&response_type=id_token"
    )

    try:
        auth_response = requests.post(auth_url)
        auth_response.raise_for_status()  # Will raise an exception for HTTP error codes
        access_token = auth_response.json().get("access_token")
        if access_token:
            st.session_state.ercot_access_token = access_token
            return access_token
        else:
            st.error("Authentication successful, but no access token was returned.")
            st.json(auth_response.json()) # Display the full response for debugging
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get ERCOT token: {e}")
        # If the response has content, it might contain a useful error message from ERCOT
        if e.response:
            st.error("ERCOT's Response:")
            st.json(e.response.json())
        return None

def process_ercot_response(data, price_column_name):
    """
    A generic function to process the JSON response from ERCOT report APIs.
    It creates, cleans, and sorts a DataFrame.
    """
    total_records = data.get("_meta", {}).get("totalRecords", 0)
    if total_records == 0:
        st.warning("API reported 0 total records for the given parameters.")
        return pd.DataFrame()

    column_names = [f["name"] for f in data.get("fields", []) if "name" in f]
    records = data.get("data", [])

    if not column_names or not records:
        st.error("API response was missing column names ('fields') or data records ('data').")
        return pd.DataFrame()

    df = pd.DataFrame(records, columns=column_names)

    if "deliveryDate" in df.columns and "hourEnding" in df.columns and price_column_name in df.columns:
        try:
            df[price_column_name] = pd.to_numeric(df[price_column_name], errors='coerce')
            df['deliveryDate_dt'] = pd.to_datetime(df['deliveryDate'], errors='coerce')
            df['hour'] = df['hourEnding'].astype(str).str.split(':').str[0].astype(int)
            df['datetime'] = df['deliveryDate_dt'] + pd.to_timedelta(df['hour'] - 1, unit='h')
            df.dropna(subset=['datetime', price_column_name], inplace=True)
            df.drop(columns=['deliveryDate_dt', 'hour'], inplace=True)
            df.sort_values(by='datetime', inplace=True)
            return df
        except Exception as e:
            st.error(f"Failed to process data columns. Error: {e}")
            return pd.DataFrame()
    else:
        st.error(f"Necessary columns ('deliveryDate', 'hourEnding', '{price_column_name}') not found in data.")
        st.write("Available columns:", df.columns.tolist())
        return pd.DataFrame()

def fetch_dam_lmp(access_token, subscription_key, node, start_date, end_date, page_size=5000):
    """Fetch DAM hourly LMP data from ERCOT API."""
    url = "https://api.ercot.com/api/public-reports/np4-183-cd/dam_hourly_lmp"
    headers = {"Authorization": f"Bearer {access_token}", "Ocp-Apim-Subscription-Key": subscription_key}
    params = {
        "deliveryDateFrom": start_date.strftime("%Y-%m-%d"),
        "deliveryDateTo": end_date.strftime("%Y-%m-%d"),
        "busName": node, "size": page_size, "sort": "deliveryDate", "dir": "asc"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return process_ercot_response(response.json(), 'LMP')
    except requests.exceptions.RequestException as e:
        st.error(f"API Request failed: {e}")
        if e.response: st.json(e.response.json())
        return pd.DataFrame()
    
def fetch_rtm_lmp(access_token, subscription_key, node, start_date, end_date, page_size=5000):
    """Fetch RTM hourly LMP data from ERCOT API."""
    url = "https://api.ercot.com/api/public-reports/np6-787-cd/lmp_electrical_bus"
    headers = {"Authorization": f"Bearer {access_token}", "Ocp-Apim-Subscription-Key": subscription_key}
    params = {
        "SCEDTimestampFrom": start_date.strftime("%Y-%m-%d"),
        "SCEDTimestampTo": end_date.strftime("%Y-%m-%d"),
        "electricalBus": node, "size": page_size, "sort": "SCEDTimestamp", "dir": "asc"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return process_ercot_response(response.json(), 'LMP')
    except requests.exceptions.RequestException as e:
        st.error(f"API Request failed: {e}")
        if e.response: st.json(e.response.json())
        return pd.DataFrame()

def fetch_dam_spp(access_token, subscription_key, settlement_point, start_date, end_date, page_size=5000):
    """Fetch DAM Settlement Point Prices from ERCOT API."""
    url = "https://api.ercot.com/api/public-reports/np4-190-cd/dam_stlmnt_pnt_prices"
    headers = {"Authorization": f"Bearer {access_token}", "Ocp-Apim-Subscription-Key": subscription_key}
    params = {
        "deliveryDateFrom": start_date.strftime("%Y-%m-%d"),
        "deliveryDateTo": end_date.strftime("%Y-%m-%d"),
        "settlementPoint": settlement_point, "size": page_size, "sort": "deliveryDate", "dir": "asc"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return process_ercot_response(response.json(), 'settlementPointPrice')
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.text(traceback.format_exc())
        return pd.DataFrame()
    
def fetch_spp(access_token, subscription_key, settlement_point, start_date, end_date, page_size=5000):
    """Fetch Settlement Point Prices from ERCOT API."""
    url = "https://api.ercot.com/api/public-reports/np6-905-cd/spp_node_zone_hub"
    headers = {"Authorization": f"Bearer {access_token}", "Ocp-Apim-Subscription-Key": subscription_key}
    params = {
        "deliveryDateFrom": start_date.strftime("%Y-%m-%d"),
        "deliveryDateTo": end_date.strftime("%Y-%m-%d"),
        "settlementPoint": settlement_point, "size": page_size, "sort": "deliveryDate", "dir": "asc"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return process_ercot_response(response.json(), 'settlementPointPrice')
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.text(traceback.format_exc())
        return pd.DataFrame()

# --- Load Credentials  ---
try:
    ERCOT_USERNAME = st.secrets["ERCOT_USERNAME"]
    ERCOT_PASSWORD = st.secrets["ERCOT_PASSWORD"]
    ERCOT_SUBSCRIPTION_KEY = st.secrets["ERCOT_SUBSCRIPTION_KEY"]
except (FileNotFoundError, KeyError) as e:
    st.error(f"Credential not found in Streamlit secrets: {e}. Please add it to your secrets file.")
    st.stop()

# --- Streamlit UI ---
# --- sidebar inputs ---

st.sidebar.header("Data Selection")

# 1. NEW: A selector to choose which report/API to call
report_type = st.sidebar.selectbox(
    "Select Report Type:",
    ("DAM - LMPs (by Bus)", "DAM - SPP", "RT - SPP", "RTM - LMPs (by Bus)"),
    key="report_selector"
)

# 2. NEW: Dynamic label for the text input
if 'LMP' in report_type:
    input_label = "Enter Bus Name:"
    default_node = "AEEC"
elif 'RT' in report_type:
    input_label = "Enter Settlement Point:"
    default_node = "HB_HOUSTON"
elif 'RTM' in report_type:
    input_label = "Enter Bus Name:"
    default_node = "AEEC"
else: # For SPP
    input_label = "Enter Settlement Point:"
    default_node = "HB_HOUSTON"

location_input = st.sidebar.text_input(input_label, default_node)
start_date = st.sidebar.date_input("Start Date", date.today() - timedelta(days=1))
end_date = st.sidebar.date_input("End Date", date.today() - timedelta(days=1))

# --- Main Application Logic ---
if st.sidebar.button("Fetch Data"):
    # Authenticate if we don't have a token
    if not st.session_state.ercot_access_token:
        with st.spinner('Authenticating with ERCOT...'):
            get_ercot_token(ERCOT_USERNAME, ERCOT_PASSWORD)

    # Proceed only if authentication is successful
    if st.session_state.ercot_access_token:
        df = pd.DataFrame()
        price_column = None
        report_name = ""

        with st.spinner(f"Fetching data for {location_input} from {start_date} to {end_date}..."):
            # 3. NEW: Conditional logic to call the correct function
            if report_type == "DAM - LMPs (by Bus)":
                df = fetch_dam_lmp(
                    st.session_state.ercot_access_token,
                    ERCOT_SUBSCRIPTION_KEY,
                    location_input,
                    start_date,
                    end_date
                )
                price_column = 'LMP'
                report_name = 'LMP'

            elif report_type == "DAM - SPP":
                df = fetch_dam_spp(
                    st.session_state.ercot_access_token,
                    ERCOT_SUBSCRIPTION_KEY,
                    location_input,
                    start_date,
                    end_date
                )
                price_column = 'settlementPointPrice'
                report_name = 'SPP'
        
        # 4. NEW: Common logic for handling the results
        if df.empty:
            st.warning("No data found for the given parameters.")
        else:
            st.subheader(f"Displaying {report_type} for {location_input}")
            st.dataframe(df.head())

            fig = px.line(df, x="datetime", y=price_column, title=f"{report_type} for {location_input}")
            st.plotly_chart(fig, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{location_input}_{report_name}_{start_date}_to_{end_date}.csv",
                mime="text/csv",
            )
    else:
        st.error("Authentication failed. Cannot fetch data.")
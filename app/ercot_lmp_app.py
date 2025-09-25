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

def process_and_normalize_data(df, price_column_name):
    """
    NEW: A flexible function that inspects the DataFrame and creates a standardized 'datetime' column.
    Handles multiple ERCOT report formats.
    """
    if df.empty:
        return pd.DataFrame()

    try:
        # Case 1: Real-time data with a full timestamp column
        if 'SCEDTimestamp' in df.columns:
            st.info("Detected 'SCEDTimestamp' column for real-time data.")
            df['datetime'] = pd.to_datetime(df['SCEDTimestamp'], errors='coerce')
        
        # Case 2: DAM data with separate date and hour ending (e.g., '04:00')
        elif 'deliveryDate' in df.columns and 'hourEnding' in df.columns:
            st.info("Detected 'deliveryDate' and 'hourEnding' columns.")
            df['hour'] = df['hourEnding'].astype(str).str.split(':').str[0].astype(int)
            df['datetime'] = pd.to_datetime(df['deliveryDate'], errors='coerce') + pd.to_timedelta(df['hour'] - 1, unit='h')
        
        # Case 3: RTM data with separate date and delivery hour (e.g., 4)
        elif 'deliveryDate' in df.columns and 'deliveryHour' in df.columns:
            st.info("Detected 'deliveryDate' and 'deliveryHour' columns.")
            df['hour'] = df['deliveryHour'].astype(int)
            df['datetime'] = pd.to_datetime(df['deliveryDate'], errors='coerce') + pd.to_timedelta(df['hour'] - 1, unit='h')
            
        else:
            st.error("Could not find a recognizable timestamp column ('SCEDTimestamp') or date/hour combination.")
            st.write("Available columns:", df.columns.tolist())
            return pd.DataFrame()

        # Standard processing for all cases
        df[price_column_name] = pd.to_numeric(df[price_column_name], errors='coerce')
        df.dropna(subset=['datetime', price_column_name], inplace=True)
        df.sort_values(by='datetime', inplace=True)
        
        # Keep only the essential columns for the final output
        essential_columns = ['datetime', price_column_name] + [col for col in ['settlementPoint', 'busName', 'electricalBus'] if col in df.columns]
        return df[essential_columns]

    except Exception as e:
        st.error(f"Failed during data normalization. Error: {e}")
        return pd.DataFrame()
    
def resample_to_hourly_average(df, price_column_name):
    """
    Resamples a DataFrame with a 'datetime' column to hourly frequency,
    calculating the mean of the specified price column.
    """
    st.info("Resampling 15-minute data to hourly averages...")
    if df.empty or 'datetime' not in df.columns:
        return pd.DataFrame()
    
    # Set 'datetime' as the index to perform time-series resampling
    df_resampled = df.set_index('datetime')
    
    # Resample to hourly ('H') frequency and calculate the mean
    df_resampled = df_resampled[price_column_name].resample('H').mean().reset_index()
    
    return df_resampled
    
def fetch_api_data(url, headers, params, price_column):
    """A generic function to fetch and process data from an ERCOT endpoint."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
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
        return process_and_normalize_data(df, price_column)

    except requests.exceptions.RequestException as e:
        st.error(f"API Request failed: {e}")
        if e.response: st.json(e.response.json())
        return pd.DataFrame()
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

report_type = st.sidebar.selectbox(
    "Select Report Type:",
    ("DAM - LMPs (by Bus)", "DAM - SPP", "RTM - SPP", "RTM - LMPs (by Bus)"),
    key="report_selector"
)

if "LMP" in report_type:
    input_label = "Enter Electrical Bus:"
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
        url = ""
        params = {}
        needs_hourly_resampling = False
        headers = {"Authorization": f"Bearer {st.session_state.ercot_access_token}", "Ocp-Apim-Subscription-Key": ERCOT_SUBSCRIPTION_KEY}

        with st.spinner(f"Fetching data for {location_input} from {start_date} to {end_date}..."):
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            if report_type == "DAM - LMPs (by Bus)":
                price_column = 'LMP'
                report_name = 'DAM_LMP'
                url = "https://api.ercot.com/api/public-reports/np4-183-cd/dam_hourly_lmp"
                params = {"deliveryDateFrom": start_str, "deliveryDateTo": end_str, "busName": location_input, "size": 5000}

            elif report_type == "DAM - SPP":
                price_column = 'settlementPointPrice'
                report_name = 'DAM_SPP'
                url = "https://api.ercot.com/api/public-reports/np4-190-cd/dam_stlmnt_pnt_prices"
                params = {"deliveryDateFrom": start_str, "deliveryDateTo": end_str, "settlementPoint": location_input, "size": 5000}

            elif report_type == "RTM - LMPs (by Bus)":
                price_column = 'LMP'
                report_name = 'RTM_LMP'
                url = "https://api.ercot.com/api/public-reports/np6-787-cd/lmp_electrical_bus"
                params = {"SCEDTimestampFrom": start_str, "SCEDTimestampTo": end_str, "electricalBus": location_input, "size": 5000}

            elif report_type == "RTM - SPP":
                price_column = 'settlementPointPrice'
                report_name = 'RTM_SPP_Avg'
                url = "https://api.ercot.com/api/public-reports/np6-905-cd/spp_node_zone_hub"
                params = {"deliveryDateFrom": start_str, "deliveryDateTo": end_str, "settlementPoint": location_input, "size": 5000}
                needs_hourly_resampling = True
            
            if url:
                df = fetch_api_data(url, headers, params, price_column)
        
        if not df.empty and needs_hourly_resampling:
            df = resample_to_hourly_average(df, price_column)

        if df.empty:
            st.warning("No data found or processed for the given parameters.")
        else:
            st.subheader(f"Displaying {report_type} for {location_input}")
            graph_title = f"{report_type} for {location_input}"
            if needs_hourly_resampling:
                graph_title = f"Hourly Average {report_type} for {location_input}"
            st.dataframe(df)

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
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from IPython.display import display, HTML
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pc
import streamlit as st
from fredapi import Fred
import yfinance as yf

# Load variables from .env into the system environment
load_dotenv()

# Retrieve the key
api_key = os.getenv('FRED_API_KEY')

# Initialize the FRED client
if api_key:
    fred = Fred(api_key=api_key)
else:
    raise ValueError("FRED_API_KEY not found in environment variables.")


MYDICT = {
    "DGS1MO": ["fred", "1-Month US Treasury Yield", "Rates", "Daily"],
    "DGS3MO": ["fred", "3-Month US Treasury Yield", "Rates", "Daily"],
    "DGS6MO": ["fred", "6-Month US Treasury Yield", "Rates", "Daily"],
    "DGS1": ["fred", "1 Year US Treasury Yield", "Rates", "Daily"],
    "DGS2": ["fred", "2 Year US Treasury Yield", "Rates", "Daily"],
    "DGS3": ["fred", "3 Year US Treasury Yield", "Rates", "Daily"],
    "DGS5": ["fred", "5 Year US Treasury Yield", "Rates", "Daily"],
    "DGS7": ["fred", "7 Year US Treasury Yield", "Rates", "Daily"],
    "DGS10": ["fred", "10 Year US Treasury Yield", "Rates", "Daily"],
    "DGS20": ["fred", "20 Year US Treasury Yield", "Rates", "Daily"],
    "DGS30": ["fred", "30 Year US Treasury Yield", "Rates", "Daily"],
    "DFEDTARU": ["fred", "Federal Funds Target Range - Upper Limit", "Rates", "Daily"],
    "SOFR": ["fred", "Secured Overnight Financing Rate", "Rates", "Daily"],
    "A191RL1Q225SBEA": ["fred", "Real Gross Domestic Product", "Macro", "Quarterly"],
    "CPIAUCSL": ["fred", "CPI for All Urban Consumers", "Macro", "Monthly"],
    "PCEPI": ["fred", "Personal Consumption Expenditures Price Index", "Macro", "Monthly"],
    "PAYEMS": ["fred", "Total Nonfarm Employees", "Macro", "Monthly"],
    "ICSA": ["fred", "Initial Jobless Claims", "Macro", "Weekly"],
    "UNRATE": ["fred", "Unemployment Rate", "Macro", "Monthly"],
    "T5YIFR": ["fred", "5Y5Y Forward Inflation Expectation Rate", "Macro", "Daily"],
    "BAMLH0A0HYM2EY": ["fred", "BofA US High Yield Index Effective Yield", "Credit", "Daily"],
    "BAMLC0A0CMEY": ["fred", "Bofa US Investment Grade Index Effective Yield", "Credit", "Daily"],
    "^GSPC": ["yf", "S&P 500", "Equities", "Daily"],
    "^VIX": ["yf", "CBOE Volatility Index", "Equities", "Daily"],
    "^DJI": ["yf", "Dow Jones Industrial Average", "Equities", "Daily"],
    "^IXIC": ["yf", "NASDAQ Composite", "Equities", "Daily"],
    "^FTSE": ["yf", "FTSE 100", "Equities", "Daily"],
    "^N225": ["yf", "Nikkei 225", "Equities", "Daily"],
    "SI=F": ["yf", "CME Silver Futures", "Commodities", "Daily"],
    "GC=F": ["yf", "CME Gold Futures", "Commodities", "Daily"],
    "BZ=F": ["yf", "Brent Crude Oil Last Day Financ", "Commodities", "Daily"],
    "CL=F": ["yf", "WTI Crude Oil", "Commodities", "Daily"],
    "EURUSD=X": ["yf", "EUR/USD", "FX", "Daily"],
    "USDJPY=X": ["yf", "USD/JPY", "FX", "Daily"],
    "GBPUSD=X": ["yf", "GBP/USD", "FX", "Daily"],
}

TODAY = date.today()
CHART_START_DATE = "2025-01-01"


def get_fred(_fred_client, series_ids):
    df = []
    for code in series_ids:
        for attempt in range(3):
            try:
                series = fred.get_series(code)
                series_titled = series.rename(code).to_frame()
                df.append(series_titled)
                print(code, "fetched.", end=' ')
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                else:
                    print("Failed to fetch", code)

    fred_df = pd.concat(df, axis=1).dropna(how="all")                 # Joins all individual series DataFrames side by side, so that each series becomes a column
    print("Retrieval of FRED data complete.")

    return fred_df

def get_yf(tickers):
    
    yf_df_all = yf.download(tickers, period="5y")
    print("Retrieval of Yahoo Finance data complete.")

    return yf_df_all

@st.cache_data(ttl=3600)
def load_all_data():
    series_ids = [key for key, val in MYDICT.items() if val[0] == "fred"]
    tickers = [key for key, val in MYDICT.items() if val[0] == "yf"]
    
    fred_df = get_fred(fred, series_ids)
    yf_df_all = yf.download(tickers, period="5y")
    yf_df_close = yf_df_all["Close"]
    return fred_df.join(yf_df_close)
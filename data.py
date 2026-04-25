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

# series_ids = [key for key, val in mydict.items() if val[0] == "fred"]
# fred_df = get_fred(fred, series_ids)

def get_yf(tickers):
    
    yf_df_all = yf.download(tickers, period="5y")
    print("Retrieval of Yahoo Finance data complete.")

    return yf_df_all
# tickers = [key for key, val in mydict.items() if val[0] == "yf"]
# yf_df_all = get_yf(tickers)

@st.cache_data(ttl=3600)
def load_all_data():
    series_ids = [key for key, val in MYDICT.items() if val[0] == "fred"]
    tickers = [key for key, val in MYDICT.items() if val[0] == "yf"]
    
    fred_df = get_fred(fred, series_ids)
    yf_df_all = yf.download(tickers, period="5y")
    yf_df_close = yf_df_all["Close"]
    combined_df = fred_df.join(yf_df_close)
    return combined_df

combined_df = load_all_data()

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option('display.float_format', '{:,.2f}'.format)
   


def get_yieldcurves():
    treasuries = [key for key, val in MYDICT.items() if "US Treasury Yield" in str(val[1])]
    
    labels_long = [val[1] for key, val in MYDICT.items() if "US Treasury Yield" in str(val[1])]
    labels_short = []
    for label in labels_long:
        label_short = label.replace(" US Treasury Yield", "").replace("-Month","mo").replace(" Year", "Y")
        labels_short.append(label_short)

    prev_1m = TODAY + relativedelta(months=-1)
    prev_1y = TODAY + relativedelta(years=-1)
    prev_2y = TODAY + relativedelta(years=-2)
    prev_3y = TODAY + relativedelta(years=-3)
    ref_dates = [TODAY, prev_1m, prev_1y, prev_2y, prev_3y]
    ref_dates = [pd.Timestamp(d) for d in ref_dates]

    curves = combined_df[treasuries].asof(ref_dates)

    fig = go.Figure()

    # Each row = one curve (one date)
    for maturity in curves.index:
        fig.add_trace(
            go.Scatter(
                x=labels_short,                # maturities
                y=curves.loc[maturity],        # yields
                mode='lines+markers',
                name=str(maturity.date()),
                visible="legendonly" if maturity.date() != TODAY else True,
                hovertemplate='%{x}, %{y:.2f}%'
            )
        )

    fig.add_annotation(x=4, y=4,
            text=f"Latest 2Y: {combined_df['DGS2'].asof(pd.Timestamp(TODAY)):.2f}%",
            showarrow=False,
            yshift=218,
            bgcolor="#636EFA",
            )
    
    fig.add_annotation(x=8, y=4,
            text=f"Latest 10Y: {combined_df['DGS10'].asof(pd.Timestamp(TODAY)):.2f}%",
            showarrow=False,
            yshift=218,
            bgcolor="#636EFA"
            )
        
    
    fig.update_layout(
        title="US Treasury Yield Curves (Latest to L3Y)",
        xaxis_title="Maturity",
        yaxis_title="Yield (%)",
        template="plotly_dark"
    )
    return fig




# 2Y10Y Spread
def get_twoten():
    twoten = pd.DataFrame({})
    twoten["2Y10Y Yield Spread"] = combined_df["DGS10"] - combined_df["DGS2"]
    twoten["Fed Funds Rate - Upper Limit"] = combined_df["DFEDTARU"]
    twoten_clean = twoten.dropna()
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=twoten_clean.index,          
            y=twoten_clean["2Y10Y Yield Spread"],
            mode='lines',
            name="2Y10Y Spread",
            hovertemplate='%{x}, %{y:.2f}%'
        )
    )

    fig.add_hline(y=0, line_dash="solid", line_color="grey", line_width=1)

    fig.add_annotation(xref="paper",
            x=1.035, y=twoten_clean['2Y10Y Yield Spread'].asof(pd.Timestamp(TODAY)),
            text=f"{twoten_clean['2Y10Y Yield Spread'].asof(pd.Timestamp(TODAY)):.2f}%",
            showarrow=False,
            yshift=0,
            bgcolor="#636EFA"
            )

    fig.update_layout(
        title="2Y10Y Spread",
        xaxis_title="Date",
        yaxis_title="%",
        xaxis=dict(range=[CHART_START_DATE,TODAY]),
        yaxis=dict(range=[-0.5,1]),
        template="plotly_dark",
        showlegend=True
    )
    return fig





# US CPI YoY % Change

def get_cpi():

    cpi_series = {
        "CPI": combined_df["CPIAUCSL"].dropna(),
        "PCE": combined_df["PCEPI"].dropna()
    }
    fed_rate = pd.DataFrame(combined_df["DFEDTARU"]).dropna()

    all_dfs = []

    for label, series in cpi_series.items():
        yoy = series.pct_change(12) * 100
        yoy.name = f"{label} YoY (%)"
        all_dfs.append(yoy.to_frame())
    yoy_df = pd.concat(all_dfs, axis=1).sort_index()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=yoy_df.index,          
            y=yoy_df["CPI YoY (%)"],
            mode='lines',
            name="CPI YoY Change",
            hovertemplate='%{x}, %{y:.2f}%'
        )
    )
    fig.add_trace(
        go.Scatter(
            x=yoy_df.index,          
            y=yoy_df["PCE YoY (%)"],
            mode='lines',
            name="PCE YoY Change",
            hovertemplate='%{x}, %{y:.2f}%'
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fed_rate.index,
            y=fed_rate["DFEDTARU"],
            mode="lines",
            name="Fed Funds Rate",
            hovertemplate='%{x}, %{y:.2f}%'
        )
    )
    fig.update_layout(
        title="US Annual Inflation",
        xaxis_title="Date",
        yaxis_title="%",
        xaxis=dict(range=[CHART_START_DATE,TODAY]),
        yaxis=dict(range=[0,5]),
        template="plotly_dark"
    )
    return fig

# US Non-farm Payrolls and Unemployment

def get_jobs():   

    payrolls = combined_df["PAYEMS"].dropna()
    unrate = combined_df["UNRATE"].dropna()

    months = len(payrolls)
    rows = []
    for i in range(months+1):
        date_latest = pd.Timestamp(TODAY + relativedelta(months=-1-i, day=1))
        date_1m = pd.Timestamp(TODAY + relativedelta(months=-2-i, day=1))
        latest = payrolls.asof(date_latest)
        last_1m = payrolls.asof(date_1m)
        diff = latest - last_1m
        rows.append({"Date": date_latest, "Change": diff})
    payrolls_df = pd.DataFrame(rows).set_index("Date").sort_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=payrolls_df.index,          
            y=payrolls_df["Change"],
            name="Non-farm Payrolls",
            marker_color=["green" if v > 0 else "red" for v in payrolls_df["Change"]]
        ), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=unrate.index,
            y=unrate.values,
            name="Unemployment Rate (%)",
            line_color="blue",
            hovertemplate='%{x}, %{y:.2f}%'
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Thousands of Persons", secondary_y=False)
    fig.update_yaxes(title_text="Unemployment Rate %", range=[3,5], showgrid=False, secondary_y=True)   
    fig.update_layout(
        title="Monthly Change in Non-farm Payrolls, and Unemployment Rate",
        xaxis=dict(range=[CHART_START_DATE,TODAY]),
        yaxis=dict(range=[-200,300]),
        xaxis_title="Date",
        yaxis_title="Thousands of Persons",
        template="plotly_dark",
        legend=dict(yanchor="top", y=1.3, xanchor="left", x=0.4)
    )

    return fig

# US GDP

def get_gdp():
    gdp = combined_df["A191RL1Q225SBEA"].dropna().sort_index()
    quarters = len(gdp)
    rows = []
    for i in range(quarters-1):
        # date_latest = pd.Timestamp(TODAY + relativedelta(day=1))
        # date_lq = pd.Timestamp(TODAY + relativedelta(months=-4*i, day=1))
        latest = gdp.iloc[-1-i]
        date_latest = gdp.index[-1-i]
        rows.append({"Date": date_latest, "GDP": latest})
    gdp_df = pd.DataFrame(rows).set_index("Date").sort_index()
    
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=gdp_df.index,          
            y=gdp_df["GDP"],
            mode='lines',
            name="GDP Growth Rate",
            hovertemplate='%{x}, %{y:.2f}%'
        )
    )
    fig.add_annotation(xref="paper",
        x=1.035, y=gdp_df['GDP'].asof(pd.Timestamp(TODAY)),
        text=f"{gdp_df['GDP'].asof(pd.Timestamp(TODAY)):.2f}%",
        showarrow=False,
        yshift=0,
        bgcolor="#636EFA"
        )
    fig.update_layout(
            title="Real GDP Growth Rate (QoQ)",
            xaxis_title="Date",
            yaxis_title="%",
            xaxis=dict(range=[CHART_START_DATE,TODAY]),
            yaxis=dict(range=[-2,5]),
            template="plotly_dark",
            showlegend=True
        )
    return fig
    

def get_equities():
    
    rebase_boolean = True
    rebase_date = CHART_START_DATE                             # edit this to change rebase and chart zoom date
    all_indices = []
    indices = {
            "S&P 500": combined_df["^GSPC"].dropna(),
            "FTSE 100": combined_df["^FTSE"].dropna(),
            "Nikkei 225": combined_df["^N225"].dropna()
        }
    
    for label, index in indices.items():
        level = index
        level.name = f"{label}"
        base_value = index.asof(pd.Timestamp(rebase_date)) if rebase_boolean == True else 100
        rebased = index/base_value*100
        rebased.name = f"{label} Rebased"
        all_indices.append(level.to_frame())
        all_indices.append(rebased.to_frame())
    all_indices_df = pd.concat(all_indices, axis=1).sort_index()
    
    fig = go.Figure()

    for col in all_indices_df.columns:
        if "Rebased" in str(col):
            non_rebase_col = str(col).replace(" Rebased", "")
            fig.add_trace(
            go.Scatter(
                x=all_indices_df.index,          
                y=all_indices_df[col].values,
                customdata=all_indices_df[non_rebase_col].values,
                mode='lines',
                name=f"{col} | <b>Latest: {all_indices_df[non_rebase_col].asof(pd.Timestamp(TODAY)):.2f}<b>",
                hovertemplate='%{x}: %{customdata:.2f}'
                )
            )
        # fig.add_annotation(xref="paper",
        #     x=1.04, y=all_indices_df[col].asof(pd.Timestamp(TODAY)),
        #     text=f"{all_indices_df[col].asof(pd.Timestamp(TODAY)):.2f}",
        #     showarrow=False,
        #     yshift=0
        #     )
        
    fig.update_layout(
            title=f"Equity Indices, Rebased as of {rebase_date}" if rebase_boolean == True else "Equity Indices",

            xaxis_title="Date",
            yaxis_title="Value",
            xaxis=dict(range=[rebase_date,TODAY]),
            # yaxis=dict(range=[60,220]),
            template="plotly_dark",
            showlegend=True,
            legend=dict(yanchor="top", y=1.3, xanchor="left", x=0.25)
        )
    fig.update_yaxes(showticklabels=False)
    return fig

    

# ---- Streamlit layout ----
st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("Macro Dashboard")


# st.plotly_chart(get_yieldcurves(), width='stretch', key="yieldcurves")
# st.plotly_chart(get_twoten(), width='stretch', key="twoten")
# st.plotly_chart(get_cpi(), width='stretch', key="cpi")
# st.plotly_chart(get_gdp(), width='stretch', key="cpi")
# st.plotly_chart(get_jobs(), width='stretch', key="jobs")
# st.plotly_chart(get_equities(), width='stretch', key="equities")


# Header
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center; 
            padding: 1rem 0; border-bottom: 1px solid #333; margin-bottom: 2rem;">
    <div style="color: #888; font-size: 0.85rem;">Last updated: {}</div>
</div>
""".format(datetime.now().strftime("%d %b %Y %r")), unsafe_allow_html=True)

# Columns
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(get_yieldcurves(), width='stretch', key="yieldcurves")
with col2:
    st.plotly_chart(get_twoten(), width='stretch', key="twoten")

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(get_cpi(), width='stretch', key="cpi")
with col4:
    st.plotly_chart(get_gdp(), width='stretch', key="gdp")

col5, col6 = st.columns(2)
with col5:
    st.plotly_chart(get_jobs(), width='stretch', key="jobs")
with col6:
    st.plotly_chart(get_equities(), width='stretch', key="equities")

# python -m streamlit run C:\Users\xavie\NUS\Coding\Dashboard\data.py"
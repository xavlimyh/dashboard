import os
from dotenv import load_dotenv
import pandas as pd
import time
from functools import reduce
from fredapi import Fred
import yfinance as yf
from get_boe import get_boe_series
from get_cnbc import get_cnbc_series
from get_boj import get_boj_series

# Load variables from .env into the system environment
load_dotenv()

# Retrieve the key
api_key = os.getenv('FRED_API_KEY')

# Initialize the FRED client
if api_key:
    fred = Fred(api_key=api_key)
else:
    raise ValueError("FRED_API_KEY not found in environment variables.")

TICKERS = [
#   (sym,                   name,                                                         fmt,              section,          prev_offset, direction, source)
    ("A191RL1Q225SBEA",     "Real GDP QoQ",                                               "pct_1dp",        "US Macro",       1,  1,  "fred"),
    ("CPIAUCSL",            "CPI YoY",                                                    "pct_1dp",        "US Macro",       1, -1,  "fred"),
    ("CPILFESL",            "Core CPI YoY",                                               "pct_1dp",        "US Macro",       1, -1,  "fred"),
    ("PCEPI",               "PCE YoY",                                                    "pct_1dp",        "US Macro",       1, -1,  "fred"),
    ("PCEPILFE",            "Core PCE YoY",                                               "pct_1dp",        "US Macro",       1, -1,  "fred"),
    ("T5YIFR",              "5Y5Y Forward Inflation Expectation Rate",                    "pct_1dp",        "US Macro",       5, -1,  "fred"),
    ("UNRATE",              "Unemployment Rate",                                          "pct_1dp",        "US Macro",       1, -1,  "fred"),
    ("PAYEMS",              "Non-farm Payrolls",                                          "kppl",           "US Macro",       1,  1,  "fred"),
    ("DFEDTARU",            "Fed Funds Rate",                                             "range",          "US Rates",       1, -1,  "fred"),
    ("SOFR",                "SOFR",                                                       "pct_2dp",        "US Rates",       5,  1,  "fred"),
    ("DGS1MO",              "1mo Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS3MO",              "3mo Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS6MO",              "6mo Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"), 
    ("DGS1",                "1Y Treasury",                                                "pct_2dp",        "US Rates",       5,  -1,  "fred"),   
    ("DGS2",                "2Y Treasury",                                                "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS3",                "3Y Treasury",                                                "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS5",                "5Y Treasury",                                                "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS7",                "7Y Treasury",                                                "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS10",               "10Y Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS20",               "20Y Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("DGS30",               "30Y Treasury",                                               "pct_2dp",        "US Rates",       5,  -1,  "fred"),
    ("US2S10S",             "US 2s10s Spread",                                            "pct_2dp",        "US Rates",       5,  1,  "derived"),
    ("USYIELDCURVE",        "Yield Curve",                                                "yc",             "US Rates",       0,  1,  "derived"),      
    ("ECBDFR",              "ECB Deposit Facility Rate",                                  "pct_2dp",        "Euro Rates",     5, -1,  "fred"),
    ("DE2Y",                "German 2Y Bund",                                             "pct_2dp",        "Euro Rates",     5, -1,  "cnbc"),
    ("DE10Y",               "German 10Y Bund",                                            "pct_2dp",        "Euro Rates",     5, -1,  "cnbc"), 
    ("DE2S10S",             "German 2s10s Spread",                                        "pct_2dp",        "Euro Rates",     5,  1,  "derived"),
    ("IUDBEDR",             "BoE Bank Rate",                                              "pct_2dp",        "UK Rates",       5, -1,  "boe"),
    ("IUDSOIA",             "SONIA",                                                      "pct_2dp",        "UK Rates",       5, -1,  "boe"),
    ("GB1Y",                "1Y Gilt",                                                    "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),      
    ("GB2Y",                "2Y Gilt",                                                    "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),     
    ("GB3Y",                "3Y Gilt",                                                    "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),   
    ("GB5Y",                "5Y Gilt",                                                    "pct_2dp",        "UK Rates",       5, -1,  "cnbc"), 
    ("GB10Y",               "10Y Gilt",                                                   "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),
    ("GB20Y",               "20Y Gilt",                                                   "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),
    ("GB30Y",               "30Y Gilt",                                                   "pct_2dp",        "UK Rates",       5, -1,  "cnbc"),
    ("UK2S10S",             "UK 2s10s Spread",                                            "pct_2dp",        "UK Rates",       5, -1,  "derived"),
    ("JPNRGDPEXP",          "Japan Real GDP QoQ",                                         "pct_1dp",        "Japan Macro",    1,  1,  "fred"),    
    ("FM01_STRDCLUCON",     "Japan Uncollateralised Overnight Call Rate",                 "pct_2dp",        "Japan Rates",   5, -1,  "boj"),
    ("JP2Y",                "2Y Japan Government Bond",                                   "pct_2dp",        "Japan Rates",   5, -1,  "cnbc"),
    ("JP10Y",               "10Y Japan Government Bond",                                  "pct_2dp",        "Japan Rates",   5, -1,  "cnbc"),
    ("JP30Y",               "30Y Japan Government Bond",                                  "pct_2dp",        "Japan Rates",   5, -1,  "cnbc"),    
    ("JP2S10S",             "Japan 2s10s Spread",                                         "pct_2dp",        "Japan Rates",   5,  1,  "derived"),
    ("JP2S30S",             "Japan 2s30s Spread",                                         "pct_2dp",        "Japan Rates",   5,  1,  "derived"),    
    ("BAMLC0A0CMEY",        "Bofa US Corporate Index Effective Yield",                    "pct_2dp",        "US Credit",      5,  -1,  "fred"),        
    ("BAMLH0A0HYM2EY",      "BofA US High Yield Index Effective Yield",                   "pct_2dp",        "US Credit",      5,  -1,  "fred"),
    ("^GSPC",               "S&P 500",                                                    "idx",            "Indices",       5,  1,  "yf"),
    ("^VIX",                "VIX",                                                        "idx_twodp",      "Indices",       5,  1,  "yf"),
    ("^IXIC",               "NASDAQ Composite",                                           "idx",            "Indices",       5,  1,  "yf"),
    ("^DJI",                "Dow Jones Industrial Average",                               "idx",            "Indices",       5,  1,  "yf"),
    ("^FTSE",               "FTSE 100",                                                   "idx",            "Indices",       5,  1,  "yf"),       
    ("^STOXX",              "STOXX 600",                                                  "idx_twodp",      "Indices",       5,  1,  "yf"),  
    ("^GDAXI",              "DAX 40",                                                     "idx",            "Indices",       5,  1,  "yf"),
    ("^N225",               "Nikkei 225",                                                 "idx",            "Indices",       5,  1,  "yf"),
    ("^HSI",                "Hang Seng Index",                                            "idx",            "Indices",       5,  1,  "yf"),
    ("000001.SS",           "Shanghai Composite Index",                                   "idx",            "Indices",       5,  1,  "yf"),
    ("^KS11",               "KOSPI",                                                      "idx",            "Indices",       5,  1,  "yf"),
    ("^AXJO",               "ASX 200",                                                    "idx",            "Indices",       5,  1,  "yf"),
    ("^STI",                "Straits Times Index",                                        "idx",            "Indices",       5,  1,  "yf"),
    ("NVDA",                "NVDA",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),
    ("AAPL",                "AAPL",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),
    ("GOOG",                "GOOG",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),
    ("MSFT",                "MSFT",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),
    ("AMZN",                "AMZN",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),   
    ("META",                "META",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),      
    ("MAQ.AX",              "ASX: MAQ",                                                   "idx_twodp",      "Equities",       5,  1,  "yf"),
    ("SNPS",                "SNPS",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"), 
    ("SPGI",                "SPGI",                                                       "idx_twodp",      "Equities",       5,  1,  "yf"),   
    ("DX-Y.NYB",            "DXY",                                                        "idx_twodp",      "FX",             5,  1,  "yf"),    
    ("EURUSD=X",            "EURUSD",                                                     "idx_twodp",      "FX",             5,  1,  "yf"),
    ("GBPUSD=X",            "GBPUSD",                                                     "idx_twodp",      "FX",             5,  1,  "yf"),
    ("USDJPY=X",            "USDJPY",                                                     "idx_twodp",      "FX",             5,  1,  "yf"),
    ("USDCNY=X",            "USDCNY",                                                     "idx_twodp",      "FX",             5,  1,  "yf"),
    ("USDSGD=X",            "USDSGD",                                                     "idx_twodp",      "FX",             5,  1,  "yf"),    
    ("GC=F",                "CME Gold Futures",                                           "idx",            "Commodities",    5,  1,  "yf"),
    ("SI=F",                "CME Silver Futures",                                         "idx_twodp",      "Commodities",    5,  1,  "yf"),
    ("BZ=F",                "Brent Crude Oil Futures",                                    "idx_twodp",      "Commodities",    5,  1,  "yf"),
    ("CL=F",                "WTI Crude Oil Futures",                                      "idx_twodp",      "Commodities",    5,  1,  "yf")
]

def get_fred(_fred_client, fred_ids):
    df = []
    for code in fred_ids:
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
    print(f"{len(fred_ids)} FRED queries complete.")
    return fred_df

def get_yf(yf_ids):
    yf_df_all = yf.download(yf_ids, period="5y")
    print(f"{len(yf_ids)} Yahoo Finance queries complete.")
    yf_df_close = yf_df_all["Close"]
    return yf_df_close

def get_econ_cal():                      # Uses yfinance, start date by default set as today, end date is (today+7 days)
    all_pages = []
    cal = pd.DataFrame()
    empty = False
    offset = 0
    while empty == False:
        page = yf.Calendars().get_economic_events_calendar(limit=100, offset=offset)
        if page.empty:
            empty = True
        else:
            offset += 100
            all_pages.append(page)
    cal = pd.concat(all_pages)
    cal["Event"] = cal.index
    cal = cal.set_index("Event Time")
    cal = cal.sort_index()
    cal = cal[["Event", "Region", "For", "Actual", "Expected", "Last", "Revised"]]
    return cal

def get_cnbc(cnbc_ids):
    print(f"{len(cnbc_ids)} CNBC queries complete.")
    return get_cnbc_series(cnbc_ids)

def get_boe(boe_ids):
    print(f"{len(boe_ids)} BoE queries complete.")
    return get_boe_series(boe_ids)

def get_boj(boj_ids):
    print(f"{len(boj_ids)} BoJ queries complete.")
    return get_boj_series(boj_ids)

# @st.cache_data(ttl=3600)
def load_all_data():
    fred_ids = [sym for sym, name, fmt, section, prev_offset, direction, source in TICKERS if source == "fred"]
    yf_ids = [sym for sym, name, fmt, section, prev_offset, direction, source in TICKERS if source == "yf"]
    boe_ids = [sym for sym, name, fmt, section, prev_offset, direction, source in TICKERS if source == "boe"]
    cnbc_ids = [sym for sym, name, fmt, section, prev_offset, direction, source in TICKERS if source == "cnbc"]
    boj_ids = [sym for sym, name, fmt, section, prev_offset, direction, source in TICKERS if source == "boj"]
    id_count = len(fred_ids) + len(yf_ids) + len(boe_ids) + len(cnbc_ids) + len(boj_ids)

    print(id_count, "tickers queried.")
    fred_df = get_fred(fred, fred_ids)
    yf_df = get_yf(yf_ids)
    boe_df = get_boe(boe_ids)
    cnbc_df = get_cnbc(cnbc_ids)
    boj_df = get_boj(boj_ids)
    print("All data sources queried.\nLoading dashboard...")

    data_frames = [fred_df, yf_df, boe_df, cnbc_df, boj_df]
    for name, df in [("fred", fred_df), ("yf", yf_df), ("boe", boe_df), ("cnbc", cnbc_df), ("boj", boj_df)]:
        print(f"{name}: dtype={df.index.dtype}, tz={getattr(df.index, 'tz', None)}, sample={df.index[:2].tolist()}")
    df_merged = reduce(lambda left,right: left.join(right), data_frames)
    print(df_merged)

    return df_merged

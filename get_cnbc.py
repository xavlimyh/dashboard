import requests
import pandas as pd
from functools import reduce

def get_chart_data(symbol, time_range="5Y"):
    url = "https://webql-redesign.cnbcfm.com/graphql"
    params = {
        "operationName": "getQuoteChartData",
        "variables": f'{{"symbol":"{symbol}","timeRange":"{time_range}"}}',
        "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"9e1670c29a10707c417a1efd327d4b2b1d456b77f1426e7e84fb7d399416bb6b"}}'
        }
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.cnbc.com/",
        }

    response = requests.get(url, params=params, headers=headers)
    data = response.json()["data"]["chartData"]["priceBars"]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["tradeTime"], format="%Y%m%d%H%M%S").dt.date
    df = df[["Date", "open", "high", "low", "close", "volume"]]
    
    # Cleaning Dataframe
    all_cols = df.copy()
    cols_todrop = ["open", "high", "low", "volume"]
    hist_close = all_cols.drop(columns=cols_todrop)
    hist_close = hist_close.rename(columns={"close": symbol})
    hist_close[symbol] = hist_close[symbol].map(lambda x: x.replace("%", ""))
    hist_close[symbol] = hist_close[symbol].astype(float)

    return hist_close

def get_cnbc_series(symbols):
    data_frames = []
    for symbol in symbols:
        sym_df = get_chart_data(symbol)
        data_frames.append(sym_df)
    df_merged = reduce(lambda left,right: pd.merge(left, right, on="Date", how='outer'), data_frames)
    df_merged.set_index('Date', inplace=True)
    return df_merged



import requests
import pandas as pd
from functools import reduce

def get_boj_series(symbols):

    # Format symbol into db and code parameters from BoJ API
    # In data file, use _ instead of ' to split db and code. Using ' will cause data.py to read code wrong.

    split_sym = []
    for sym in symbols:
        split = str.split(sym, "_")
        split_sym.append(split)

    url = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"

    data_frames = []

    for db, code in split_sym:
        params = {
            "format": "json",
            "lang": "en",
            "db": db,
            "code": code
        }
        response = requests.get(url, params=params)
        data = response.json()
        dates = data["RESULTSET"][0]["VALUES"]["SURVEY_DATES"]
        values = data["RESULTSET"][0]["VALUES"]["VALUES"]

        sym_df = pd.DataFrame({"Date": dates, f"{db}_{code}": values})
        sym_df["Date"] = pd.to_datetime(sym_df["Date"], format="%Y%m%d")
        data_frames.append(sym_df)

    df_merged = reduce(lambda left,right: pd.merge(left,right,on=['Date'], how='outer'), data_frames)
    df_merged.set_index('Date', inplace=True)
    
    return df_merged


import requests
import pandas as pd


test_symbols = ["JPCPI", "JPCPICORE", "JPUNRATE"]

ESTAT_SYMBOLS = {

    "JPCPI": {
        "estat_code": "0004052037",
        "area": "00000", # All Japan
        "cat01": "0001", # All items
        "cat02": "",
        "cat03": "",
        "tab": "1",      # Level
    },

    "JPCPICORE": {
        "estat_code": "0004052037",
        "area": "00000", # All Japan
        "cat01": "0161", # All items excluding fresh food
        "cat02": "",
        "cat03": "",
        "tab": "1",      # Level
    },

    "JPUNRATE": {
        "estat_code": "0003005865",
        "area": "00000", # All Japan
        "cat01": "000",
        "cat02": "08",   # Unemployment
        "cat03": "0",    # Both sexes
        "tab": "02",  
    },

}

def get_estat_jp_series(symbols):

    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    dfs = []

    for sym in symbols:
        estat_sym = ESTAT_SYMBOLS[sym]

        estat_code = estat_sym["estat_code"]
        area = estat_sym["area"]
        cat01 = estat_sym["cat01"]
        cat02 = estat_sym["cat02"]
        cat03 = estat_sym["cat03"]
        tab = estat_sym["tab"]

        params = {
            "appId": "16de145fd48d9605d6abe4dfc91dba66c8e65822",
            "lang": "E",
            "statsDataId": estat_code,
            "cdArea": area,
            "cdCat01": cat01,
            "cdCat02": cat02,
            "cdCat03": cat03,
            "cdTab": tab,
            "metaGetFlg": "Y",
            "cntGetFlg": "N",
            "explanationGetFlg": "Y",
            "annotationGetFlg": "Y",
            "sectionHeaderFlg": "1",
            "replaceSpChars": "0"
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        json_data = response.json()

        stat_data = json_data["GET_STATS_DATA"]["STATISTICAL_DATA"]
        # class_info = stat_data["CLASS_INF"]
        # print(class_info)

        # Observations
        values = stat_data["DATA_INF"]["VALUE"]
        df = pd.DataFrame(values)

        df = df[(df["@time"].astype(str).str[8:10] != "00")   # Filters out annual figures with @time e.g. "2025000000" or "2024100000"
                ]

        # Change time to datetime format; Original time format example: "2026000707"
        df["Date"] = pd.to_datetime(
            df["@time"].astype(str).str[0:4]+df["@time"].astype(str).str[8:10],
            format="%Y%m"
        )

        df = df[["Date", "$"]].rename(columns={"$": sym})  # Keep only Date and relevant column
        df[sym] = pd.to_numeric(df[sym], errors="coerce") # Ensure numeric
        dfs.append(df)

    df_merged = dfs[0]
    for df in dfs[1:]:
        df_merged = df_merged.merge(df, on="Date", how="outer")

    df_merged.set_index('Date', inplace=True)
    print(df_merged)
    return df_merged

get_estat_jp_series(test_symbols)
import requests
import pandas as pd


symbols = ["0004052037"]
def get_estat_jp_series(symbols):

    url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    dfs = []

    for sym in symbols:
        params = {
            "appId": "16de145fd48d9605d6abe4dfc91dba66c8e65822",
            "lang": "E",
            "statsDataId": sym,
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
        class_info = stat_data["CLASS_INF"]
        print(class_info)

        # Observations
        values = stat_data["DATA_INF"]["VALUE"]
        df = pd.DataFrame(values)

        df = df[(df["@time"].astype(str).str[8:10] != "00")   # Filters out annual figures with @time e.g. "2025000000" or "2024100000"
                ]

        # Change time to datetime format; Original time format: 2026000707
        df["Date"] = pd.to_datetime(
            df["@time"].astype(str).str[0:4]+df["@time"].astype(str).str[8:10],
            format="%Y%m"
        )

        # Filters for CPI
        if sym == "0004052037":
            df = df[
                (df["@area"] == "00000") &                       # All Japan
                (df["@tab"] == "1") &                            # 1 = Index, 2 = change from prev period, 3 = YoY change
                (df["@cat01"] == "0001")                         # 0001 = All items
            ]

        # Filters for unemployment
        if sym == "0003005865":
            df = df[
                (df["@tab"] == "02") &
                (df["@cat01"] == "000") &                                      # All industries
                (df["@cat02"] == "08") &                                       # Unemployment
                (df["@cat03"] == "0") &                                        # Both sexes
                (df["@area"] == "00000")                                       # All Japan
            ]

        df = df[["Date", "$"]].rename(columns={"$": sym})  # Keep only Date and relevant column
        df[sym] = pd.to_numeric(df[sym], errors="coerce") # Ensure numeric
        dfs.append(df)

    df_merged = dfs[0]
    for df in dfs[1:]:
        df_merged = df_merged.merge(df, on="Date", how="outer")

    df_merged.set_index('Date', inplace=True)
    print(df_merged)
    return df_merged

get_estat_jp_series(symbols)
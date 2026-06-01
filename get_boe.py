import requests
import pandas as pd
from io import StringIO

def get_boe_series(series_codes, start_date="01/Jan/1975"):
    codes_str = ",".join(series_codes)
    url = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"
    params = {
        "csv.x": "yes",
        "Datefrom": start_date,
        "Dateto": "now",
        "SeriesCodes": codes_str,
        "CSVF": "TN",
        "UsingCodes": "Y"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = requests.get(url, params=params, headers=headers)
    df = pd.read_csv(StringIO(data.text))
    df.columns = df.columns.str.strip()
    df["DATE"] = pd.to_datetime(df["DATE"])
    df.set_index("DATE", inplace=True)
    return df


"""
te_scraper.py
--------------
Scrape the historical time-series chart data from a TradingEconomics
indicator page using Selenium. Defaults to Singapore's GDP Growth Rate
(QoQ): https://tradingeconomics.com/singapore/gdp-growth

How it works
-------------
TradingEconomics renders its historical charts with Highcharts. Once the
page has finished loading, the full series (every point shown on the
chart - for this page that's quarterly GDP growth back to 1975) lives in
the Highcharts JS objects in the browser. Highcharts "point" objects have
circular references (point -> series -> chart -> series...), so they
can't be JSON-serialized directly - this script flattens each series to
plain [timestamp_ms, value] pairs inside the browser via
driver.execute_script() before handing the data back to Python.

As a fallback/supplement, any plain HTML <table> elements on the page are
also captured with pandas.read_html().

Setup
-----
    pip install undetected-chromedriver selenium pandas lxml

You need Google Chrome installed locally. undetected-chromedriver patches
chromedriver to avoid the automation fingerprints that Cloudflare-style
bot checks look for. Plain Selenium tends to get served a "Just a
moment..." interstitial instead of the real page - often a near-empty
page that's little more than a single <iframe> (the challenge widget),
i.e. page source ending in "</iframe></html>" with no chart in sight.

Usage
-----
    python te_scraper.py
    python te_scraper.py --url https://tradingeconomics.com/singapore/gdp-growth-annual
    python te_scraper.py --out gdp.csv
    python te_scraper.py --no-headless     # watch the browser, useful if still blocked
"""

import argparse
import time

import pandas as pd
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_URL = "https://tradingeconomics.com/singapore/gdp-growth"


def build_driver(headless: bool = True) -> uc.Chrome:
    """
    Create an undetected-chromedriver Chrome instance.

    undetected-chromedriver patches around navigator.webdriver, CDP
    artifacts, and other signals that Cloudflare-style bot-management
    checks look for. Pass `headless` to the constructor (rather than a
    raw --headless flag) - it applies extra patches specifically for
    headless mode.
    """
    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return uc.Chrome(options=opts, headless=headless)


def wait_for_challenge_to_clear(driver, timeout: int = 30) -> None:
    """
    Sites behind Cloudflare-style protection often first serve an
    interstitial - a "Just a moment..." page, or a near-empty page
    that's little more than a single <iframe> challenge widget (page
    source ending in "</iframe></html>") - before redirecting to the
    real content. Poll until that's gone, or give up after `timeout`
    seconds (the real page load still gets its own wait afterwards).
    """
    markers = ("just a moment", "checking your browser", "attention required", "verify you are human")
    end = time.time() + timeout
    while time.time() < end:
        title = (driver.title or "").lower()
        source = driver.page_source.lower()
        looks_like_challenge = any(m in title for m in markers) or any(m in source[:2000] for m in markers)
        bare_iframe_shell = "<iframe" in source and "highcharts" not in source
        if not looks_like_challenge and not bare_iframe_shell:
            return
        time.sleep(1)


def dismiss_cookie_banner(driver) -> None:
    """Best-effort: click through the cookie/consent banner if one appears."""
    candidates = [
        (By.ID, "onetrust-accept-btn-handler"),
        (By.CSS_SELECTOR, "button[aria-label='Accept all']"),
        (By.XPATH, "//button[contains(., 'Agree') or contains(., 'Accept') or contains(., 'Got it')]"),
    ]
    for by, sel in candidates:
        try:
            btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((by, sel)))
            btn.click()
            time.sleep(0.5)
            return
        except Exception:
            continue


def extract_highcharts_series(driver):
    """
    Return every series from every Highcharts chart on the page as
    plain {"name": ..., "data": [[timestamp_ms, value], ...]} dicts.
    """
    script = """
        if (typeof Highcharts === 'undefined' || !Highcharts.charts) return null;
        return Highcharts.charts
            .filter(c => c && c.series && c.series.length)
            .map(c => c.series.map(s => ({
                name: s.name,
                data: s.data.map(p => [p.x, p.y])
            })));
    """
    return driver.execute_script(script)


def scrape(url: str = DEFAULT_URL, headless: bool = True, wait: int = 25):
    """Return (time_series_df, list_of_html_tables) for a TE indicator page."""
    driver = build_driver(headless=headless)
    try:
        driver.get(url)
        wait_for_challenge_to_clear(driver)
        dismiss_cookie_banner(driver)

        # The chart container has id="chart" on TE indicator pages
        try:
            WebDriverWait(driver, wait).until(
                EC.presence_of_element_located((By.ID, "chart"))
            )
        except TimeoutException:
            raise RuntimeError(
                f"Timed out waiting for the chart to appear.\n"
                f"  Page title: {driver.title!r}\n"
                f"  Page source (first 300 chars): {driver.page_source[:300]!r}\n"
                f"Try --no-headless to watch what the browser actually loads."
            )
        time.sleep(3)  # let Highcharts finish populating its series data

        charts = extract_highcharts_series(driver)
        if not charts or not charts[0]:
            raise RuntimeError(
                f"Chart container was present but no Highcharts series were "
                f"found (page title: {driver.title!r}). The page may not "
                f"have fully rendered - try increasing `wait`, or run with "
                f"--no-headless to inspect it visually."
            )

        series = charts[0][0]  # first series of the main chart = the history
        df = pd.DataFrame(series["data"], columns=["timestamp_ms", "value"])
        df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
        df = df[["date", "value"]].sort_values("date").reset_index(drop=True)
        df.attrs["series_name"] = series.get("name", "")

        try:
            tables = pd.read_html(driver.page_source)
        except ValueError:
            tables = []

        return df, tables
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a TradingEconomics indicator chart's time series with Selenium"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="TradingEconomics indicator page URL")
    parser.add_argument("--out", default="te_timeseries.csv", help="Output CSV path")
    parser.add_argument(
        "--no-headless", dest="headless", action="store_false",
        help="Run with a visible browser window (useful for debugging)",
    )
    args = parser.parse_args()

    df, tables = scrape(args.url, headless=args.headless)

    print(f"Series: {df.attrs.get('series_name')}")
    print(f"Rows scraped: {len(df)}")
    print(df.tail(10).to_string(index=False))

    df.to_csv(args.out, index=False)
    print(f"\nSaved {len(df)} rows to {args.out}")

    if tables:
        print(f"\nAlso found {len(tables)} plain HTML table(s) on the page.")
        print("Preview of table 0:")
        print(tables[0].head().to_string(index=False))


if __name__ == "__main__":
    main()
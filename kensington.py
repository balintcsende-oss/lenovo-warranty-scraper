import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time


BASE = "https://www.kensington.com"


def get_product_data(sku):

    result = {
        "url": None,
        "images": [],
        "features": [],
        "specs": {}
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ---------- SEARCH ----------
        search_url = f"{BASE}/search/?text={sku}"

        page.goto(search_url, timeout=60000)
        page.wait_for_timeout(3000)

        links = page.query_selector_all("a")

        for a in links:
            href = a.get_attribute("href")
            if href and "/p/" in href:
                result["url"] = BASE + href if href.startswith("/") else href
                break

        if not result["url"]:
            browser.close()
            return result

        # ---------- PRODUCT ----------
        page.goto(result["url"], timeout=60000)
        page.wait_for_timeout(4000)

        # IMAGES
        imgs = page.query_selector_all("[data-zoom-image]")
        for i in imgs:
            src = i.get_attribute("data-zoom-image")
            if src and src not in result["images"]:
                result["images"].append(src)

        # FEATURES
        lis = page.query_selector_all("li")
        for li in lis:
            txt = li.inner_text().strip()
            if len(txt) > 30:
                result["features"].append(txt)

        # SPECS
        rows = page.query_selector_all("table tr")
        for r in rows:
            cols = r.query_selector_all("td, th")
            if len(cols) == 2:
                k = cols[0].inner_text().strip()
                v = cols[1].inner_text().strip()
                result["specs"][k] = v

        browser.close()

    return result


st.title("Kensington PRO scraper")

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("SKU oszlop hiányzik")
        st.stop()

    results = []

    prog = st.progress(0)

    total = len(df)

    for i, sku in enumerate(df["SKU"].dropna()):

        st.write("Processing:", sku)

        data = get_product_data(str(sku))

        row = {
            "SKU": sku,
            "URL": data["url"],
            "FEATURES": " | ".join(data["features"]),
            "SPECS": str(data["specs"])
        }

        for n, img in enumerate(data["images"]):
            row[f"IMAGE_{n+1}"] = img

        results.append(row)

        prog.progress((i+1)/total)

        time.sleep(1)

    out = pd.DataFrame(results)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész ✔")

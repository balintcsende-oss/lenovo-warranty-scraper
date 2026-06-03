import os
os.system("playwright install --with-deps chromium")

import io
import time
import random
import pandas as pd
import streamlit as st

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --------------------------------------------------
# PLAYWRIGHT HTML FETCH
# --------------------------------------------------

def get_html(page, url):
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(random.uniform(1.5, 3.0))
        return page.content(), None
    except Exception as e:
        return None, str(e)


# --------------------------------------------------
# SKU -> PRODUCT URL
# --------------------------------------------------

def search_product_url(page, sku):

    search_url = f"https://www.arukereso.hu/CategorySearch.php?st={sku}"

    html, err = get_html(page, search_url)
    if err:
        return None, err

    soup = BeautifulSoup(html, "html.parser")

    sku_lower = sku.lower()

    for a in soup.find_all("a", href=True):

        href = a["href"]
        title = a.get("title", "")

        if (
            sku_lower in title.lower()
            and "arukereso.hu" in href
            and "-p" in href
        ):
            return href, None

    return None, None


# --------------------------------------------------
# PRODUCT PAGE -> OFFERS
# --------------------------------------------------

def get_prices(page, product_url):

    html, err = get_html(page, product_url)
    if err:
        return [], err

    soup = BeautifulSoup(html, "html.parser")

    results = []

    offers = soup.select("div.optoffer")

    for offer in offers:
        try:
            shop_el = offer.select_one('[itemprop="seller"] [itemprop="name"]')
            price_el = offer.select_one('[itemprop="price"]')

            if not shop_el or not price_el:
                continue

            results.append({
                "shop": shop_el.get_text(strip=True),
                "price": price_el.get("content", "")
            })

        except Exception:
            pass

    return results, None


# --------------------------------------------------
# EXCEL EXPORT
# --------------------------------------------------

def dataframe_to_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Arukereso")

    output.seek(0)
    return output


# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------

st.set_page_config(page_title="Árukereső SKU árlekérő (Playwright)", layout="wide")

st.title("Árukereső SKU árlekérő (Playwright verzió)")

uploaded_file = st.file_uploader("Excel vagy CSV", type=["xlsx", "xls", "csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

    st.dataframe(df.head())

    if "sku" not in df.columns:
        st.error("Nincs sku oszlop!")
        st.stop()

    if st.button("Lekérdezés indítása"):

        all_rows = []
        progress = st.progress(0)
        total = len(df)

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for idx, row in df.iterrows():

                sku = str(row["sku"]).strip()

                product_url, err = search_product_url(page, sku)

                if err:
                    st.warning(f"{sku} → {err}")

                if not product_url:
                    all_rows.append({
                        "sku": sku,
                        "product_url": None,
                        "shop": None,
                        "price": None,
                        "error": err
                    })

                    progress.progress((idx + 1) / total)
                    continue

                offers, err = get_prices(page, product_url)

                if err:
                    st.warning(f"{sku} → {err}")

                if not offers:
                    all_rows.append({
                        "sku": sku,
                        "product_url": product_url,
                        "shop": None,
                        "price": None,
                        "error": err
                    })
                else:
                    for o in offers:
                        all_rows.append({
                            "sku": sku,
                            "product_url": product_url,
                            "shop": o["shop"],
                            "price": o["price"],
                            "error": None
                        })

                time.sleep(random.uniform(2, 5))
                progress.progress((idx + 1) / total)

            browser.close()

        result_df = pd.DataFrame(all_rows)

        st.success(f"Kész! {len(result_df)} sor.")
        st.dataframe(result_df)

        excel_file = dataframe_to_excel(result_df)

        st.download_button(
            "Excel letöltése",
            data=excel_file,
            file_name="arukereso_playwright.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

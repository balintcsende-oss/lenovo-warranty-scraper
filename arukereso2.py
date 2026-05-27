# app.py
# Streamlit alkalmazás:
# - Feltöltesz egy CSV/XLSX fájlt, amiben van egy "sku" oszlop
# - Az app megkeresi a SKU-t az Arukereso oldalon
# - Megnyitja a termékoldalt
# - Letölti az összes bolt árát
# - Exportálható CSV-be

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# ---------------------------------------------------
# Árkereső keresés SKU alapján
# ---------------------------------------------------
def search_product_url(sku):
    search_url = f"https://www.arukereso.hu/?st={quote(str(sku))}"

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        # első találat linkje
        link = soup.select_one("a.product-box__title")

        if link and link.get("href"):
            href = link["href"]

            if href.startswith("/"):
                href = "https://www.arukereso.hu" + href

            return href

    except Exception as e:
        print(f"Hiba SKU keresésnél: {sku} -> {e}")

    return None


# ---------------------------------------------------
# Bolt árak kigyűjtése termékoldalról
# ---------------------------------------------------
def scrape_prices(product_url):
    results = []

    try:
        r = requests.get(product_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        # ajánlatok
        offers = soup.select(".row.offer")

        for offer in offers:
            try:
                shop = offer.select_one(".offer-shop-name")
                price = offer.select_one(".price")

                shop_name = shop.get_text(strip=True) if shop else None
                price_value = price.get_text(strip=True) if price else None

                results.append({
                    "shop": shop_name,
                    "price": price_value
                })

            except Exception:
                continue

    except Exception as e:
        print(f"Hiba termékoldal scrape során: {e}")

    return results


# ---------------------------------------------------
# Streamlit UI
# ---------------------------------------------------
st.set_page_config(page_title="Árukereső SKU scraper", layout="wide")

st.title("Árukereső SKU ár scraper")

uploaded_file = st.file_uploader(
    "Tölts fel egy CSV vagy XLSX fájlt, amiben van egy 'sku' oszlop",
    type=["csv", "xlsx"]
)

if uploaded_file:

    # fájl betöltése
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Betöltött adatok")
    st.dataframe(df.head())

    if "sku" not in df.columns:
        st.error("A fájl nem tartalmaz 'sku' oszlopot!")
        st.stop()

    if st.button("Lekérdezés indítása"):

        final_results = []

        progress = st.progress(0)
        total = len(df)

        for idx, row in df.iterrows():

            sku = row["sku"]

            st.write(f"Feldolgozás: {sku}")

            product_url = search_product_url(sku)

            if product_url:

                prices = scrape_prices(product_url)

                if prices:
                    for p in prices:
                        final_results.append({
                            "sku": sku,
                            "product_url": product_url,
                            "shop": p["shop"],
                            "price": p["price"]
                        })

                else:
                    final_results.append({
                        "sku": sku,
                        "product_url": product_url,
                        "shop": None,
                        "price": None
                    })

            else:
                final_results.append({
                    "sku": sku,
                    "product_url": None,
                    "shop": None,
                    "price": None
                })

            progress.progress((idx + 1) / total)

            # ne spameld az oldalt
            time.sleep(1)

        result_df = pd.DataFrame(final_results)

        st.success("Kész!")

        st.subheader("Eredmények")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="CSV letöltése",
            data=csv,
            file_name="arukereso_prices.csv",
            mime="text/csv"
        )

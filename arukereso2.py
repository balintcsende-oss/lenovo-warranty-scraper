import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# ---------------------------------------------------
# SKU keresés
# ---------------------------------------------------
def search_product_url(sku):

    search_url = f"https://www.arukereso.hu/CategorySearch.php?st={quote(str(sku))}"

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=30)

        soup = BeautifulSoup(r.text, "html.parser")

        links = soup.find_all("a", href=True)

        for a in links:

            href = a["href"]

            # termékoldal szűrés
            if "/p" in href or href.endswith("/"):

                if href.startswith("/"):
                    href = "https://www.arukereso.hu" + href

                return href

    except Exception as e:
        st.error(f"Keresési hiba: {sku} -> {e}")

    return None


# ---------------------------------------------------
# Ár scraping
# ---------------------------------------------------
def scrape_prices(product_url):

    results = []

    try:
        r = requests.get(product_url, headers=HEADERS, timeout=30)

        soup = BeautifulSoup(r.text, "html.parser")

        text = soup.get_text("\n")

        # boltok keresése
        offers = soup.find_all(["div", "tr", "li"])

        for item in offers:

            row_text = item.get_text(" ", strip=True)

            # ár regex
            price_match = re.search(r"([\d\s]+Ft)", row_text)

            if price_match:

                price = price_match.group(1)

                # bolt név próbálása
                shop = None

                links = item.find_all("a")

                for l in links:
                    txt = l.get_text(strip=True)

                    if len(txt) > 2 and "Ft" not in txt:
                        shop = txt
                        break

                results.append({
                    "shop": shop,
                    "price": price
                })

        # duplikáció törlés
        unique = []
        seen = set()

        for r in results:

            key = (r["shop"], r["price"])

            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique

    except Exception as e:
        st.error(f"Scrape hiba: {e}")

    return []


# ---------------------------------------------------
# STREAMLIT
# ---------------------------------------------------
st.set_page_config(page_title="Árukereső scraper", layout="wide")

st.title("Árukereső SKU scraper")

uploaded_file = st.file_uploader(
    "CSV vagy XLSX feltöltés",
    type=["csv", "xlsx"]
)

if uploaded_file:

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.dataframe(df.head())

    if "sku" not in df.columns:
        st.error("Nincs sku oszlop!")
        st.stop()

    if st.button("Indítás"):

        output = []

        progress = st.progress(0)

        total = len(df)

        for idx, row in df.iterrows():

            sku = str(row["sku"])

            st.write(f"SKU: {sku}")

            product_url = search_product_url(sku)

            st.write(f"Talált URL: {product_url}")

            if product_url:

                prices = scrape_prices(product_url)

                if prices:

                    for p in prices:

                        output.append({
                            "sku": sku,
                            "url": product_url,
                            "shop": p["shop"],
                            "price": p["price"]
                        })

                else:

                    output.append({
                        "sku": sku,
                        "url": product_url,
                        "shop": None,
                        "price": None
                    })

            else:

                output.append({
                    "sku": sku,
                    "url": None,
                    "shop": None,
                    "price": None
                })

            progress.progress((idx + 1) / total)

            time.sleep(1)

        result_df = pd.DataFrame(output)

        st.success("Kész")

        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "CSV letöltése",
            csv,
            "arukereso_export.csv",
            "text/csv"
        )

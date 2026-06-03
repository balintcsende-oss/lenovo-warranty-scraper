import io
import time
import random
import pandas as pd
import requests
import streamlit as st

from bs4 import BeautifulSoup
from urllib.parse import quote

# --------------------------------------------------
# SESSION + HEADERS
# --------------------------------------------------

session = requests.Session()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
    "Referer": "https://www.arukereso.hu/"
}

session.headers.update(HEADERS)


# --------------------------------------------------
# SAFE GET (403 + CAPTCHA DETECTION + RETRY)
# --------------------------------------------------

def safe_get(url, retries=3):

    for i in range(retries):

        try:
            r = session.get(url, timeout=30)
            text = r.text.lower()

            # HTTP block
            if r.status_code == 403:
                time.sleep(2 * (i + 1))
                continue

            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue

            if r.status_code != 200:
                return None, f"HTTP hiba ({r.status_code})"

            # Bot / captcha detection
            block_signals = [
                "captcha",
                "verify you are human",
                "robot",
                "access denied",
                "unusual traffic",
                "too many requests"
            ]

            if any(sig in text for sig in block_signals):
                return None, "Bot védelem / CAPTCHA"

            return r.text, None

        except Exception as e:
            return None, f"Hálózati hiba: {str(e)}"

    return None, "Tartós 403 blokk"


# --------------------------------------------------
# SKU -> PRODUCT URL
# --------------------------------------------------

def search_product_url(sku):

    search_url = (
        "https://www.arukereso.hu/CategorySearch.php?st="
        + quote(sku)
    )

    html, err = safe_get(search_url)

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

def get_prices(product_url):

    html, err = safe_get(product_url)

    if err:
        return [], err

    soup = BeautifulSoup(html, "html.parser")

    results = []

    for offer in soup.select("div.optoffer"):

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
        df.to_excel(writer, sheet_name="Arukereso", index=False)

    output.seek(0)
    return output


# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------

st.set_page_config(page_title="Árukereső SKU árlekérő", layout="wide")
st.title("Árukereső SKU árlekérő")

uploaded_file = st.file_uploader(
    "Excel vagy CSV",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file:

    try:

        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

        st.dataframe(df.head())

        if "sku" not in df.columns:
            st.error("Nincs sku oszlop!")
            st.stop()

        if st.button("Lekérdezés indítása"):

            all_rows = []
            progress = st.progress(0)
            total = len(df)

            for idx, row in df.iterrows():

                sku = str(row["sku"]).strip()

                product_url, err = search_product_url(sku)

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

                offers, err = get_prices(product_url)

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

                time.sleep(random.uniform(2.0, 5.0))
                progress.progress((idx + 1) / total)

            result_df = pd.DataFrame(all_rows)

            st.success(f"Kész! {len(result_df)} sor.")
            st.dataframe(result_df)

            excel_file = dataframe_to_excel(result_df)

            st.download_button(
                "Excel letöltése",
                data=excel_file,
                file_name="arukereso_arak.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.exception(e)

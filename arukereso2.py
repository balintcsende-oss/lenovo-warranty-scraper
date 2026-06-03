import io
import time
import pandas as pd
import requests
import streamlit as st

from bs4 import BeautifulSoup

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8"
}


# --------------------------------------------------
# SAFE REQUEST (ANTI-BLOCK DETECTION)
# --------------------------------------------------

def safe_get(url):
    """
    Returns: (status, text, blocked_reason)

    status: HTTP status code or None
    blocked_reason: None if OK, otherwise string
    """

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)

        text_lower = r.text.lower()

        # HTTP alapú védelem
        if r.status_code in [403, 429]:
            return r.status_code, None, f"HTTP blokkolás ({r.status_code})"

        # HTML alapú bot/captcha detektálás
        block_signals = [
            "captcha",
            "robot",
            "access denied",
            "unusual traffic",
            "verify you are human",
            "too many requests"
        ]

        if any(sig in text_lower for sig in block_signals):
            return r.status_code, None, "Bot védelem / CAPTCHA oldal"

        if r.status_code != 200:
            return r.status_code, None, f"HTTP hiba ({r.status_code})"

        return r.status_code, r.text, None

    except Exception as e:
        return None, None, f"Hálózati hiba: {str(e)}"


# --------------------------------------------------
# SKU -> PRODUCT URL
# --------------------------------------------------

def search_product_url(sku):

    search_url = f"https://www.arukereso.hu/CategorySearch.php?st={sku}"

    status, html, blocked = safe_get(search_url)

    if blocked or not html:
        return None, blocked

    soup = BeautifulSoup(html, "html.parser")

    sku_lower = str(sku).lower()

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

    results = []

    status, html, blocked = safe_get(product_url)

    if blocked or not html:
        return results, blocked

    soup = BeautifulSoup(html, "html.parser")

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
        df.to_excel(writer, sheet_name="Arukereso", index=False)

    output.seek(0)
    return output


# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------

st.set_page_config(
    page_title="Árukereső SKU árlekérő",
    layout="wide"
)

st.title("Árukereső SKU árlekérő")

st.write("Tölts fel egy Excel vagy CSV fájlt. Kötelező oszlop: sku")

uploaded_file = st.file_uploader(
    "Excel vagy CSV",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file:

    try:

        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("Beolvasott adatok")
        st.dataframe(df.head())

        if "sku" not in df.columns:
            st.error("Nem található sku oszlop!")
            st.stop()

        if st.button("Lekérdezés indítása"):

            all_rows = []
            progress = st.progress(0)
            total = len(df)

            for idx, row in df.iterrows():

                sku = str(row["sku"]).strip()

                product_url, block_reason = search_product_url(sku)

                if block_reason:
                    st.warning(f"⚠️ Védelem detektálva SKU: {sku} -> {block_reason}")

                if not product_url:
                    all_rows.append({
                        "sku": sku,
                        "product_url": None,
                        "shop": None,
                        "price": None,
                        "blocked": block_reason
                    })

                    progress.progress((idx + 1) / total)
                    continue

                offers, block_reason = get_prices(product_url)

                if block_reason:
                    st.warning(f"⚠️ Védelem a termékoldalon: {sku} -> {block_reason}")

                if not offers:
                    all_rows.append({
                        "sku": sku,
                        "product_url": product_url,
                        "shop": None,
                        "price": None,
                        "blocked": block_reason
                    })
                else:
                    for offer in offers:
                        all_rows.append({
                            "sku": sku,
                            "product_url": product_url,
                            "shop": offer["shop"],
                            "price": offer["price"],
                            "blocked": None
                        })

                time.sleep(1)
                progress.progress((idx + 1) / total)

            result_df = pd.DataFrame(all_rows)

            st.success(f"Kész! {len(result_df)} sor.")

            st.dataframe(result_df)

            excel_file = dataframe_to_excel(result_df)

            st.download_button(
                label="Excel letöltése",
                data=excel_file,
                file_name="arukereso_arak.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.exception(e)

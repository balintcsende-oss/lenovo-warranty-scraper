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
# SKU -> PRODUCT URL
# --------------------------------------------------

def search_product_url(sku):

    try:
        search_url = f"https://www.arukereso.hu/CategorySearch.php?st={sku}"

        r = requests.get(
            search_url,
            headers=HEADERS,
            timeout=30
        )

        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        sku_lower = str(sku).lower()

        for a in soup.find_all("a", href=True):

            href = a["href"]
            title = a.get("title", "")

            if (
                sku_lower in title.lower()
                and "arukereso.hu" in href
                and "-p" in href
            ):
                return href

        return None

    except Exception:
        return None


# --------------------------------------------------
# PRODUCT PAGE -> OFFERS
# --------------------------------------------------

def get_prices(product_url):

    results = []

    try:

        r = requests.get(
            product_url,
            headers=HEADERS,
            timeout=30
        )

        if r.status_code != 200:
            return results

        soup = BeautifulSoup(r.text, "html.parser")

        offers = soup.select("div.optoffer")

        for offer in offers:

            try:

                shop_el = offer.select_one(
                    '[itemprop="seller"] [itemprop="name"]'
                )

                price_el = offer.select_one(
                    '[itemprop="price"]'
                )

                if not shop_el:
                    continue

                if not price_el:
                    continue

                shop = shop_el.get_text(strip=True)

                price = price_el.get(
                    "content",
                    ""
                )

                results.append(
                    {
                        "shop": shop,
                        "price": price
                    }
                )

            except Exception:
                pass

        return results

    except Exception:
        return results


# --------------------------------------------------
# EXCEL EXPORT
# --------------------------------------------------

def dataframe_to_excel(df):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Arukereso",
            index=False
        )

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

st.write(
    """
Tölts fel egy Excel vagy CSV fájlt.

Kötelező oszlop:

- sku
"""
)

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

            st.error(
                "Nem található sku oszlop!"
            )

            st.stop()

        if st.button("Lekérdezés indítása"):

            all_rows = []

            progress = st.progress(0)

            total = len(df)

            for idx, row in df.iterrows():

                sku = str(row["sku"]).strip()

                product_url = search_product_url(sku)

                if not product_url:

                    all_rows.append(
                        {
                            "sku": sku,
                            "product_url": None,
                            "shop": None,
                            "price": None
                        }
                    )

                    progress.progress(
                        (idx + 1) / total
                    )

                    continue

                offers = get_prices(product_url)

                if not offers:

                    all_rows.append(
                        {
                            "sku": sku,
                            "product_url": product_url,
                            "shop": None,
                            "price": None
                        }
                    )

                else:

                    for offer in offers:

                        all_rows.append(
                            {
                                "sku": sku,
                                "product_url": product_url,
                                "shop": offer["shop"],
                                "price": offer["price"]
                            }
                        )

                time.sleep(1)

                progress.progress(
                    (idx + 1) / total
                )

            result_df = pd.DataFrame(all_rows)

            st.success(
                f"Kész! {len(result_df)} sor."
            )

            st.dataframe(result_df)

            excel_file = dataframe_to_excel(
                result_df
            )

            st.download_button(
                label="Excel letöltése",
                data=excel_file,
                file_name="arukereso_arak.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                )
            )

    except Exception as e:

        st.exception(e)

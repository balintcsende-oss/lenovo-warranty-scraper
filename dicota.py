import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tempfile

st.set_page_config(page_title="Dicota Scraper", layout="wide")

st.title("Dicota SKU → Product Title + Handle")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # SKU oszlop keresése
    sku_col = None
    for col in df.columns:
        if "sku" in col.lower():
            sku_col = col
            break

    if sku_col is None:
        st.error("Nem található SKU oszlop")
        st.stop()

    st.success(f"SKU oszlop: {sku_col}")

    if st.button("Scrape indítása"):

        titles = []
        handles = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9"
        }

        progress = st.progress(0)
        log = st.empty()

        for i, sku in enumerate(df[sku_col]):

            if pd.isna(sku):
                titles.append("")
                handles.append("")
                continue

            sku = str(sku).strip()

            url = f"https://www.dicota.com/search/suggest?q={sku}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"

            try:

                r = requests.get(url, headers=headers)

                if r.status_code != 200:
                    titles.append("")
                    handles.append("")
                    log.text(f"{sku} → HTTP {r.status_code}")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                # TITLE
                title = ""
                span = soup.find("span", {"li-object": "product.title"})
                if span:
                    title = span.text.strip()

                # HANDLE
                handle = ""
                link = soup.find("a", class_="predictive-search_line-item")

                if link and "href" in link.attrs:
                    href = link["href"]
                    if "/products/" in href:
                        handle = href.split("/products/")[1].split("?")[0]

                titles.append(title)
                handles.append(handle)

                log.text(f"{sku} → {title} | {handle}")

            except Exception as e:

                titles.append("")
                handles.append("")
                log.text(f"{sku} → ERROR {e}")

            progress.progress((i + 1) / len(df))

        df["product_title"] = titles
        df["handle"] = handles

        st.success("Scraping kész!")

        st.subheader("Eredmények")
        st.dataframe(df)

        # Excel export
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(tmp.name, index=False)

        with open(tmp.name, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name="dicota_results.xlsx"
            )

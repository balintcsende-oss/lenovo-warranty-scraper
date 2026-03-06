import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tempfile

st.set_page_config(page_title="Dicota Product Title Scraper")
st.title("Dicota Product Title Scraper")

# 1️⃣ Excel feltöltés
uploaded_file = st.file_uploader("Excel feltöltése (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # 2️⃣ SKU oszlop keresése
    sku_col = None
    for col in df.columns:
        if "sku" in col.lower():
            sku_col = col
            break

    if sku_col is None:
        st.error("Nem található SKU oszlop az Excelben")
    else:
        st.success(f"SKU oszlop: {sku_col}")

        if st.button("Scrape indítása"):

            titles = []

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/118.0.5993.90 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, sku in enumerate(df[sku_col]):
                if pd.isna(sku):
                    titles.append("")
                    continue

                sku = str(sku).strip()
                url = f"https://www.dicota.com/search/suggest?q={sku}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"

                try:
                    resp = requests.get(url, headers=headers)
                    if resp.status_code != 200:
                        titles.append("")
                        progress_text.text(f"Hiba: {sku} → HTTP {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = ""
                    span = soup.find("span", {"li-object": "product.title"})
                    if span:
                        title = span.text.strip()

                    titles.append(title)
                    progress_text.text(f"{sku} → {title}")

                except Exception as e:
                    titles.append("")
                    progress_text.text(f"Hiba: {sku} → {e}")

                progress_bar.progress((i + 1) / len(df))

            df["product_title"] = titles

            # ideiglenes fájl mentés és letöltés
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            df.to_excel(tmp_file.name, index=False)
            tmp_file.close()

            st.success("Kész! A product_title oszlop kitöltve.")
            st.download_button(
                "Letöltés Excel",
                tmp_file.name,
                file_name="dicota_output.xlsx"
            )

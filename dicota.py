import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import tempfile

st.title("Dicota Product Title Scraper (Playwright)")

# Excel feltöltés
uploaded_file = st.file_uploader("Excel feltöltése (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # SKU oszlop keresése
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

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                progress_text = st.empty()
                progress_bar = st.progress(0)

                for i, sku in enumerate(df[sku_col]):
                    if pd.isna(sku):
                        titles.append("")
                        continue

                    sku = str(sku).strip()
                    url = f"https://www.dicota.com/search?type=product&q={sku}"
                    page.goto(url)

                    try:
                        # várunk, amíg a product.title megjelenik (max 5 sec)
                        page.wait_for_selector('[li-object="product.title"]', timeout=5000)
                        title_elem = page.query_selector('[li-object="product.title"]')
                        title = title_elem.inner_text().strip() if title_elem else ""
                    except:
                        title = ""

                    titles.append(title)

                    progress_text.text(f"Keresés: {sku} → {title}")
                    progress_bar.progress((i + 1) / len(df))

                browser.close()

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

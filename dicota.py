import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tempfile
import re

st.set_page_config(page_title="Dicota Scraper", layout="wide")
st.title("Dicota SKU → Full Product Data by Handle")

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

        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9"
        }

        progress = st.progress(0)
        log = st.empty()

        # Segédfüggvény: handle alapján scrape
        def scrape_product_by_handle(handle):
            url = f"https://www.dicota.com/products/{handle}"
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
            data = {}

            # TITLE
            title_tag = soup.find("h1")
            data["title"] = title_tag.text.strip() if title_tag else ""

            # DESCRIPTION
            desc_tag = soup.find("div", class_=re.compile("rich-text"))
            data["description"] = desc_tag.text.strip() if desc_tag else ""

            # BULLETS / FEATURES
            bullets = soup.find_all("li")
            features = [b.text.strip() for b in bullets if len(b.text.strip())>5]
            data["features"] = " | ".join(features[:10])

            # IMAGES (max 5)
            images = []
            for img in soup.find_all("img"):
                src = img.get("src")
                if src and "cdn.shopify.com" in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    images.append(src)
            images = list(dict.fromkeys(images))  # unique
            for i in range(5):
                data[f"image_{i+1}"] = images[i] if i < len(images) else ""

            # PRICE
            price_tag = soup.find(string=re.compile("Ft"))
            data["price"] = price_tag if price_tag else ""

            # PRODUCT TYPE / VENDOR
            type_tag = soup.find("div", {"li-object": "product.type"})
            data["product_type"] = type_tag.text.strip() if type_tag else ""

            vendor_tag = soup.find("div", {"li-object": "product.vendor"})
            data["vendor"] = vendor_tag.text.strip() if vendor_tag else ""

            return data

        # Iterálunk a SKU-kon
        for i, sku in enumerate(df[sku_col]):
            if pd.isna(sku):
                results.append({})
                continue
            sku = str(sku).strip()

            # 1️⃣ Handle kinyerése a predictive search-ből
            search_url = f"https://www.dicota.com/search/suggest?q={sku}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"
            try:
                r = requests.get(search_url, headers=headers)
                if r.status_code != 200:
                    log.text(f"{sku} → HTTP {r.status_code}")
                    results.append({})
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                # HANDLE
                handle = ""
                link = soup.find("a", class_="predictive-search_line-item")
                if link and "href" in link.attrs:
                    href = link["href"]
                    if "/products/" in href:
                        handle = href.split("/products/")[1].split("?")[0]

                if not handle:
                    log.text(f"{sku} → nincs handle")
                    results.append({})
                    continue

                # 2️⃣ Handle alapján a teljes product scrape
                product_data = scrape_product_by_handle(handle)
                if not product_data:
                    log.text(f"{sku} → handle scrape hiba")
                    results.append({})
                    continue

                # Adatok összegyűjtése
                product_data_ordered = {
                    "sku": sku,
                    "handle": handle,
                    "handle_link": f"https://www.dicota.com/products/{handle}",
                    **product_data
                }

                results.append(product_data_ordered)
                log.text(f"{sku} → {product_data['title']} | {handle}")

            except Exception as e:
                log.text(f"{sku} → ERROR {e}")
                results.append({})

            progress.progress((i+1)/len(df))

        # DataFrame készítése
        result_df = pd.DataFrame(results)

        # Sorrend biztosítása
        cols = ["sku", "handle", "handle_link"] + [c for c in result_df.columns if c not in ["sku", "handle", "handle_link"]]
        result_df = result_df[cols]

        st.subheader("Eredmények")
        st.dataframe(result_df)

        # Excel export
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        result_df.to_excel(tmp.name, index=False)
        with open(tmp.name, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name="dicota_full_results.xlsx"
            )

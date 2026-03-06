import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tempfile
import re

st.set_page_config(page_title="Dicota Full Product Scraper", layout="wide")
st.title("Dicota – Full Product Data by Handle")

uploaded_file = st.file_uploader("Excel feltöltése (SKU + handle)", type=["xlsx"])

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

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

    # IMAGES
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

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Ellenőrizzük, hogy van handle oszlop
    handle_col = None
    for col in df.columns:
        if "handle" in col.lower():
            handle_col = col
            break
    if handle_col is None:
        st.error("Nincs handle oszlop az Excelben!")
        st.stop()

    if st.button("Scrape indítása"):
        results = []
        progress = st.progress(0)
        log = st.empty()
        total = len(df)

        for i, row in df.iterrows():
            handle = str(row[handle_col]).strip()
            sku = row.get("SKU", "")
            try:
                product_data = scrape_product_by_handle(handle)
                if product_data is None:
                    log.text(f"{sku} → {handle} → HTTP hiba")
                    continue
                product_data["sku"] = sku
                product_data["handle"] = handle
                results.append(product_data)
                log.text(f"{sku} → {handle} → OK")
            except Exception as e:
                log.text(f"{sku} → {handle} → ERROR {e}")
            progress.progress((i+1)/total)

        result_df = pd.DataFrame(results)
        st.subheader("Eredmény")
        st.dataframe(result_df)

        # Excel export
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        result_df.to_excel(tmp.name, index=False)
        with open(tmp.name, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name="dicota_products.xlsx"
            )

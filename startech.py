import streamlit as st
import pandas as pd
import io
import re
import demjson3
from curl_cffi import requests

st.title("StarTech SKU Scraper")

uploaded = st.file_uploader(
    "Excel feltöltése (kell egy 'sku' oszlop)",
    type=["xlsx"]
)

def scrape_sku(sku):

    url = f"https://www.startech.com/en-us/universal-laptop-docking-stations/{sku.lower()}"

    try:
        html = requests.get(url, impersonate="chrome", timeout=30).text
    except:
        return {"sku": sku, "error": "request error"}

    matches = re.findall(r"modParam\s*=\s*(\{.*?\});", html, re.S)

    product = None

    for m in matches:

        try:
            data = demjson3.decode(m)
        except:
            continue

        if "product" in data:
            product = data["product"]
            break

        if "productDetail" in data and "product" in data["productDetail"]:
            product = data["productDetail"]["product"]
            break

    if not product:
        return {"sku": sku, "error": "no product data"}

    row = {}

    row["sku"] = product.get("productID")
    row["title"] = product.get("title")
    row["upc"] = product.get("upc")

    # specs
    for spec in product.get("technical", {}).get("techSpecs", []):
        row[spec.get("attributeText")] = spec.get("attributeValue")

    # images
    for i, img in enumerate(product.get("galleryImages", [])):
        row[f"image_{i+1}"] = img.get("largeUrl")

    return row


if uploaded:

    df_input = pd.read_excel(uploaded)

    # oszlopnevek normalizálása
df_input.columns = df_input.columns.str.strip().str.lower()

if "sku" not in df_input.columns:
    st.error(f"Nincs sku oszlop. Talált oszlopok: {list(df_input.columns)}")
    st.stop()

    skus = df_input["sku"].dropna().astype(str).tolist()

    if st.button("SCRAPE"):

        results = []

        progress = st.progress(0)

        for i, sku in enumerate(skus):

            results.append(scrape_sku(sku))

            progress.progress((i + 1) / len(skus))

        df = pd.DataFrame(results)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.success("Kész")

        st.download_button(
            "Excel letöltés",
            buffer.getvalue(),
            file_name="startech_products.xlsx"
        )

        st.dataframe(df)

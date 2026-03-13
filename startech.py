import streamlit as st
import pandas as pd
import io
import re
import demjson3
from curl_cffi import requests

st.title("⭐ StarTech SKU Scraper PRO")

uploaded = st.file_uploader(
    "Excel feltöltése",
    type=["xlsx", "xls"]
)

def find_sku_column(df):

    cols = df.columns.str.strip().str.lower()

    for i, c in enumerate(cols):
        if c in ["sku", "part number", "part_number", "product code", "product_code"]:
            return df.columns[i]

    return None


def scrape_sku(sku):

    url = f"https://www.startech.com/en-us/universal-laptop-docking-stations/{sku.lower()}"

    try:
        html = requests.get(
            url,
            impersonate="chrome",
            timeout=30
        ).text
    except:
        return {"input_sku": sku, "error": "request error"}

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
        return {"input_sku": sku, "error": "no product data"}

    row = {}

    row["input_sku"] = sku
    row["sku"] = product.get("productID")
    row["title"] = product.get("title")
    row["upc"] = product.get("upc")

    for spec in product.get("technical", {}).get("techSpecs", []):
        row[spec.get("attributeText")] = spec.get("attributeValue")

    for i, img in enumerate(product.get("galleryImages", [])):
        row[f"image_{i+1}"] = img.get("largeUrl")

    return row


if uploaded:

    xls = pd.ExcelFile(uploaded)

    sheet = st.selectbox(
        "Sheet kiválasztása",
        xls.sheet_names
    )

    df_input = pd.read_excel(uploaded, sheet_name=sheet)

    st.write("Talált oszlopok:", df_input.columns.tolist())

    sku_col = find_sku_column(df_input)

    if not sku_col:
        st.error("Nem található SKU oszlop")
        st.stop()

    st.success(f"SKU oszlop: {sku_col}")

    skus = df_input[sku_col].dropna().astype(str).tolist()

    if st.button("🚀 SCRAPE"):

        results = []

        progress = st.progress(0)

        for i, sku in enumerate(skus):

            results.append(scrape_sku(sku))

            progress.progress((i + 1) / len(skus))

        df = pd.DataFrame(results)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.success("✅ Kész")

        st.download_button(
            "📥 Excel letöltés",
            buffer.getvalue(),
            file_name="startech_products.xlsx"
        )

        st.dataframe(df)

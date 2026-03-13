import streamlit as st
from curl_cffi import requests
import re
import demjson3
import pandas as pd
import io

st.title("StarTech SKU scraper")

sku_input = st.text_area(
    "SKU lista (egy sor = egy SKU)",
    height=200
)

def scrape_sku(sku):

    url = f"https://www.startech.com/en-us/universal-laptop-docking-stations/{sku.lower()}"

    html = requests.get(url, impersonate="chrome").text

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
        return {"sku": sku, "error": "no product"}

    row = {}

    row["sku"] = product.get("productID")
    row["title"] = product.get("title")
    row["upc"] = product.get("upc")

    for spec in product.get("technical", {}).get("techSpecs", []):
        row[spec.get("attributeText")] = spec.get("attributeValue")

    for i, img in enumerate(product.get("galleryImages", [])):
        row[f"image_{i+1}"] = img.get("largeUrl")

    return row


if st.button("SCRAPE"):

    skus = [s.strip() for s in sku_input.split("\n") if s.strip()]

    results = []

    progress = st.progress(0)

    for i, sku in enumerate(skus):

        results.append(scrape_sku(sku))

        progress.progress((i+1)/len(skus))

    df = pd.DataFrame(results)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)

    st.success("Kész")

    st.download_button(
        label="Excel letöltés",
        data=buffer.getvalue(),
        file_name="startech_products.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.dataframe(df)

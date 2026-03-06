import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import tempfile

st.set_page_config(page_title="Dicota Product Scraper", layout="wide")

st.title("Dicota SKU → Full Product Data")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}


def get_handle_and_title(sku):

    url = f"https://www.dicota.com/search/suggest?q={sku}&section_id=predictive_search"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return "", ""

    soup = BeautifulSoup(r.text, "html.parser")

    title = ""
    handle = ""

    span = soup.find("span", {"li-object": "product.title"})
    if span:
        title = span.text.strip()

    link = soup.find("a", class_="predictive-search_line-item")

    if link and "href" in link.attrs:
        href = link["href"]
        if "/products/" in href:
            handle = href.split("/products/")[1].split("?")[0]

    return title, handle


def scrape_product(handle):

    url = f"https://www.dicota.com/products/{handle}"

    r = requests.get(url, headers=headers)

    soup = BeautifulSoup(r.text, "html.parser")

    data = {}

    # TITLE
    title = soup.find("h1")
    data["title"] = title.text.strip() if title else ""

    # DESCRIPTION
    desc = soup.find("div", class_=re.compile("rich-text"))
    data["description"] = desc.text.strip() if desc else ""

    # BULLETS
    bullets = soup.find_all("li")
    features = [b.text.strip() for b in bullets if len(b.text.strip()) > 20]

    data["features"] = " | ".join(features[:6])

    # IMAGES
    images = []
    imgs = soup.find_all("img")

    for img in imgs:
        src = img.get("src")

        if src and "cdn.shopify.com" in src:
            if src.startswith("//"):
                src = "https:" + src
            images.append(src)

    images = list(dict.fromkeys(images))

    for i in range(5):
        data[f"image_{i+1}"] = images[i] if i < len(images) else ""

    # PRICE
    price = soup.find(string=re.compile("Ft"))
    data["price"] = price if price else ""

    return data


if uploaded_file:

    df = pd.read_excel(uploaded_file)

    sku_col = None

    for col in df.columns:
        if "sku" in col.lower():
            sku_col = col
            break

    if sku_col is None:
        st.error("Nincs SKU oszlop")
        st.stop()

    if st.button("Scrape indítása"):

        results = []

        progress = st.progress(0)
        log = st.empty()

        total = len(df)

        for i, sku in enumerate(df[sku_col]):

            sku = str(sku).strip()

            try:

                title, handle = get_handle_and_title(sku)

                if handle == "":
                    log.text(f"{sku} → nincs találat")
                    continue

                product_data = scrape_product(handle)

                product_data["sku"] = sku
                product_data["handle"] = handle

                results.append(product_data)

                log.text(f"{sku} → OK")

            except Exception as e:

                log.text(f"{sku} → ERROR {e}")

            progress.progress((i + 1) / total)

        result_df = pd.DataFrame(results)

        st.subheader("Eredmény")

        st.dataframe(result_df)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

        result_df.to_excel(tmp.name, index=False)

        with open(tmp.name, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name="dicota_products.xlsx"
            )

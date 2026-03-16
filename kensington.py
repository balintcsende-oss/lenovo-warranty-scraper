import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

ALGOLIA_URL = "https://y5z6c9v1x9-dsn.algolia.net/1/indexes/*/queries"

HEADERS = {
    "x-algolia-application-id": "Y5Z6C9V1X9",
    "x-algolia-api-key": "0cfdc9c5f9f0cfa_fake_public_search_key",
    "Content-Type": "application/json"
}


def get_product_url(sku):

    payload = {
        "requests": [
            {
                "indexName": "prod_products_en_us",
                "params": f"query={sku}&hitsPerPage=5"
            }
        ]
    }

    try:
        r = requests.post(ALGOLIA_URL, json=payload, headers=HEADERS, timeout=30)
        data = r.json()

        hits = data["results"][0]["hits"]

        if hits:
            return "https://www.kensington.com" + hits[0]["url"]

    except:
        return None

    return None


def parse_product(url):

    images = []
    features = []
    specs = {}

    try:
        r = requests.get(url, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        for img in soup.select("[data-zoom-image]"):
            src = img.get("data-zoom-image")
            if src:
                images.append(src)

        for li in soup.select("li"):
            t = li.get_text(strip=True)
            if len(t) > 30:
                features.append(t)

        for row in soup.select("table tr"):
            cols = row.find_all(["td","th"])
            if len(cols) == 2:
                specs[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

    except:
        pass

    return images, features, specs


st.title("Kensington scraper")

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    results = []

    prog = st.progress(0)

    for i, sku in enumerate(df["SKU"].dropna()):

        st.write("Processing:", sku)

        url = get_product_url(str(sku))

        if not url:
            results.append({"SKU": sku})
            continue

        images, features, specs = parse_product(url)

        row = {
            "SKU": sku,
            "URL": url,
            "FEATURES": " | ".join(features),
            "SPECS": str(specs)
        }

        for n, img in enumerate(images):
            row[f"IMAGE_{n+1}"] = img

        results.append(row)

        prog.progress((i+1)/len(df))

        time.sleep(0.3)

    out = pd.DataFrame(results)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész")

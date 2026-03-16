import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.kensington.com"
SEARCH = "https://www.kensington.com/GlobalSearch/QuickSearch/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}


def get_product_url(sku):
    try:
        r = requests.get(
            SEARCH,
            params={"query": sku},
            headers=headers,
            timeout=30
        )

        data = r.json()

        if data and "Results" in data and len(data["Results"]) > 0:
            rel = data["Results"][0]["Url"]
            return urljoin(BASE, rel)

    except:
        return None

    return None


def parse_product(url):
    try:
        r = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        # ---------- IMAGES ----------
        images = []
        gallery = soup.select("img")

        for img in gallery:
            src = img.get("src") or img.get("data-src")

            if src and "kensington.com" in src:
                src = src.replace("width=80", "width=1000")
                src = src.replace("width=200", "width=1200")

                if src not in images:
                    images.append(src)

        # ---------- FEATURES ----------
        features = []
        feats = soup.select("ul li")

        for f in feats:
            txt = f.get_text(strip=True)
            if len(txt) > 30:
                features.append(txt)

        # ---------- SPECS ----------
        specs = {}
        rows = soup.select("table tr")

        for r in rows:
            cols = r.find_all("td")
            if len(cols) == 2:
                k = cols[0].get_text(strip=True)
                v = cols[1].get_text(strip=True)
                specs[k] = v

        return images, features, specs

    except:
        return [], [], {}


st.title("Kensington SKU scraper")

file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop")
        st.stop()

    result = []

    for sku in df["SKU"].dropna():

        st.write("Processing:", sku)

        url = get_product_url(str(sku))

        if not url:
            result.append({
                "SKU": sku,
                "URL": None
            })
            continue

        images, features, specs = parse_product(url)

        row = {
            "SKU": sku,
            "URL": url,
            "FEATURES": " | ".join(features),
            "SPECS": str(specs)
        }

        for i, img in enumerate(images):
            row[f"IMAGE_{i+1}"] = img

        result.append(row)

    out = pd.DataFrame(result)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész")

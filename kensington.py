import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

BASE = "https://www.kensington.com"
SEARCH = "https://www.kensington.com/GlobalSearch/QuickSearch/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.kensington.com/",
    "X-Requested-With": "XMLHttpRequest"
}


def get_product_url(session, sku):
    # FONTOS: először home page → cookie
    session.get(BASE, headers=HEADERS)

    r = session.get(
        SEARCH,
        params={"query": sku},
        headers=HEADERS,
        timeout=30
    )

    try:
        data = r.json()
        if "Results" in data and len(data["Results"]) > 0:
            return BASE + data["Results"][0]["Url"]
    except:
        return None

    return None


def parse_product(url):
    images = []
    features = []
    specs = {}
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        # FULL HD képek
        for img in soup.select("[data-zoom-image]"):
            src = img.get("data-zoom-image")
            if src and src not in images:
                images.append(src)

        # fallback
        if not images:
            for img in soup.select("img"):
                src = img.get("src")
                if src and "kensington" in src:
                    if src not in images:
                        images.append(src)

        # FEATURES
        for li in soup.select("li"):
            txt = li.get_text(strip=True)
            if len(txt) > 30:
                features.append(txt)

        # SPECS
        for row in soup.select("table tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                specs[key] = val

    except:
        pass

    return images, features, specs


# ---------- STREAMLIT UI ----------
st.title("Kensington QuickSearch Scraper")

file = st.file_uploader("Excel feltöltése (SKU oszlop)", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop")
        st.stop()

    session = requests.Session()
    results = []
    skus = df["SKU"].dropna().tolist()
    progress = st.progress(0)

    for i, sku in enumerate(skus):
        st.write("Processing:", sku)
        url = get_product_url(session, str(sku))

        if not url:
            results.append({"SKU": sku, "URL": None})
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
        progress.progress((i + 1) / len(skus))
        time.sleep(0.3)

    out = pd.DataFrame(results)
    st.dataframe(out)
    out.to_excel("kensington_output.xlsx", index=False)
    st.success("Kész ✔")

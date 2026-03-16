import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ---------- URL KERESÉS BINGGEL ----------
def get_product_url(sku):

    try:
        query = quote(f"site:kensington.com {sku}")

        url = f"https://www.bing.com/search?q={query}"

        r = requests.get(url, headers=HEADERS, timeout=30)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("li.b_algo h2 a"):
            link = a.get("href")

            if "/p/" in link:
                return link

    except:
        return None

    return None


# ---------- PRODUCT OLDAL PARSE ----------
def parse_product(url):

    images = []
    features = []
    specs = {}

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)

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
                if src and "kensington" in src and src not in images:
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
                k = cols[0].get_text(strip=True)
                v = cols[1].get_text(strip=True)
                specs[k] = v

    except:
        pass

    return images, features, specs


# ---------- STREAMLIT ----------
st.title("Kensington scraper")

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("SKU oszlop nincs")
        st.stop()

    result = []

    prog = st.progress(0)

    total = len(df)

    for i, sku in enumerate(df["SKU"].dropna()):

        st.write("Processing:", sku)

        url = get_product_url(str(sku))

        if not url:
            result.append({"SKU": sku})
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

        result.append(row)

        prog.progress((i+1)/total)

        time.sleep(1)

    out = pd.DataFrame(result)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész")

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ---------- GOOGLE SITE SEARCH ----------
def get_product_url(sku):

    try:
        q = quote(f"{sku} site:kensington.com")

        url = f"https://www.google.com/search?q={q}"

        r = requests.get(url, headers=HEADERS, timeout=30)

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a"):
            href = a.get("href")

            if href and "kensington.com" in href and "/p/" in href:
                href = href.split("/url?q=")[1].split("&")[0]
                return href

    except:
        return None

    return None


# ---------- PRODUCT PARSER ----------
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
                if src and "kensington" in src:
                    images.append(src)

        # FEATURES
        for li in soup.select("li"):
            t = li.get_text(strip=True)
            if len(t) > 30:
                features.append(t)

        # SPECS
        for row in soup.select("table tr"):
            cols = row.find_all(["td","th"])
            if len(cols) == 2:
                specs[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

    except:
        pass

    return images, features, specs


# ---------- STREAMLIT ----------
st.title("Kensington SKU scraper")

file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop")
        st.stop()

    results = []

    prog = st.progress(0)

    skus = df["SKU"].dropna().tolist()

    for i, sku in enumerate(skus):

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

        prog.progress((i+1)/len(skus))

        time.sleep(1)

    out = pd.DataFrame(results)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész ✔")

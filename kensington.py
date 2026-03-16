import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

BASE = "https://www.kensington.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ---------- URL KERESÉS ----------
def get_product_url(sku):

    try:
        search_url = f"https://www.kensington.com/search/?text={sku}"

        r = requests.get(search_url, headers=HEADERS, timeout=30)

        soup = BeautifulSoup(r.text, "html.parser")

        links = soup.select("a")

        for a in links:
            href = a.get("href")

            if href and "/p/" in href:
                return urljoin(BASE, href)

    except:
        return None

    return None


# ---------- PRODUCT SCRAPE ----------
def parse_product(url):

    images = []
    features = []
    specs = {}

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        # ---- FULL HD IMAGES ----
        zoom_imgs = soup.select("[data-zoom-image]")

        for img in zoom_imgs:
            link = img.get("data-zoom-image")

            if link and link not in images:
                images.append(link)

        # fallback
        if not images:
            normal_imgs = soup.select("img")

            for img in normal_imgs:
                src = img.get("src")

                if src and "kensington" in src and src not in images:
                    images.append(src)

        # ---- FEATURES ----
        ul_lists = soup.select("ul")

        for ul in ul_lists:
            for li in ul.select("li"):
                txt = li.get_text(strip=True)

                if len(txt) > 25:
                    features.append(txt)

        # ---- SPECS ----
        rows = soup.select("table tr")

        for row in rows:
            cols = row.find_all(["td", "th"])

            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                specs[key] = val

    except:
        pass

    return images, features, specs


# ---------- STREAMLIT UI ----------
st.title("Kensington SKU scraper")

file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop")
        st.stop()

    result = []

    progress = st.progress(0)

    total = len(df)

    for i, sku in enumerate(df["SKU"].dropna()):

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

        for idx, img in enumerate(images):
            row[f"IMAGE_{idx+1}"] = img

        result.append(row)

        progress.progress((i+1)/total)

        time.sleep(1)

    out = pd.DataFrame(result)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész ✔")

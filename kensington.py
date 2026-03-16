import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import concurrent.futures

st.title("Kensington Google scraper")

HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ---------------- GOOGLE SEARCH ----------------

def google_search(sku):

    query = f'site:kensington.com "{sku}"'

    r = requests.get(
        "https://www.google.com/search",
        params={"q": query, "num": 5},
        headers=HEADERS,
        timeout=20
    )

    soup = BeautifulSoup(r.text, "lxml")

    for a in soup.select("a"):

        href = a.get("href")

        if not href:
            continue

        if "/url?q=" in href and "kensington.com" in href:

            link = href.split("/url?q=")[1].split("&")[0]

            if "/p/" in link:
                return link

    return None


# ---------------- PRODUCT SCRAPE ----------------

def scrape_product(url):

    r = requests.get(url, headers=HEADERS, timeout=30)

    soup = BeautifulSoup(r.text, "lxml")

    # images
    images = []

    for img in soup.select("img"):

        src = img.get("src") or img.get("data-src")

        if not src:
            continue

        if "kensington" not in src:
            continue

        if src.startswith("//"):
            src = "https:" + src

        if "zoom" in src or "xl" in src or "large" in src:
            images.append(src)

    images = list(set(images))

    # features
    features = []

    for li in soup.select("ul li"):

        t = li.get_text(strip=True)

        if len(t) > 40:
            features.append(t)

    # specs
    specs = {}

    for row in soup.select("table tr"):

        cols = row.find_all(["td", "th"])

        if len(cols) == 2:
            specs[
                cols[0].get_text(strip=True)
            ] = cols[1].get_text(strip=True)

    return images, features, specs


# ---------------- PROCESS SKU ----------------

def process_sku(sku):

    url = google_search(sku)

    if not url:
        return {
            "SKU": sku,
            "URL": None,
            "IMAGES": None,
            "FEATURES": None,
            "SPECS": None
        }

    images, features, specs = scrape_product(url)

    time.sleep(2)

    return {
        "SKU": sku,
        "URL": url,
        "IMAGES": "\n".join(images),
        "FEATURES": "\n".join(features),
        "SPECS": str(specs)
    }


# ---------------- UI ----------------

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    skus = df["SKU"].dropna().astype(str).tolist()

    results = []

    progress = st.progress(0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exe:

        futures = [exe.submit(process_sku, s) for s in skus]

        for i, f in enumerate(concurrent.futures.as_completed(futures)):

            results.append(f.result())

            progress.progress((i + 1) / len(skus))

    out = pd.DataFrame(results)

    st.dataframe(out)

    st.download_button(
        "Download",
        out.to_csv(index=False),
        "kensington.csv"
    )

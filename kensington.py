import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time

st.title("Kensington PRO scraper")

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------------- SEARCH ENGINE 1 ----------------

def search_bing(sku):

    q = f'site:kensington.com "{sku}"'

    r = requests.get(
        "https://www.bing.com/search",
        params={"q": q},
        headers=HEADERS,
        timeout=20
    )

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("li.b_algo h2 a"):
        link = a.get("href")
        if "/p/" in link:
            return link

    return None


# ---------------- SEARCH ENGINE 2 ----------------

def search_ddg(sku):

    q = f'site:kensington.com "{sku}"'

    r = requests.get(
        "https://duckduckgo.com/html/",
        params={"q": q},
        headers=HEADERS,
        timeout=20
    )

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("a.result__a"):
        link = a.get("href")
        if "/p/" in link:
            return link

    return None


# ---------------- PRODUCT SCRAPER ----------------

def scrape_product(url):

    r = requests.get(url, headers=HEADERS, timeout=30)

    soup = BeautifulSoup(r.text, "html.parser")

    # ---------- FULL HD IMAGES ----------

    images = []

    for img in soup.select("img"):

        src = img.get("src") or img.get("data-src")

        if not src:
            continue

        if "kensington" not in src:
            continue

        if src.startswith("//"):
            src = "https:" + src

        if "zoom" in src or "large" in src or "xl" in src:
            images.append(src)

    images = list(set(images))


    # ---------- FEATURES ----------

    features = []

    for li in soup.select("ul li"):

        txt = li.get_text(strip=True)

        if len(txt) > 40:
            features.append(txt)


    # ---------- SPECS ----------

    specs = {}

    for row in soup.select("table tr"):

        cols = row.find_all(["td", "th"])

        if len(cols) == 2:
            specs[
                cols[0].get_text(strip=True)
            ] = cols[1].get_text(strip=True)

    return images, features, specs


# ---------------- MASTER FUNCTION ----------------

def process_sku(sku):

    url = search_bing(sku)

    if not url:
        url = search_ddg(sku)

    if not url:
        return {
            "SKU": sku,
            "URL": None,
            "IMAGES": None,
            "FEATURES": None,
            "SPECS": None
        }

    images, features, specs = scrape_product(url)

    return {
        "SKU": sku,
        "URL": url,
        "IMAGES": "\n".join(images),
        "FEATURES": "\n".join(features),
        "SPECS": str(specs)
    }


# ---------------- UI ----------------

file = st.file_uploader("Excel SKU list", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    skus = df["SKU"].dropna().astype(str).tolist()

    results = []

    progress = st.progress(0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exe:

        futures = [exe.submit(process_sku, s) for s in skus]

        for i, f in enumerate(concurrent.futures.as_completed(futures)):

            results.append(f.result())

            progress.progress((i + 1) / len(skus))

    out = pd.DataFrame(results)

    st.dataframe(out)

    st.download_button(
        "Download CSV",
        out.to_csv(index=False),
        "kensington_output.csv"
    )

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

BASE = "https://www.kensington.com"
SEARCH = "https://www.kensington.com/GlobalSearch/QuickSearch/"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.kensington.com/"
}

LOCALES = [
    "en-gb",
    "en-us",
    "de-de",
    "fr-fr",
    "hu-hu"
]


def get_product_url(session, sku):

    for loc in LOCALES:

        try:
            # locale cookie set
            session.cookies.set("site", loc)

            # warmup request
            session.get(BASE, headers=BROWSER_HEADERS, timeout=20)

            r = session.get(
                SEARCH,
                params={"query": sku},
                headers=BROWSER_HEADERS,
                timeout=20
            )

            if "application/json" not in r.headers.get("content-type", ""):
                continue

            data = r.json()

            if data.get("Results"):
                rel = data["Results"][0]["Url"]
                return BASE + rel

        except:
            continue

    return None


def parse_product(url):

    images = []
    features = []
    specs = {}

    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        # HD images
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

        # features
        for li in soup.select("li"):
            t = li.get_text(strip=True)
            if len(t) > 40:
                features.append(t)

        # specs
        for tr in soup.select("table tr"):
            cols = tr.find_all(["td", "th"])
            if len(cols) == 2:
                specs[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

    except:
        pass

    return images, features, specs


st.title("Kensington SKU Scraper")

file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("SKU oszlop hiányzik")
        st.stop()

    session = requests.Session()

    results = []
    skus = df["SKU"].dropna().tolist()

    prog = st.progress(0)

    for i, sku in enumerate(skus):

        st.write("Processing:", sku)

        url = get_product_url(session, str(sku))

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

        prog.progress((i + 1) / len(skus))
        time.sleep(0.4)

    out = pd.DataFrame(results)

    st.dataframe(out)

    out.to_excel("kensington_output.xlsx", index=False)

    st.success("Kész ✔")

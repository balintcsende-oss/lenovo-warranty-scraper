import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

st.title("Kensington scraper – HU search")

# ---------------- SEARCH ----------------

def find_product_url(sku):

    search_url = f"https://www.kensington.com/hu-hu/keres%C3%A9s/?search={sku}"

    r = requests.get(
        search_url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("a"):

        href = a.get("href")

        if href and "/p/" in href:
            return "https://www.kensington.com" + href

    return None


# ---------------- PRODUCT ----------------

def scrape_product(url):

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(r.text, "html.parser")

    # -------- images --------

    images = []

    for img in soup.select("img"):
        src = img.get("src")
        if src and "kensington" in src:
            if src.startswith("//"):
                src = "https:" + src
            images.append(src)

    # -------- features --------

    features = []

    for li in soup.select("li"):
        txt = li.get_text(strip=True)
        if len(txt) > 25:
            features.append(txt)

    # -------- specs --------

    specs = {}

    for row in soup.select("table tr"):
        tds = row.find_all("td")
        if len(tds) == 2:
            specs[
                tds[0].get_text(strip=True)
            ] = tds[1].get_text(strip=True)

    return images, features, specs


# ---------------- UI ----------------

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    results = []

    for sku in df["SKU"]:

        st.write("Keresés:", sku)

        link = find_product_url(sku)

        if not link:
            st.error("Nincs találat")
            continue

        st.success(link)

        images, features, specs = scrape_product(link)

        results.append({
            "SKU": sku,
            "URL": link,
            "IMAGES": "\n".join(images),
            "FEATURES": "\n".join(features),
            "SPECS": str(specs)
        })

        time.sleep(1)

    out = pd.DataFrame(results)

    st.dataframe(out)

    st.download_button(
        "Download CSV",
        out.to_csv(index=False),
        "kensington.csv"
    )

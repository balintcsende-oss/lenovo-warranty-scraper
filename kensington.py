import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

st.title("Kensington scraper – NO browser")

# --------- keresés Binggel ---------

def find_product_url(sku):

    q = f"site:kensington.com {sku}"

    url = "https://www.bing.com/search"

    r = requests.get(
        url,
        params={"q": q},
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("li.b_algo h2 a"):

        link = a.get("href")

        if "/p/" in link:
            return link

    return None


# --------- product scrape ---------

def scrape_product(url):

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(r.text, "html.parser")

    # képek
    images = []

    for img in soup.select("img"):
        src = img.get("src")
        if src and "kensington" in src:
            images.append(src)

    # features
    features = []

    for li in soup.select("ul li"):
        txt = li.get_text(strip=True)
        if len(txt) > 20:
            features.append(txt)

    # specs
    specs = {}

    for row in soup.select("table tr"):
        tds = row.find_all("td")
        if len(tds) == 2:
            specs[tds[0].get_text(strip=True)] = tds[1].get_text(strip=True)

    return images, features, specs


# --------- excel feltöltés ---------

file = st.file_uploader("Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    results = []

    for sku in df["SKU"]:

        st.write("SKU:", sku)

        link = find_product_url(sku)

        if not link:
            st.error("Nincs URL")
            continue

        st.success(link)

        images, features, specs = scrape_product(link)

        row = {
            "SKU": sku,
            "URL": link,
            "IMAGES": "\n".join(images),
            "FEATURES": "\n".join(features),
            "SPECS": str(specs)
        }

        results.append(row)

        time.sleep(2)

    out = pd.DataFrame(results)

    st.dataframe(out)

    st.download_button(
        "Download",
        out.to_csv(index=False),
        "kensington.csv"
    )

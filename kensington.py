import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

st.title("Kensington scraper – REAL API")

# -------- API SEARCH --------

def find_product_url(sku):

    api = "https://www.kensington.com/api/site-search"

    r = requests.get(
        api,
        params={"search": sku},
        headers={"User-Agent": "Mozilla/5.0"}
    )

    data = r.json()

    try:
        item = data["results"][0]
        return "https://www.kensington.com" + item["url"]
    except:
        return None


# -------- PRODUCT SCRAPE --------

def scrape_product(url):

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(r.text, "html.parser")

    images = []

    for img in soup.select("img"):
        src = img.get("src")
        if src and "kensington" in src:
            if src.startswith("//"):
                src = "https:" + src
            images.append(src)

    features = []

    for li in soup.select("li"):
        txt = li.get_text(strip=True)
        if len(txt) > 25:
            features.append(txt)

    specs = {}

    for row in soup.select("table tr"):
        tds = row.find_all("td")
        if len(tds) == 2:
            specs[
                tds[0].get_text(strip=True)
            ] = tds[1].get_text(strip=True)

    return images, features, specs


# -------- UI --------

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
        "Download",
        out.to_csv(index=False),
        "kensington.csv"
    )

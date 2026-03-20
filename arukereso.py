import streamlit as st
import pandas as pd
import cloudscraper

st.title("eMAG Doogee terméklista – Cloudflare bypass")

scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False
    }
)

BASE_URL = "https://www.emag.hu/search-by-url"

params = {
    "source_id": 1,
    "source_type": "brand",
    "brand_id": "doogee",
    "is_legal_page": 1,
    "page": 1
}

all_products = []

for page in range(1, 20):
    params["page"] = page

    response = scraper.get(BASE_URL, params=params)

    if response.status_code != 200:
        st.error(f"Hiba a(z) {page}. oldalon: {response.status_code}")
        break

    data = response.json()
    items = data.get("results", {}).get("items", [])

    if not items:
        break

    for item in items:
        all_products.append({
            "Terméknév": item.get("name"),
            "Ár (Ft)": item.get("price"),
            "Link": item.get("url")
        })

df = pd.DataFrame(all_products)

st.subheader("📄 Talált termékek")
st.dataframe(df)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV letöltése", csv, "emag_doogee.csv", "text/csv")

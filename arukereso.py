import streamlit as st
import requests
import pandas as pd

st.title("eMAG Doogee terméklista – működő API lekérés")

BASE_URL = "https://www.emag.hu/search-by-url"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

params = {
    "source_id": 1,
    "source_type": "brand",
    "brand_id": "doogee",
    "is_legal_page": 1,
    "page": 1
}

all_products = []

for page in range(1, 20):  # max 20 oldalt nézünk át
    params["page"] = page
    r = requests.get(BASE_URL, params=params, headers=headers)

    if r.status_code != 200:
        st.error(f"Hiba a(z) {page}. oldalon: {r.status_code}")
        break

    data = r.json()

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

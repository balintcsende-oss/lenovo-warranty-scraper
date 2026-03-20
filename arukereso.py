import streamlit as st
import requests
import pandas as pd

st.title("eMAG Doogee terméklista – API lekérés")

BASE_URL = "https://www.emag.hu/search-by-url"
PARAMS = {
    "source_id": 1,
    "source_type": "brand",
    "brand_id": "doogee",
    "page": 1
}

st.write("Forrás API:", BASE_URL)

all_products = []

for page in range(1, 10):  # max 10 oldalt nézünk át
    PARAMS["page"] = page
    r = requests.get(BASE_URL, params=PARAMS, headers={"User-Agent": "Mozilla/5.0"})

    if r.status_code != 200:
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

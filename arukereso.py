import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.title("eMAG Doogee terméklista lekérése")

URL = "https://www.emag.hu/brands/brand/doogee?ref=bc"

st.write(f"Adatok forrása: {URL}")

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers)

if response.status_code != 200:
    st.error("Nem sikerült letölteni az oldalt.")
else:
    soup = BeautifulSoup(response.text, "html.parser")

    products = []
    cards = soup.find_all("div", class_="card-item")

    for card in cards:
        name = card.get("data-product-name")
        price = card.get("data-product-price")
        link = card.find("a", class_="card-v2-title")["href"] if card.find("a", class_="card-v2-title") else None

        if name and price:
            products.append({
                "Terméknév": name,
                "Ár (Ft)": int(price),
                "Link": "https://www.emag.hu" + link if link else None
            })

    df = pd.DataFrame(products)

    st.subheader("📄 Talált termékek")
    st.dataframe(df)

    # CSV export
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 CSV letöltése",
        data=csv,
        file_name="emag_doogee.csv",
        mime="text/csv"
    )

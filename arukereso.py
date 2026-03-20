import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.title("Ár lekérdező")

uploaded_file = st.file_uploader("Excel feltöltése (TableAK fül)", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="ÁK")
    st.write("Beolvasott adatok:", df.head())

    def scrape_row(row):
        url = row['Link']
        vpn = row['VPN']
        sku = row['SKU']

        if pd.isna(url) or url.strip() == "":
            return pd.Series([vpn, sku, None, None, None, url], index=["VPN","SKU","Terméknév","Bolt","Ár","Link"])

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            html = r.text
            soup = BeautifulSoup(html, 'html.parser')
        except:
            return pd.Series([vpn, sku, None, None, None, url], index=["VPN","SKU","Terméknév","Bolt","Ár","Link"])

        product_name = None
        # meta tag
        meta_name = soup.find("meta", {"itemprop":"name"})
        if meta_name and meta_name.get("content"):
            product_name = meta_name["content"]
        elif soup.title:
            product_name = soup.title.string

        price = None
        seller = None

        # eMAG
        if "emag" in url.lower():
            match = re.search(r'"price":(\d+)', html)
            price = int(match.group(1)) if match else None
            seller_tag = soup.select_one("div.fs-14 a")
            seller = seller_tag.get_text(strip=True) if seller_tag else "eMAG"

        # Pepita
        elif "pepita" in url.lower():
            price_tag = soup.select_one(".price, .product-price, .main-price")
            if price_tag:
                price_text = "".join(filter(str.isdigit, price_tag.get_text()))
                price = int(price_text) if price_text else None
            seller_tag = soup.select_one(".product-distributor a")
            seller = seller_tag.get_text(strip=True) if seller_tag else "Pepita"

        # Allegro
        elif "allegro" in url.lower():
            seller_tag = soup.select_one(".mpof_ki .mp0t_ji")
            seller = seller_tag.get_text(strip=True) if seller_tag else None
            price = None  # ha akarjuk, ide lehet később beilleszteni az Allegro árat

        # Árkereső (pl. Arukereso)
        else:
            price_tag = soup.select_one('[itemprop="price"]')
            price = float(price_tag["content"]) if price_tag and price_tag.get("content") else None
            shop_tag = soup.select_one(".shopname")
            seller = shop_tag.get_text(strip=True) if shop_tag else None

        return pd.Series([vpn, sku, product_name, seller, price, url], index=["VPN","SKU","Terméknév","Bolt","Ár","Link"])

    st.write("Lekérdezés folyamatban…")
    result_df = df.apply(scrape_row, axis=1)
    st.write(result_df)

    # Excel export lehetőség
    st.download_button(
        "Letöltés Excelben",
        data=result_df.to_excel(index=False),
        file_name="output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

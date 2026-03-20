import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import io
import time

st.title("Ár lekérdező - eMAG/Pepita/Allegro/Árukereső")

uploaded_file = st.file_uploader("Excel feltöltése", type="xlsx")

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    st.write("Munkalapok a fájlban:", xls.sheet_names)
    
    # Első lapot olvassa be
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    st.write("Beolvasott adatok:", df.head())

    result_rows = []

    progress_bar = st.progress(0)
    total = len(df)

    for idx, row in df.iterrows():
        url = row.get("Link")
        vpn = row.get("VPN")
        sku = row.get("SKU")

        # Üres link átugrás
        if pd.isna(url) or str(url).strip() == "":
            result_rows.append([vpn, sku, None, None, None, url])
            continue

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            html = r.text
            soup = BeautifulSoup(html, "html.parser")
        except:
            result_rows.append([vpn, sku, None, None, None, url])
            continue

        product_name = None
        # meta tag
        meta_name = soup.find("meta", {"itemprop":"name"})
        if meta_name and meta_name.get("content"):
            product_name = meta_name["content"]
        elif soup.title:
            product_name = soup.title.string

        price = None
        seller = None

        url_lower = str(url).lower()

        # --------------------- eMAG ---------------------
        if "emag" in url_lower:
            # Figyelem: eMAG botvédelem miatt a scraping nem mindig működik
            price = None
            seller = "iHunt / eMAG (API vagy kézi export szükséges)"
        
        # --------------------- Pepita ---------------------
        elif "pepita" in url_lower:
            price_tag = soup.select_one(".price, .product-price, .main-price")
            if price_tag:
                price_text = "".join(filter(str.isdigit, price_tag.get_text()))
                price = int(price_text) if price_text else None
            seller_tag = soup.select_one(".product-distributor a")
            seller = seller_tag.get_text(strip=True) if seller_tag else "Pepita"

        # --------------------- Allegro ---------------------
        elif "allegro" in url_lower:
            seller_tag = soup.select_one(".mpof_ki .mp0t_ji")
            seller = seller_tag.get_text(strip=True) if seller_tag else None
            price = None  # Allegro ár később bővíthető, mert dinamikus

        # --------------------- Árkereső ---------------------
        else:
            price_tag = soup.select_one('[itemprop="price"]')
            price = float(price_tag["content"]) if price_tag and price_tag.get("content") else None
            shop_tag = soup.select_one(".shopname")
            seller = shop_tag.get_text(strip=True) if shop_tag else None

        result_rows.append([vpn, sku, product_name, seller, price, url])

        progress_bar.progress((idx+1)/total)
        time.sleep(0.2)  # kis szünet, hogy ne bombázzuk a szervereket

    result_df = pd.DataFrame(result_rows, columns=["VPN","SKU","Terméknév","Bolt","Ár","Link"])
    st.write("Eredmény:", result_df.head())

    # --------------------- Excel letöltés ---------------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        label="Letöltés Excelben",
        data=output,
        file_name="output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

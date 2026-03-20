import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time

st.title("eMAG Doogee terméklista – Selenium lekérés")

URL = "https://www.emag.hu/brands/brand/doogee?ref=bc"

# Selenium beállítások
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

st.write("Oldal betöltése…")
driver.get(URL)

# Várunk, hogy a JS betöltse a termékeket
time.sleep(5)

html = driver.page_source
driver.quit()

soup = BeautifulSoup(html, "html.parser")

products = []

cards = soup.find_all("div", class_="card-item")

for card in cards:
    name = card.get("data-product-name")
    price = card.get("data-product-price")
    link_tag = card.find("a", class_="card-v2-title")
    link = "https://www.emag.hu" + link_tag["href"] if link_tag else None

    if name and price:
        products.append({
            "Terméknév": name,
            "Ár (Ft)": int(price),
            "Link": link
        })

df = pd.DataFrame(products)

st.subheader("📄 Talált termékek")
st.dataframe(df)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV letöltése", csv, "emag_doogee.csv", "text/csv")

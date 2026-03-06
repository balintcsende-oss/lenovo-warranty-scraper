import streamlit as st
import pandas as pd
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup


st.title("Dicota SKU scraper")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # SKU oszlop keresése
    sku_col = None

    for col in df.columns:
        if "sku" in col.lower():
            sku_col = col
            break

    if sku_col is None:
        st.error("Nem található SKU oszlop")
        st.stop()

    st.success(f"SKU oszlop: {sku_col}")

    if st.button("Scrape indítása"):

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        titles = []

        progress = st.progress(0)

        for i, sku in enumerate(df[sku_col]):

            if pd.isna(sku):
                titles.append("")
                continue

            sku = str(sku).strip()

            url = f"https://www.dicota.com/search?type=product&q={sku}"

            driver.get(url)

            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            title = ""

            div = soup.find("div", {"li-object": "product.title"})

            if div:
                title = div.text.strip()

            titles.append(title)

            progress.progress((i+1)/len(df))

        driver.quit()

        df["product_title"] = titles

        output = "dicota_output.xlsx"

        df.to_excel(output, index=False)

        with open(output, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name=output
            )

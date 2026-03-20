import streamlit as st
import pandas as pd
import time
import io

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

st.title("Ár lekérdező (Selenium verzió)")

uploaded_file = st.file_uploader("Excel feltöltése", type="xlsx")

# =========================
# Selenium driver indítása
# =========================
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    return driver


# =========================
# Scraper függvény
# =========================
def scrape_with_selenium(driver, row):
    url = row.get("Link")
    vpn = row.get("VPN")
    sku = row.get("SKU")

    if pd.isna(url) or str(url).strip() == "":
        return [vpn, sku, None, None, None, url]

    try:
        driver.get(url)
        time.sleep(3)  # várunk JS betöltésre
    except:
        return [vpn, sku, None, None, None, url]

    product_name = None
    price = None
    seller = None

    url_lower = str(url).lower()

    # ================= eMAG =================
    if "emag" in url_lower:
        try:
            product_name = driver.find_element(By.CSS_SELECTOR, "h1").text
        except:
            pass

        try:
            price_text = driver.find_element(By.CSS_SELECTOR, "[data-testid='price']").text
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            pass

        try:
            seller = driver.find_element(By.CSS_SELECTOR, "div.fs-14 a").text
        except:
            seller = "eMAG"

    # ================= Pepita =================
    elif "pepita" in url_lower:
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text
        except:
            pass

        try:
            price_text = driver.find_element(By.CSS_SELECTOR, ".price, .product-price").text
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            pass

        try:
            seller = driver.find_element(By.CSS_SELECTOR, ".product-distributor a").text
        except:
            seller = "Pepita"

    # ================= Allegro =================
    elif "allegro" in url_lower:
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text
        except:
            pass

        try:
            price_text = driver.find_element(By.CSS_SELECTOR, "[data-testid='price']").text
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            pass

        try:
            seller = driver.find_element(By.CSS_SELECTOR, ".mpof_ki .mp0t_ji").text
        except:
            pass

    # ================= Árkereső =================
    else:
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text
        except:
            pass

        try:
            price_text = driver.find_element(By.CSS_SELECTOR, "[itemprop='price']").get_attribute("content")
            price = float(price_text)
        except:
            pass

        try:
            seller = driver.find_element(By.CSS_SELECTOR, ".shopname").text
        except:
            pass

    return [vpn, sku, product_name, seller, price, url]


# =========================
# FŐ LOGIKA
# =========================
if uploaded_file:

    df = pd.read_excel(uploaded_file)
    st.write("Adatok:", df.head())

    if st.button("Lekérdezés indítása"):

        driver = init_driver()

        results = []
        progress = st.progress(0)

        for i, row in df.iterrows():
            results.append(scrape_with_selenium(driver, row))
            progress.progress((i + 1) / len(df))

        driver.quit()

        result_df = pd.DataFrame(
            results,
            columns=["VPN", "SKU", "Terméknév", "Bolt", "Ár", "Link"]
        )

        st.write("Eredmény:", result_df)

        # Excel export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            label="Letöltés Excelben",
            data=output,
            file_name="eredmeny.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

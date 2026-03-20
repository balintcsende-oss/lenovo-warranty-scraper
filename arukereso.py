import streamlit as st
import pandas as pd
import io
import time
import subprocess
import sys

# ===================================================
# 0️⃣ Playwright telepítés (Cloud kompatibilis)
# ===================================================
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

st.title("Ár lekérdező (Playwright verzió)")

# ===================================================
# 1️⃣ Excel feltöltés
# ===================================================
uploaded_file = st.file_uploader("Excel feltöltése", type="xlsx")

def scrape_page(page, url, vpn, sku):
    if pd.isna(url) or str(url).strip() == "":
        return [vpn, sku, None, None, None, url]

    try:
        page.goto(url, timeout=90000)
        page.wait_for_timeout(3000)  # várunk a JS betöltésére
    except:
        return [vpn, sku, None, None, None, url]

    product_name = None
    price = None
    seller = None
    url_lower = str(url).lower()

    # ================= eMAG =================
    if "emag" in url_lower:
        try:
            product_name = page.locator("h1").first.inner_text()
        except:
            pass
        try:
            price_text = page.locator("[data-testid='price']").first.inner_text()
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            price = None
        try:
            seller = page.locator("div.fs-14 a").first.inner_text()
        except:
            seller = "eMAG"

    # ================= Pepita =================
    elif "pepita" in url_lower:
        try:
            product_name = page.locator("h1").first.inner_text()
        except:
            pass
        try:
            price_text = page.locator(".price, .product-price").first.inner_text()
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            price = None
        try:
            seller = page.locator(".product-distributor a").first.inner_text()
        except:
            seller = "Pepita"

    # ================= Allegro =================
    elif "allegro" in url_lower:
        try:
            product_name = page.locator("h1").first.inner_text()
        except:
            pass
        try:
            price_text = page.locator("[data-testid='price']").first.inner_text()
            price = int("".join(filter(str.isdigit, price_text)))
        except:
            price = None
        try:
            seller = page.locator(".mpof_ki .mp0t_ji").first.inner_text()
        except:
            seller = None

    # ================= Árkereső =================
    else:
        try:
            product_name = page.locator("h1").first.inner_text()
        except:
            pass
        try:
            price_attr = page.locator("[itemprop='price']").first.get_attribute("content")
            price = float(price_attr) if price_attr else None
        except:
            price = None
        try:
            seller = page.locator(".shopname").first.inner_text()
        except:
            seller = None

    return [vpn, sku, product_name, seller, price, url]

# ===================================================
# 2️⃣ Feldolgozás és Streamlit GUI
# ===================================================
if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    st.write("Munkalapok:", xls.sheet_names)

    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    st.write("Beolvasott adatok:", df.head())

    if st.button("Lekérdezés indítása"):

        results = []
        progress = st.progress(0)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            page = browser.new_page()

            for i, row in df.iterrows():
                result = scrape_page(page, row.get("Link"), row.get("VPN"), row.get("SKU"))
                results.append(result)
                progress.progress((i + 1) / len(df))

            browser.close()

        result_df = pd.DataFrame(
            results,
            columns=["VPN","SKU","Terméknév","Bolt","Ár","Link"]
        )

        st.write("Eredmény:", result_df)

        # ================= Excel export =================
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

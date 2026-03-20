import streamlit as st
import pandas as pd
import io
import time

from playwright.sync_api import sync_playwright

st.title("Ár lekérdező (Playwright)")

uploaded_file = st.file_uploader("Excel feltöltése", type="xlsx")


# =========================
# SCRAPER
# =========================
def scrape_page(page, url, vpn, sku):

    if pd.isna(url) or str(url).strip() == "":
        return [vpn, sku, None, None, None, url]

    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)  # várunk JS-re
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
            pass

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
            pass

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
            pass

        try:
            seller = page.locator(".mpof_ki .mp0t_ji").first.inner_text()
        except:
            pass

    # ================= Árkereső =================
    else:
        try:
            product_name = page.locator("h1").first.inner_text()
        except:
            pass

        try:
            price = float(page.locator("[itemprop='price']").first.get_attribute("content"))
        except:
            pass

        try:
            seller = page.locator(".shopname").first.inner_text()
        except:
            pass

    return [vpn, sku, product_name, seller, price, url]


# =========================
# MAIN
# =========================
if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)
    st.write("Munkalapok:", xls.sheet_names)

    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    st.write("Adatok:", df.head())

    if st.button("Lekérdezés indítása"):

        results = []
        progress = st.progress(0)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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

import streamlit as st
import pandas as pd
import io
import requests
from bs4 import BeautifulSoup

st.title("Ár lekérdező (Cloud kompatibilis, BS4)")

uploaded_file = st.file_uploader("Excel feltöltése", type="xlsx")

# ========================
# FUNKCIÓ: oldalak feldolgozása
# ========================
def scrape_page(url, vpn, sku):
    if pd.isna(url) or str(url).strip() == "":
        return [vpn, sku, None, None, None, url]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
    except:
        return [vpn, sku, None, None, None, url]

    product_name = None
    price = None
    seller = None
    url_lower = str(url).lower()

    # ================= eMAG =================
    if "emag" in url_lower:
        # terméknév
        h1 = soup.find("h1")
        if h1:
            product_name = h1.get_text(strip=True)
        # ár
        price_tag = soup.find(attrs={"data-testid": "price"})
        if price_tag:
            price_text = price_tag.get_text()
            price = int("".join(filter(str.isdigit, price_text)))
        # bolt
        seller_tag = soup.select_one("div.fs-14 a")
        seller = seller_tag.get_text(strip=True) if seller_tag else "eMAG"

    # ================= Pepita =================
    elif "pepita" in url_lower:
        h1 = soup.find("h1")
        if h1:
            product_name = h1.get_text(strip=True)
        price_tag = soup.select_one(".price, .product-price")
        if price_tag:
            price_text = price_tag.get_text()
            price = int("".join(filter(str.isdigit, price_text)))
        seller_tag = soup.select_one(".product-distributor a")
        seller = seller_tag.get_text(strip=True) if seller_tag else "Pepita"

    # ================= Allegro =================
    elif "allegro" in url_lower:
        h1 = soup.find("h1")
        if h1:
            product_name = h1.get_text(strip=True)
        seller_tag = soup.select_one(".mpof_ki .mp0t_ji")
        seller = seller_tag.get_text(strip=True) if seller_tag else None
        # ár itt csak statikus, JS ár nem lesz

    # ================= Árkereső =================
    else:
        h1 = soup.find("h1")
        if h1:
            product_name = h1.get_text(strip=True)
        price_tag = soup.select_one("[itemprop='price']")
        if price_tag and price_tag.has_attr("content"):
            try:
                price = float(price_tag["content"])
            except:
                price = None
        seller_tag = soup.select_one(".shopname")
        seller = seller_tag.get_text(strip=True) if seller_tag else None

    return [vpn, sku, product_name, seller, price, url]

# ========================
# MAIN STREAMLIT
# ========================
if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    st.write("Munkalapok:", xls.sheet_names)

    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    st.write("Beolvasott adatok:", df.head())

    if st.button("Lekérdezés indítása"):
        results = []
        progress = st.progress(0)

        for i, row in df.iterrows():
            result = scrape_page(row.get("Link"), row.get("VPN"), row.get("SKU"))
            results.append(result)
            progress.progress((i+1)/len(df))

        result_df = pd.DataFrame(results, columns=["VPN","SKU","Terméknév","Bolt","Ár","Link"])
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

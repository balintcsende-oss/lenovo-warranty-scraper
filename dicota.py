import streamlit as st
import pandas as pd
import requests
import tempfile

st.set_page_config(page_title="Dicota Scraper JSON", layout="wide")
st.title("Dicota SKU → Full Product Data by Handle (JSON)")

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

        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9"
        }

        progress = st.progress(0)
        log = st.empty()

        # Iterálunk a SKU-kon
        for i, sku in enumerate(df[sku_col]):
            if pd.isna(sku):
                results.append({})
                continue
            sku = str(sku).strip()

            # 1️⃣ Handle kinyerése a predictive search-ből
            search_url = f"https://www.dicota.com/search/suggest?q={sku}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"
            try:
                r = requests.get(search_url, headers=headers)
                if r.status_code != 200:
                    log.text(f"{sku} → HTTP {r.status_code}")
                    results.append({})
                    continue

                search_json = r.json()
                products = search_json.get("resources", {}).get("results", {}).get("products", [])

                if not products:
                    log.text(f"{sku} → nincs találat a predictive search-ben")
                    results.append({})
                    continue

                # Vegyük az első találatot
                handle = products[0].get("handle")
                if not handle:
                    log.text(f"{sku} → nincs handle")
                    results.append({})
                    continue

                # 2️⃣ JSON lekérés handle alapján
                json_url = f"https://www.dicota.com/products/{handle}.json"
                r_json = requests.get(json_url, headers=headers)
                if r_json.status_code != 200:
                    log.text(f"{sku} → handle JSON hiba HTTP {r_json.status_code}")
                    results.append({})
                    continue

                data = r_json.json()
                product = data.get("product", {})

                # Adatok kinyerése
                title = product.get("title", "")
                description = product.get("body_html", "")
                vendor = product.get("vendor", "")
                product_type = product.get("product_type", "")
                price = ""
                images = []
                variants = product.get("variants", [])
                if variants:
                    price = variants[0].get("price", "")
                for img in product.get("images", []):
                    images.append(img.get("src", ""))

                # Max 5 kép
                while len(images) < 5:
                    images.append("")

                # Eredmény összegyűjtése
                product_data_ordered = {
                    "sku": sku,
                    "handle": handle,
                    "handle_link": json_url,
                    "title": title,
                    "description": description,
                    "product_type": product_type,
                    "vendor": vendor,
                    "price": price,
                    "image_1": images[0],
                    "image_2": images[1],
                    "image_3": images[2],
                    "image_4": images[3],
                    "image_5": images[4]
                }

                results.append(product_data_ordered)
                log.text(f"{sku} → {title} | {handle}")

            except Exception as e:
                log.text(f"{sku} → ERROR {e}")
                results.append({})

            progress.progress((i+1)/len(df))

        # DataFrame készítése
        result_df = pd.DataFrame(results)

        st.subheader("Eredmények")
        st.dataframe(result_df)

        # Excel export
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        result_df.to_excel(tmp.name, index=False)
        with open(tmp.name, "rb") as f:
            st.download_button(
                "Excel letöltése",
                f,
                file_name="dicota_full_results.xlsx"
            )

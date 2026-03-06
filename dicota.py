import streamlit as st
import pandas as pd
import requests
import tempfile

st.set_page_config(page_title="Dicota Scraper", layout="wide")
st.title("Dicota SKU → Full Product Data by Handle")

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

        # Segédfüggvény: handle alapján scrape JSON
        def scrape_product_by_handle(handle):
            link = f"https://www.dicota.com/products/{handle}.json"
            r = requests.get(link, headers=headers)
            if r.status_code != 200 or not r.text.strip():
                return None
            data = r.json().get("product", {})
            result = {}
            result["handle"] = data.get("handle", "")
            result["title"] = data.get("title", "")
            result["description"] = data.get("body_html", "")
            result["product_type"] = data.get("product_type", "")
            result["vendor"] = data.get("vendor", "")
            variants = data.get("variants", [{}])
            result["price"] = variants[0].get("price", "") if variants else ""
            images = [img.get("src", "") for img in data.get("images", [])]
            while len(images) < 5:
                images.append("")
            for i in range(5):
                result[f"image_{i+1}"] = images[i]
            return result

        # Iterálunk a SKU-kon
        for i, sku in enumerate(df[sku_col]):
            result_dict = {
                "sku": sku if pd.notna(sku) else "",
                "handle": "",
                "handle_link": "",
                "title": "",
                "description": "",
                "product_type": "",
                "vendor": "",
                "price": "",
                "image_1": "",
                "image_2": "",
                "image_3": "",
                "image_4": "",
                "image_5": ""
            }

            if pd.isna(sku):
                results.append(result_dict)
                progress.progress((i + 1) / len(df))
                continue

            sku_str = str(sku).strip()

            # 1️⃣ Keresés a predictive search-ből a handle kinyeréséhez
            search_url = f"https://www.dicota.com/search/suggest?q={sku_str}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"
            try:
                r = requests.get(search_url, headers=headers)
                if r.status_code != 200:
                    log.text(f"{sku_str} → HTTP {r.status_code}")
                    results.append(result_dict)
                    progress.progress((i + 1) / len(df))
                    continue

                # BeautifulSoup-ot használunk a handle kinyerésére
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                link_tag = soup.find("a", class_="predictive-search_line-item")
                handle = ""
                if link_tag and "href" in link_tag.attrs:
                    href = link_tag["href"]
                    if "/products/" in href:
                        handle = href.split("/products/")[1].split("?")[0]

                if not handle:
                    log.text(f"{sku_str} → nincs handle")
                    results.append(result_dict)
                    progress.progress((i + 1) / len(df))
                    continue

                # 2️⃣ Handle alapján lekérjük a teljes adatot a JSON-ból
                product_data = scrape_product_by_handle(handle)
                if product_data:
                    result_dict.update(product_data)
                    result_dict["handle_link"] = f"https://www.dicota.com/products/{handle}.json"

                log.text(f"{sku_str} → {result_dict['title']} | {handle}")

            except Exception as e:
                log.text(f"{sku_str} → ERROR {e}")

            results.append(result_dict)
            progress.progress((i + 1) / len(df))

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

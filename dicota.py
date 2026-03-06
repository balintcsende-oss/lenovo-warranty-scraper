import streamlit as st
import pandas as pd
import requests
import tempfile
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="Dicota Scraper", layout="wide")
st.title("Dicota SKU → Full Product Data (All Variants)")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # SKU oszlop keresése
    sku_col = next((c for c in df.columns if "sku" in c.lower()), None)
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

        def scrape_product_json(handle):
            url = f"https://www.dicota.com/products/{handle}.json"
            r = requests.get(url, headers=headers)
            if r.status_code != 200 or not r.text.strip():
                return None
            data = r.json().get("product", {})
            result = {}

            # Alap adatok
            result["handle"] = data.get("handle", "")
            result["title"] = data.get("title", "")
            result["body_html"] = data.get("body_html", "")
            result["vendor"] = data.get("vendor", "")
            result["product_type"] = data.get("product_type", "")
            result["tags"] = ", ".join(data.get("tags", [])) if isinstance(data.get("tags", []), list) else data.get("tags", "")

            # Options
            for i, option in enumerate(data.get("options", [])):
                result[f"option_{i+1}_name"] = option.get("name", "")
                result[f"option_{i+1}_values"] = ", ".join(option.get("values", []))

            # Variants - minden elérhető mező
            for i, variant in enumerate(data.get("variants", [])):
                for key, value in variant.items():
                    # Ha dict típusú (pl. quantity_rule, quantity_price_breaks), stringre alakítjuk
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    result[f"variant_{i+1}_{key}"] = value

            # Images
            images = [img.get("src", "") for img in data.get("images", [])]
            for i in range(10):
                result[f"image_{i+1}"] = images[i] if i < len(images) else ""

            # Dátumok
            result["created_at"] = data.get("created_at", "")
            result["updated_at"] = data.get("updated_at", "")
            result["published_at"] = data.get("published_at", "")

            return result

        for i, sku in enumerate(df[sku_col]):
            row = {"sku": sku if pd.notna(sku) else "", "handle": "", "handle_link": ""}
            if pd.isna(sku):
                results.append(row)
                progress.progress((i+1)/len(df))
                continue

            sku_str = str(sku).strip()
            # 1️⃣ Predictive search handle kinyeréséhez
            search_url = f"https://www.dicota.com/search/suggest?q={sku_str}&section_id=predictive_search&resources[options][fields]=variants.sku,variants.title,product_type,title,vendor"
            try:
                r = requests.get(search_url, headers=headers)
                if r.status_code != 200:
                    log.text(f"{sku_str} → HTTP {r.status_code}")
                    results.append(row)
                    progress.progress((i+1)/len(df))
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                link_tag = soup.find("a", class_="predictive-search_line-item")
                handle = ""
                if link_tag and "href" in link_tag.attrs:
                    href = link_tag["href"]
                    if "/products/" in href:
                        handle = href.split("/products/")[1].split("?")[0]

                if not handle:
                    log.text(f"{sku_str} → nincs handle")
                    results.append(row)
                    progress.progress((i+1)/len(df))
                    continue

                # JSON alapján teljes adat
                product_data = scrape_product_json(handle)
                if product_data:
                    row.update(product_data)
                    row["handle_link"] = f"https://www.dicota.com/products/{handle}.json"

                log.text(f"{sku_str} → {row.get('title','')} | {handle}")

            except Exception as e:
                log.text(f"{sku_str} → ERROR {e}")

            results.append(row)
            progress.progress((i+1)/len(df))

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
                file_name="dicota_full_all_variants.xlsx"
            )

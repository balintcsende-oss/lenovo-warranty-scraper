import streamlit as st
import pandas as pd
import requests
import tempfile

st.set_page_config(page_title="Dicota Scraper", layout="wide")
st.title("Dicota SKU → Full Product Data by Handle JSON")

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

        # Definiáljuk az oszlopokat
        default_columns = [
            "sku", "handle", "handle_link",
            "title", "description", "product_type", "vendor", "price",
            "image_1", "image_2", "image_3", "image_4", "image_5"
        ]

        for i, sku in enumerate(df[sku_col]):
            # Alap dict minden SKU-ra
            result_dict = {col: "" for col in default_columns}
            if pd.isna(sku):
                results.append(result_dict)
                progress.progress((i + 1) / len(df))
                continue

            sku = str(sku).strip()
            result_dict["sku"] = sku
            handle_link = f"https://www.dicota.com/products/{sku}.json"
            result_dict["handle_link"] = handle_link

            try:
                r = requests.get(handle_link, headers=headers)
                if r.status_code != 200 or not r.text.strip():
                    log.text(f"{sku} → nincs elérhető JSON (HTTP {r.status_code})")
                    results.append(result_dict)
                    progress.progress((i + 1) / len(df))
                    continue

                data = r.json()
                product = data.get("product", {})

                result_dict["handle"] = product.get("handle", "")
                result_dict["title"] = product.get("title", "")
                result_dict["description"] = product.get("body_html", "")
                result_dict["product_type"] = product.get("product_type", "")
                result_dict["vendor"] = product.get("vendor", "")
                variants = product.get("variants", [{}])
                result_dict["price"] = variants[0].get("price", "") if variants else ""

                images = [img.get("src", "") for img in product.get("images", [])]
                while len(images) < 5:
                    images.append("")
                for j in range(5):
                    result_dict[f"image_{j+1}"] = images[j]

                log.text(f"{sku} → {result_dict['title']} | {result_dict['handle']}")

            except Exception as e:
                log.text(f"{sku} → ERROR {e}")

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

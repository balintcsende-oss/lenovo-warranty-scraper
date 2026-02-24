import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from openpyxl import load_workbook

st.title("HP OID + Image Link Generator (300 DPI)")

uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlt (A oszlopban a cikkszámok)",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df["OID"] = ""
    df["LINK"] = ""
    df["IMAGE LINK"] = ""

    base_api = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/search/autocomplete"
    image_api_template = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/{}/contents/I?status[]=L&status[]=O"

    product_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/T?hierarchy=F&status=L&status=O"
    image_page_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/I?hierarchy=F&status=L&status=O"

    headers = {"User-Agent": "Mozilla/5.0"}

    all_image_columns = set()
    progress = st.progress(0)
    total_rows = len(df)

    for i, row in df.iterrows():
        prodnum = row[0]

        if pd.isna(prodnum):
            continue

        params = {
            "query": prodnum,
            "status[]": ["L", "O"],
            "exactSearch": "false"
        }

        try:
            r = requests.get(base_api, params=params, headers=headers, timeout=10)

            if r.status_code == 200:
                data = r.json()

                if data.get("results"):
                    oid = data["results"][0]["oid"]
                    df.at[i, "OID"] = oid

                    product_link = product_link_template.format(oid)
                    image_page_link = image_page_link_template.format(oid)

                    df.at[i, "LINK"] = product_link
                    df.at[i, "IMAGE LINK"] = image_page_link

                    # ===== 300 DPI képek lekérése =====
                    image_api = image_api_template.format(oid)
                    img_r = requests.get(image_api, headers=headers, timeout=10)

                    if img_r.status_code == 200:
                        img_data = img_r.json()

                        pic_counter = 1

                        for item in img_data.get("results", []):
                            if item.get("dpiResolution") == "300":
                                image_url = item.get("imageUrlHttps")

                                col_name = f"PIC LINK {pic_counter}"
                                df.at[i, col_name] = image_url
                                all_image_columns.add(col_name)

                                pic_counter += 1

                else:
                    df.at[i, "OID"] = "Nincs találat"

            else:
                df.at[i, "OID"] = f"API hiba {r.status_code}"

        except Exception:
            df.at[i, "OID"] = "Hiba"

        progress.progress((i + 1) / total_rows)

    # Oszlopok rendezése
    base_columns = ["OID", "LINK", "IMAGE LINK"]
    pic_columns = sorted(all_image_columns, key=lambda x: int(x.split()[-1]))
    final_columns = list(df.columns[:1]) + base_columns + pic_columns

    df = df.reindex(columns=final_columns)

    st.success("Feldolgozás kész!")
    st.dataframe(df)

    # ===== Excel mentés =====
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        label="Excel letöltése",
        data=output,
        file_name="output_with_images.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

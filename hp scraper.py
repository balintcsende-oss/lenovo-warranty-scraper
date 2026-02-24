import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from openpyxl import load_workbook

st.title("HP OID lekérő + link generátor + 300 DPI PNG képek")

uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlt (A oszlopban a cikkszámok)",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df["OID"] = ""
    df["LINK"] = ""
    df["OPEN PRODUCT LINK"] = ""
    df["IMAGE LINK"] = ""
    df["OPEN IMAGE LINK"] = ""

    base_api = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/search/autocomplete"
    image_api_template = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/{}/contents/I?status[]=L&status[]=O"

    product_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/T?hierarchy=F&status=L&status=O"
    image_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/I?hierarchy=F&status=L&status=O"

    headers = {"User-Agent": "Mozilla/5.0"}

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
            response = requests.get(base_api, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get("results"):
                    oid = data["results"][0]["oid"]

                    product_link = product_link_template.format(oid)
                    image_link = image_link_template.format(oid)

                    df.at[i, "OID"] = oid
                    df.at[i, "LINK"] = product_link
                    df.at[i, "IMAGE LINK"] = image_link

                    # ===== 300 DPI PNG PRODUCT IMAGE képek lekérése =====
                    try:
                        img_response = requests.get(
                            image_api_template.format(oid),
                            headers=headers,
                            timeout=10
                        )

                        if img_response.status_code == 200:
                            img_data = img_response.json()

                            pic_index = 1

                            for item in img_data.get("contents", []):

                                dpi = item.get("dpiResolution")
                                doc_type = item.get("documentTypeDetail")
                                image_url = item.get("imageUrlHttps")

                                if (
                                    str(dpi).startswith("300")
                                    and doc_type == "product image"
                                    and image_url
                                    and image_url.lower().endswith(".png")
                                ):
                                    col_name = f"PIC LINK {pic_index}"
                                    df.at[i, col_name] = image_url
                                    pic_index += 1

                    except:
                        pass

                else:
                    df.at[i, "OID"] = "Nincs találat"

            else:
                df.at[i, "OID"] = f"API hiba {response.status_code}"

        except Exception:
            df.at[i, "OID"] = "Hiba"

        progress.progress((i + 1) / total_rows)

    st.success("Feldolgozás kész!")
    st.dataframe(df)

    # ===== Excel mentés openpyxl-lel =====
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    # ===== Hyperlinkek (nem módosítva) =====
    for row in range(2, len(df) + 2):
        product_link = ws[f"C{row}"].value
        image_link = ws[f"E{row}"].value

        if product_link:
            ws[f"D{row}"].value = "OPEN"
            ws[f"D{row}"].hyperlink = product_link
            ws[f"D{row}"].style = "Hyperlink"

        if image_link:
            ws[f"F{row}"].value = "OPEN"
            ws[f"F{row}"].hyperlink = image_link
            ws[f"F{row}"].style = "Hyperlink"

    final_output = BytesIO()
    wb.save(final_output)
    final_output.seek(0)

    st.download_button(
        label="Excel letöltése",
        data=final_output,
        file_name="output_with_filtered_png_images.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

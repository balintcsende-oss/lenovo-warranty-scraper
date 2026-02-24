import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from openpyxl import load_workbook

st.title("HP OID lekérő + link generátor")

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

    # Hyperlinkek beállítása
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
        file_name="output_with_links.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

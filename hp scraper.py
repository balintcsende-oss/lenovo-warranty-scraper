import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.title("HP OID lekérő + link generátor")

uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlt (A oszlopban a cikkszámok)",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Új oszlopok létrehozása
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
                    df.at[i, "OPEN PRODUCT LINK"] = f'=HYPERLINK("{product_link}", "OPEN")'
                    df.at[i, "IMAGE LINK"] = image_link
                    df.at[i, "OPEN IMAGE LINK"] = f'=HYPERLINK("{image_link}", "OPEN")'
                else:
                    df.at[i, "OID"] = "Nincs találat"
            else:
                df.at[i, "OID"] = f"API hiba {response.status_code}"

        except Exception:
            df.at[i, "OID"] = "Hiba"

        progress.progress((i + 1) / total_rows)

    st.success("Feldolgozás kész!")
    st.dataframe(df)

    # ===== Excel export =====
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Hiperlink oszlopok újraírása, hogy valódi Excel linkek legyenek
        for row_num in range(1, len(df) + 1):
            if df.loc[row_num - 1, "LINK"]:
                worksheet.write_formula(
                    row_num, 3,
                    df.loc[row_num - 1, "OPEN PRODUCT LINK"]
                )
            if df.loc[row_num - 1, "IMAGE LINK"]:
                worksheet.write_formula(
                    row_num, 5,
                    df.loc[row_num - 1, "OPEN IMAGE LINK"]
                )

    output.seek(0)

    st.download_button(
        label="Excel letöltése",
        data=output,
        file_name="output_with_links.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

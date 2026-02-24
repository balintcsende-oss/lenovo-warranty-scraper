import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.title("HP OID + Image Link Generator")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Fix oszlopok létrehozása
    df["OID"] = ""
    df["LINK"] = ""
    df["OPEN PRODUCT LINK"] = ""
    df["IMAGE LINK"] = ""
    df["OPEN IMAGE LINK"] = ""

    base_api = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/search/autocomplete"
    image_api_template = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/{}/contents/I?status[]=L&status[]=O"

    product_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/T?hierarchy=F&status=L&status=O"
    image_page_link_template = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/I?hierarchy=F&status=L&status=O"

    headers = {"User-Agent": "Mozilla/5.0"}

    progress = st.progress(0)
    total_rows = len(df)

    max_pic_count = 0

    for i in range(len(df)):

        prodnum = df.iloc[i, 0]

        if pd.isna(prodnum):
            continue

        try:
            r = requests.get(
                base_api,
                params={
                    "query": prodnum,
                    "status[]": ["L", "O"],
                    "exactSearch": "false"
                },
                headers=headers,
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()

                if data.get("results"):

                    oid = data["results"][0]["oid"]

                    product_link = product_link_template.format(oid)
                    image_page_link = image_page_link_template.format(oid)

                    df.at[i, "OID"] = oid
                    df.at[i, "LINK"] = product_link
                    df.at[i, "OPEN PRODUCT LINK"] = product_link
                    df.at[i, "IMAGE LINK"] = image_page_link
                    df.at[i, "OPEN IMAGE LINK"] = image_page_link

                    # ===== 300 DPI képek =====
                    img_r = requests.get(
                        image_api_template.format(oid),
                        headers=headers,
                        timeout=10
                    )

                    if img_r.status_code == 200:
                        img_data = img_r.json()

                        pic_links = []

                        for item in img_data.get("results", []):

                            dpi = item.get("dpiResolution")

                            # Kezeljük int vagy string formátumot
                            if str(dpi).startswith("300"):
                                url = item.get("imageUrlHttps")
                                if url:
                                    pic_links.append(url)

                        # PIC oszlopok létrehozása
                        for idx, link in enumerate(pic_links, start=1):
                            col_name = f"PIC LINK {idx}"
                            df.at[i, col_name] = link

                        max_pic_count = max(max_pic_count, len(pic_links))

        except Exception as e:
            df.at[i, "OID"] = "Hiba"

        progress.progress((i + 1) / total_rows)

    # Hiányzó PIC oszlopok pótlása
    for n in range(1, max_pic_count + 1):
        col = f"PIC LINK {n}"
        if col not in df.columns:
            df[col] = ""

    st.success("Kész!")
    st.dataframe(df)

    # ===== Excel mentés hyperlinkkel =====
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Excel letöltése",
        output,
        "output.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

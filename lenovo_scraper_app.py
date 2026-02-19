import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.title("Lenovo Warranty Scraper (No Browser Version)")

uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlt", type=["xlsx", "xlsm"]
)

if uploaded_file is not None:

    df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)

    if "ProductLink" not in df.columns:
        st.error("Nem található ProductLink oszlop!")
        st.stop()

    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    progress = st.progress(0)
    total = len(df)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for index, row in df.iterrows():
        url = row["ProductLink"]

        if pd.isna(url):
            continue

        try:
            response = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")

            base_row = soup.find("tr", {"data": "Base Warranty"})
            upgrade_row = soup.find("tr", {"data": "Included Upgrade"})

            if base_row:
                base_value = base_row.find("div", class_="rightValue")
                if base_value:
                    df.at[index, "Base Warranty"] = base_value.text.strip()

            if upgrade_row:
                upgrade_value = upgrade_row.find("div", class_="rightValue")
                if upgrade_value:
                    df.at[index, "Included Upgrade"] = upgrade_value.text.strip()

        except Exception as e:
            st.warning(f"Hiba ennél a linknél: {url}")

        progress.progress((index + 1) / total)

    st.success("Feldolgozás kész!")

    output_file = "lenovo_warranty_result.xlsx"
    df.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button(
            "Letöltés",
            f,
            file_name="lenovo_warranty_result.xlsx"
        )

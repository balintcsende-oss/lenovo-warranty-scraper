import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.title("Lenovo Warranty Cloud Version")

uploaded_file = st.file_uploader(
    "Excel feltöltése (xls, xlsx, xlsm)",
    type=["xls", "xlsx", "xlsm"]
)

def get_warranty_data(sku):
    url = f"https://psref.lenovo.com/api/model/Info/SpecData?model_code={sku}&show_hyphen=false"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://psref.lenovo.com/Detail?M={sku}",
        "Origin": "https://psref.lenovo.com"
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        return "Hiba", "Hiba"

    data = response.json()

    base_warranty = "Nincs adat"
    included_upgrade = "Nincs adat"

    # SERVICE rész bejárása
    for item in data:
        if item.get("title") == "SERVICE":
            if item.get("name") == "Base Warranty":
                base_warranty = item.get("content", ["Nincs adat"])[0]
            if item.get("name") == "Included Upgrade":
                included_upgrade = item.get("content", ["Nincs adat"])[0]

    return base_warranty, included_upgrade


if uploaded_file:

    df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop a 3. sorban.")
        st.stop()

    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    progress = st.progress(0)

    for i, row in df.iterrows():
        sku = str(row["SKU"]).strip()

        base, included = get_warranty_data(sku)

        df.at[i, "Base Warranty"] = base
        df.at[i, "Included Upgrade"] = included

        progress.progress((i + 1) / len(df))

    st.success("Kész!")

    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "Eredmény letöltése",
        data=output,
        file_name="lenovo_warranty_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

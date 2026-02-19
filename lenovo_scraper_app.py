import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="Lenovo Warranty Scraper", layout="wide")

st.title("Lenovo Warranty Scraper")
st.write("Feltöltött Excel (.xls, .xlsx, .xlsm) fájl alapján lekéri a Base Warranty és Included Upgrade értékeket.")

# 1️⃣ Excel feltöltés
uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlodat (xls, xlsx, xlsm)", 
    type=["xls", "xlsx", "xlsm"]
)
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Hiba a fájl beolvasásakor: {e}")
        st.stop()

    if "SKU" not in df.columns:
        st.error("A fájl nem tartalmaz 'SKU' oszlopot.")
        st.stop()

    # 2️⃣ Új oszlopok létrehozása
    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    # 3️⃣ SpecData API lekérés
    st.info("Garanciaadatok lekérése a SpecData API-ból...")
    progress_text = st.empty()
    for i, row in df.iterrows():
        sku = row["SKU"]
        api_url = f"https://psref.lenovo.com/api/model/Info/SpecData?model_code={sku}&show_hyphen=false"
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            specdata = response.json()

            # SERVICE rész kinyerése
            service = specdata.get("Specifications", {}).get("SERVICE", {})
            df.at[i, "Base Warranty"] = service.get("Base Warranty", "")
            df.at[i, "Included Upgrade"] = service.get("Included Upgrade", "")
        except Exception as e:
            df.at[i, "Base Warranty"] = "Hiba"
            df.at[i, "Included Upgrade"] = "Hiba"

        # Frissítjük a progress
        progress_text.text(f"Feldolgozás: {i+1}/{len(df)}")

    st.success("Garanciaadatok lekérése kész!")

    # 4️⃣ Excel letöltés lehetősége
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="Mentés Excelként",
        data=output,
        file_name="lenovo_warranty_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

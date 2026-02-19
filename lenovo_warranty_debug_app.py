import streamlit as st
import pandas as pd
from io import BytesIO
import requests

st.set_page_config(page_title="Lenovo Warranty Debug", layout="wide")

st.title("Lenovo Warranty Scraper - Debug")
st.write("Feltöltött Excel fájl alapján lekéri a Base Warranty és Included Upgrade értékeket, és megmutatja a teljes JSON-t minden SKU-hoz.")

# 1️⃣ Excel feltöltés
uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlodat (xls, xlsx, xlsm)", 
    type=["xls", "xlsx", "xlsm"]
)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)  # A3 a fejléc
    except Exception as e:
        st.error(f"Hiba a fájl beolvasásakor: {e}")
        st.stop()

    if "SKU" not in df.columns:
        st.error("A fájl nem tartalmaz 'SKU' oszlopot a 3. sorban.")
        st.stop()

    # 2️⃣ Új oszlopok létrehozása
    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    # 3️⃣ Lekérés a PSREF API-ból
    st.info("Garanciaadatok lekérése a PSREF SpecData API-ból...")
    progress_text = st.empty()

    for i, row in df.iterrows():
        sku = row["SKU"]
        api_url = f"https://psref.lenovo.com/api/model/Info/SpecData?model_code={sku}&show_hyphen=false"
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            specdata = response.json()

            # ⚡ Debug: mutatjuk a teljes JSON-t Streamlit-ben
            st.subheader(f"SKU: {sku}")
            st.json(specdata)

            # SERVICE rész kinyerése
            service = specdata.get("Specifications", {}).get("SERVICE", {})
            df.at[i, "Base Warranty"] = service.get("Base Warranty", "Nincs adat")
            df.at[i, "Included Upgrade"] = service.get("Included Upgrade", "Nincs adat")
        except Exception as e:
            df.at[i, "Base Warranty"] = "Hiba"
            df.at[i, "Included Upgrade"] = "Hiba"
            st.warning(f"Hiba a lekérésnél SKU={sku}: {e}")

        progress_text.text(f"Feldolgozás: {i+1}/{len(df)}")

    st.success("Garanciaadatok lekérése kész!")

    # 4️⃣ Excel letöltés lehetősége
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="Mentés Excelként",
        data=output,
        file_name="lenovo_warranty_debug_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

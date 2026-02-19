import streamlit as st
import pandas as pd
from io import BytesIO
import requests

st.set_page_config(page_title="Lenovo Warranty Scraper", layout="wide")

st.title("Lenovo Warranty Scraper")
st.write("Feltöltött Excel (.xls, .xlsx, .xlsm) fájl alapján lekéri a Base Warranty és Included Upgrade értékeket a PSREF API-ból.")

# 1️⃣ Excel feltöltés
uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlodat (xls, xlsx, xlsm)", 
    type=["xls", "xlsx", "xlsm"]
)

if uploaded_file:
    try:
        # header=2 → 3. sor a fejléc
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)
    except Exception as e:
        st.error(f"Hiba a fájl beolvasásakor: {e}")
        st.stop()

    if "SKU" not in df.columns:
        st.error("A fájl nem tartalmaz 'SKU' oszlopot a 3. sorban.")
        st.stop()

    # 2️⃣ Új oszlopok létrehozása
    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    # 3️⃣ Garanciaadatok lekérése az API-ból
    st.info("Garanciaadatok lekérése a PSREF SpecData API-ból...")
    progress_text = st.empty()

    for i, row in df.iterrows():
        sku = row["SKU"]
        api_url = f"https://psref.lenovo.com/api/model/Info/SpecData?model_code={sku}&show_hyphen=false"
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            specdata = response.json()

             # ⚡ Debug: mutatjuk a JSON-t Streamlit-ben
            st.json(specdata)  # <-- ide másold be

            # SERVICE rész kinyerése
            service = specdata.get("Specifications", {}).get("SERVICE", {})
            df.at[i, "Base Warranty"] = service.get("Base Warranty", "Nincs adat")
            df.at[i, "Included Upgrade"] = service.get("Included Upgrade", "Nincs adat")
        except Exception:
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



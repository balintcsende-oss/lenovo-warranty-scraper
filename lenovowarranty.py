import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from time import sleep

st.title("Lenovo SKU Spec Extractor")

# --- 1. Excel feltöltése ---
uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt, ahol a SKU az A3-ban található", type=["xlsx"])

if uploaded_file:
    # --- 2. Excel beolvasása A3-tól ---
    df = pd.read_excel(uploaded_file, skiprows=2)

    if 'SKU' not in df.columns:
        st.error("Az Excel fájlban nincs 'SKU' oszlop a harmadik sorban!")
    else:
        st.info(f"{len(df)} SKU-t találtam a táblázatban.")
        
        # --- 3. API paraméterek ---
        base_url = "https://psref.lenovo.com/api/model/Info/SpecData"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://psref.lenovo.com/"
        }
        wanted_specs = ["Base Warranty", "Included Upgrade"]

        # --- 4. Üres oszlopok ---
        for spec in wanted_specs:
            df[spec] = ""

        # --- 5. Lekérés minden SKU-hoz ---
        progress_text = "Lekérési folyamat..."
        my_bar = st.progress(0)
        
        for idx, row in df.iterrows():
            sku = row["SKU"]
            params = {"model_code": sku}

            try:
                response = requests.get(base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

                spec_data = data['data'].get('SpecData', [])

                for item in spec_data:
                    spec_name = item.get('name', '')
                    content_list = item.get('content', [])
                    if spec_name in wanted_specs:
                        df.at[idx, spec_name] = ", ".join(content_list)

                sleep(0.2)  # ne terheljük az API-t

            except Exception as e:
                st.warning(f"Hiba SKU={sku} esetén: {e}")

            # Frissítjük a progress bar-t
            my_bar.progress((idx + 1) / len(df))

        st.success("Lekérés kész!")

        # --- 6. Táblázat megjelenítése ---
        st.dataframe(df)

        # --- 7. Excel letöltése ---
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Töltsd le az eredményt Excel-ben",
            data=output,
            file_name="sku_with_specs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

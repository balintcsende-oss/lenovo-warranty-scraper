import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.title("HP OID lekérő")

# ===== 1️⃣ Excel feltöltése =====
uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt (cikkszámok az A oszlopban)", type=["xlsx"])

if uploaded_file:
    # Excel beolvasása
    df = pd.read_excel(uploaded_file)
    
    st.write("Eredeti adatok:")
    st.dataframe(df)
    
    # B és C oszlop létrehozása
    df["OID"] = ""
    df["LINK"] = ""
    
    base_api = "https://pcb.inc.hp.com/api/catalogs/hu-hu/nodes/search/autocomplete"
    base_link = "https://pcb.inc.hp.com/webapp/#/hu-hu/{}/T?hierarchy=F&status=L&status=O"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # ===== 2️⃣ Feldolgozás =====
    for i, row in df.iterrows():
        prodnum = row[0]  # A oszlop (0 index)
        if pd.isna(prodnum):
            continue
        
        st.write(f"Feldolgozás: {prodnum}")
        
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
                    df.at[i, "OID"] = oid
                    df.at[i, "LINK"] = base_link.format(oid)
                else:
                    df.at[i, "OID"] = "Nincs találat"
            else:
                df.at[i, "OID"] = f"API hiba {response.status_code}"
        except Exception:
            df.at[i, "OID"] = "Hiba"
    
    st.write("Feldolgozott adatok:")
    st.dataframe(df)
    
    # ===== 3️⃣ Excel letöltés =====
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    st.download_button(
        label="Mentés Excel fájlba",
        data=output,
        file_name="output_with_oid.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

import streamlit as st
import pandas as pd
import io

st.title("VPN Product Link Generator")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # Ellenőrizzük a szükséges oszlopokat
    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
    else:

        def generate_link(vpn, brand):
            if pd.isna(vpn) or pd.isna(brand):
                return ""

            vpn = str(vpn)
            brand = str(brand).strip()

            if brand == "Philips":
                vpn_formatted = vpn.replace("/", "_")
                return f"https://www.philips.hu/c-p/{vpn_formatted}/"

            elif brand == "AOC":
                vpn_formatted = vpn.lower()
                return f"https://www.aoc.com/hu/gaming/monitors/{vpn_formatted}"

            elif brand == "Viewsonic":
                return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"

            else:
                return ""

        # Product link oszlop létrehozása
        df["Product link"] = df.apply(lambda row: generate_link(row["VPN"], row["Brand"]), axis=1)

        st.subheader("Eredmény")
        st.dataframe(df)

        # Excel mentés openpyxl-lel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            label="Eredmény letöltése Excel formátumban",
            data=output,
            file_name="generated_links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

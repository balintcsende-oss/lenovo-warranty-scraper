import streamlit as st
import pandas as pd
from io import BytesIO
import asyncio
from playwright.async_api import async_playwright

st.set_page_config(page_title="Lenovo Warranty Scraper", layout="wide")

st.title("Lenovo Warranty Scraper (Playwright JS extract)")
st.write("Feltöltött Excel (.xls, .xlsx, .xlsm) fájl alapján lekéri a garancia adatokat a Lenovo oldalról.")

# 1️⃣ Excel feltöltés
uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlodat (xls, xlsx, xlsm)", 
    type=["xls", "xlsx", "xlsm"]
)
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)  # 3. sor a fejléc
    except Exception as e:
        st.error(f"Hiba a fájl beolvasásakor: {e}")
        st.stop()

    if "SKU" not in df.columns:
        st.error("A fájl nem tartalmaz 'SKU' oszlopot a 3. sorban.")
        st.stop()

    # 2️⃣ Új oszlopok létrehozása
    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""

    # 3️⃣ Playwright async kód
    async def extract_warranty(skus):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Cloud-ban headless kell
            page = await browser.new_page()
            results = []

            for sku in skus:
                # PSREF oldal
                url = f"https://psref.lenovo.com/Detail/{sku}/{sku}?M={sku}"
                try:
                    await page.goto(url, timeout=30000)
                    # itt kinyerjük a garancia adatot JS változóból
                    service_data = await page.evaluate("""
                        () => {
                            try {
                                let tr_list = document.querySelectorAll("tr.as_level2");
                                let base = "", included = "";
                                tr_list.forEach(tr => {
                                    let key = tr.getAttribute("data") || "";
                                    let val = tr.querySelector("div.rightValue")?.innerText || "";
                                    if(key === "Base Warranty") base = val;
                                    if(key === "Included Upgrade") included = val;
                                });
                                return {base, included};
                            } catch(e) {
                                return {base: "Hiba", included: "Hiba"};
                            }
                        }
                    """)
                    results.append(service_data)
                except Exception as e:
                    results.append({"base": "Hiba", "included": "Hiba"})
            await browser.close()
            return results

    st.info("Garanciaadatok lekérése a Playwright-tal...")
    warranty_data = asyncio.run(extract_warranty(df["SKU"].tolist()))

    # 4️⃣ Adatok beírása a DataFrame-be
    for i, data in enumerate(warranty_data):
        df.at[i, "Base Warranty"] = data.get("base", "Hiba")
        df.at[i, "Included Upgrade"] = data.get("included", "Hiba")

    st.success("Garanciaadatok lekérése kész!")

    # 5️⃣ Excel letöltés lehetősége
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="Mentés Excelként",
        data=output,
        file_name="lenovo_warranty_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

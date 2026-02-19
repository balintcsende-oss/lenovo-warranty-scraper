import streamlit as st
import pandas as pd
import asyncio
import subprocess

# Telepítjük a Chromiumot Playwright-hoz (Streamlit Cloud esetén)
subprocess.run(["playwright", "install", "chromium"], check=True)

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

st.title("Lenovo Warranty Scraper")

# .xlsx és .xlsm engedélyezése
uploaded_file = st.file_uploader(
    "Töltsd fel az Excel fájlt", type=["xlsx", "xlsm"]
)

MAX_CONCURRENT = 5  # egyszerre hány lapot nyitunk

if uploaded_file is not None:
    # Pandas engine='openpyxl' mindkét formátumhoz működik
    df = pd.read_excel(uploaded_file, engine='openpyxl', header=2)
    df["Base Warranty"] = ""
    df["Included Upgrade"] = ""
    
    st.write("Fájl beolvasva:", df.shape)

    st.write("Feldolgozás indul, kérlek várj...")

    async def fetch_warranty(page, index, url):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")

            base_element = await page.query_selector(
                'tr[data="Base Warranty"] td.alignleft > div.rightValue'
            )
            base_warranty = await base_element.inner_text() if base_element else ""

            upgrade_element = await page.query_selector(
                'tr[data="Included Upgrade"] td.alignleft > div.rightValue'
            )
            included_upgrade = await upgrade_element.inner_text() if upgrade_element else ""

            df.at[index, "Base Warranty"] = base_warranty.strip()
            df.at[index, "Included Upgrade"] = included_upgrade.strip()

        except PlaywrightTimeoutError:
            st.warning(f"Timeout ennél a linknél: {url}")
        except Exception as e:
            st.warning(f"Hiba ennél a linknél: {url}, {e}")

    async def extract_all_warranty():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            sem = asyncio.Semaphore(MAX_CONCURRENT)

            async def sem_task(index, url):
                async with sem:
                    page = await browser.new_page()
                    await fetch_warranty(page, index, url)
                    await page.close()

            tasks = []
            for index, row in df.iterrows():
                url = row["ProductLink"]
                if pd.isna(url):
                    continue
                tasks.append(asyncio.create_task(sem_task(index, url)))

            await asyncio.gather(*tasks)
            await browser.close()

    asyncio.run(extract_all_warranty())

    st.success("Feldolgozás kész!")

    # Letöltés
    output_file = "lenovo_warranty_result.xlsx"
    df.to_excel(output_file, index=False)
    st.download_button(
        "Letöltés", output_file, file_name="lenovo_warranty_result.xlsx"
    )

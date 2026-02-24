import streamlit as st
import pandas as pd
import io
import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

st.title("VPN Product Link + High-Res Gallery Images (Playwright)")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
        st.stop()

    # -------------------------
    # Product link generálás
    # -------------------------
    def generate_link(vpn, brand):
        vpn = str(vpn)
        brand = str(brand).strip()

        if brand.lower() == "philips":
            return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"
        elif brand.lower() == "aoc":
            return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"
        elif brand.lower() == "viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
        return ""

    df["Product link"] = df.apply(lambda r: generate_link(r["VPN"], r["Brand"]), axis=1)

    # -------------------------
    # Playwright galéria lekérés
    # -------------------------
    async def get_gallery_images(playwright, url, brand):
        images = []
        try:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_timeout(3000)  # JS renderre várunk

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            if brand.lower().startswith("view"):
                container = soup.select_one("div#overviewGallery")
                if container:
                    for img in container.find_all("img"):
                        if img.has_attr("srcset"):
                            srcset = img["srcset"].split(",")
                            largest = srcset[-1].strip().split(" ")[0]
                            images.append(largest)
                        else:
                            src = img.get("data-full") or img.get("src")
                            if src and src.startswith("http"):
                                images.append(src)

            elif brand.lower() == "philips":
                gallery_imgs = soup.find_all(
                    "img",
                    class_="p-picture p-normal-view p-is-zoomable p-lazy-handled"
                )
                for img in gallery_imgs:
                    if img.has_attr("srcset"):
                        srcset = img["srcset"].split(",")
                        largest = srcset[-1].strip().split(" ")[0]
                        images.append(largest)
                    else:
                        src = img.get("src")
                        if src and src.startswith("http"):
                            images.append(src)

            elif brand.lower() == "aoc":
                container = soup.select_one("div.image-carousel")
                if container:
                    for img in container.find_all("img"):
                        src = img.get("data-zoom-image") or img.get("src")
                        if src and src.startswith("http"):
                            images.append(src)

            images = list(dict.fromkeys(images))  # duplikátumok
            await browser.close()

        except Exception as e:
            st.warning(f"Hiba történt: {url} ({str(e)})")

        return images

    st.info("Oldalak betöltése és galéria képek kigyűjtése, ez eltarthat pár másodpercig...")

    # -------------------------
    # Async lekérés minden product linkhez
    # -------------------------
    async def process_all():
        all_images = []
        async with async_playwright() as p:
            for idx, row in df.iterrows():
                imgs = await get_gallery_images(p, row["Product link"], row["Brand"])
                all_images.append(imgs)
        return all_images

    all_images = asyncio.run(process_all())

    # -------------------------
    # Pick link oszlopok
    # -------------------------
    max_imgs = max(len(imgs) for imgs in all_images) if all_images else 0
    for i in range(max_imgs):
        df[f"Pick link {i+1}"] = [imgs[i] if i < len(imgs) else "" for imgs in all_images]

    st.subheader("Eredmény")
    st.dataframe(df)

    # -------------------------
    # Excel mentés
    # -------------------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        label="Letöltés Excel fájl",
        data=output.getvalue(),
        file_name="product_links_with_gallery.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

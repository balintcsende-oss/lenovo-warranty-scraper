import streamlit as st
import pandas as pd
import io
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

st.title("VPN Product Link + High-Res Gallery Images")

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

        if brand == "Philips":
            return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"
        elif brand == "AOC":
            return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"
        elif brand.lower() == "viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
        return ""

    df["Product link"] = df.apply(lambda r: generate_link(r["VPN"], r["Brand"]), axis=1)

    # -------------------------
    # Selenium driver setup
    # -------------------------
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        ChromeDriverManager().install(),
        options=chrome_options
    )

    # -------------------------
    # Galéria képek kigyűjtése márkánként
    # -------------------------
    def get_gallery_images(url, brand):
        images = []
        try:
            driver.get(url)
            time.sleep(3)  # vár a JS betöltésre

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # -------- ViewSonic --------
            if brand.lower().startswith("view"):
                container = soup.select_one("div#overviewGallery")
                if container:
                    for img in container.find_all("img"):
                        # srcset vagy src
                        if img.has_attr("srcset"):
                            srcset = img["srcset"].split(",")
                            largest = srcset[-1].strip().split(" ")[0]
                            images.append(largest)
                        else:
                            src = img.get("data-full") or img.get("src")
                            if src and src.startswith("http"):
                                images.append(src)

            # -------- Philips --------
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

            # -------- AOC --------
            elif brand.lower() == "aoc":
                container = soup.select_one("div.image-carousel")
                if container:
                    for img in container.find_all("img"):
                        src = img.get("data-zoom-image") or img.get("src")
                        if src and src.startswith("http"):
                            images.append(src)

            # duplikátumok eltávolítása
            images = list(dict.fromkeys(images))

        except Exception as e:
            st.warning(f"Hiba történt: {url}")
        return images

    st.info("Oldalak betöltése és galéria képek kigyűjtése, ez eltarthat néhány másodpercig...")

    all_images = []
    for idx, row in df.iterrows():
        imgs = get_gallery_images(row["Product link"], row["Brand"])
        all_images.append(imgs)

    # -------------------------
    # Pick link oszlopok létrehozása
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

    # -------------------------
    # Driver lezárása
    # -------------------------
    driver.quit()

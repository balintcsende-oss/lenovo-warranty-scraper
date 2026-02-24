import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("VPN Product Link + High-Res Gallery Images")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
    else:

        # Product link generáló
        def generate_link(vpn, brand):
            vpn = str(vpn)
            brand = str(brand).strip()
            if brand == "Philips":
                return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"
            elif brand == "AOC":
                return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"
            elif brand == "ViewSonic":
                return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
            else:
                return ""

        df["Product link"] = df.apply(lambda r: generate_link(r["VPN"], r["Brand"]), axis=1)

        # Brand-specifikus galéria kép kigyűjtés
        def get_gallery_images(url, brand):
            try:
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, "html.parser")
                images = []

                if brand == "ViewSonic":
                    container = soup.select_one("div#overviewGallery")
                    if container:
                        for img in container.find_all("img"):
                            # Legnagyobb elérhető kép
                            full = img.get("data-full") or img.get("src")
                            if full and full.startswith("http"):
                                images.append(full)

                elif brand == "Philips":
                    # minden galéria kép
                    gallery_imgs = soup.find_all("img", class_="p-picture p-normal-view p-is-zoomable p-lazy-handled")
                    for img in gallery_imgs:
                        if img.has_attr("srcset"):
                            srcset = img["srcset"].split(",")
                            # a legnagyobb felbontású kép a lista végén
                            max_img = srcset[-1].strip().split(" ")[0]
                            images.append(max_img)
                        else:
                            src = img.get("src")
                            if src and src.startswith("http"):
                                images.append(src)

                elif brand == "AOC":
                    container = soup.select_one("div.image-carousel")
                    if container:
                        for img in container.find_all("img"):
                            src = img.get("data-zoom-image") or img.get("src")
                            if src and src.startswith("http"):
                                images.append(src)

                return images
            except:
                return []

        st.info("A galéria képek lekérése eltarthat néhány másodpercig minden oldalon...")

        # Képek kigyűjtése minden product linkhez
        all_images = []
        for idx, row in df.iterrows():
            images = get_gallery_images(row["Product link"], row["Brand"])
            all_images.append(images)

        # Pick link oszlopok létrehozása dinamikusan
        max_imgs = max(len(imgs) for imgs in all_images) if all_images else 0
        for i in range(max_imgs):
            df[f"Pick link {i+1}"] = [imgs[i] if i < len(imgs) else "" for imgs in all_images]

        st.subheader("Eredmény")
        st.dataframe(df)

        # Excel mentése openpyxl-lel
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

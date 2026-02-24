import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("ViewSonic VPN → Gallery Image Scraper")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
        st.stop()

    # -------------------------------------------------
    # Product link generálás (csak ViewSonic)
    # -------------------------------------------------
    def generate_link(vpn, brand):
        vpn = str(vpn).strip()
        brand = str(brand).strip().lower()

        if brand == "viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
        return ""

    df["Product link"] = df.apply(
        lambda r: generate_link(r["VPN"], r["Brand"]), axis=1
    )

    # -------------------------------------------------
    # ViewSonic galéria képek lekérése
    # -------------------------------------------------
    def get_viewsonic_gallery(url):

        images = []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            container = soup.select_one("div#overviewGallery")

            if not container:
                return []

            for img in container.find_all("img"):

                # 1️⃣ srcset → legnagyobb kép
                if img.has_attr("srcset"):
                    srcset = img["srcset"].split(",")
                    largest = srcset[-1].strip().split(" ")[0]
                    images.append(largest)

                # 2️⃣ data-original
                elif img.get("data-original"):
                    images.append(img.get("data-original"))

                # 3️⃣ data-src
                elif img.get("data-src"):
                    images.append(img.get("data-src"))

                # 4️⃣ fallback src
                else:
                    src = img.get("src")
                    if src and src.startswith("http"):
                        images.append(src)

            # duplikátumok eltávolítása
            images = list(dict.fromkeys(images))

            # csak valódi képfájlok
            images = [
                img for img in images
                if any(ext in img.lower() for ext in [".jpg", ".jpeg", ".png"])
            ]

        except Exception:
            return []

        return images

    st.info("ViewSonic galéria képek lekérése...")

    # -------------------------------------------------
    # Minden ViewSonic sor feldolgozása
    # -------------------------------------------------
    all_images = []

    for idx, row in df.iterrows():
        if row["Brand"].strip().lower() == "viewsonic":
            imgs = get_viewsonic_gallery(row["Product link"])
        else:
            imgs = []

        all_images.append(imgs)

    # -------------------------------------------------
    # Pick link oszlopok létrehozása
    # -------------------------------------------------
    max_imgs = max(len(imgs) for imgs in all_images) if all_images else 0

    for i in range(max_imgs):
        df[f"Pick link {i+1}"] = [
            imgs[i] if i < len(imgs) else ""
            for imgs in all_images
        ]

    st.subheader("Eredmény")
    st.dataframe(df)

    # -------------------------------------------------
    # Excel mentés
    # -------------------------------------------------
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    output.seek(0)

    st.download_button(
        label="Letöltés Excel fájl",
        data=output.getvalue(),
        file_name="viewsonic_gallery_images.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

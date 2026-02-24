import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("ViewSonic VPN → Gallery Image Scraper")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if not all(col in df.columns for col in ["VPN", "Brand"]):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
        st.stop()

    # -------------------------------------------------
    # Product link generálás
    # -------------------------------------------------
    def generate_link(vpn, brand):
        if str(brand).strip().lower() == "viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{str(vpn).strip()}"
        return ""

    df["Product link"] = df.apply(
        lambda r: generate_link(r["VPN"], r["Brand"]), axis=1
    )

    # -------------------------------------------------
    # ViewSonic galéria lekérés (JS nélküli JSON fallback)
    # -------------------------------------------------
    def get_viewsonic_gallery(url):

        images = []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # 1️⃣ Normál HTML galéria
            container = soup.select_one("div#overviewGallery")
            if container:
                for img in container.find_all("img"):
                    if img.has_attr("srcset"):
                        srcset = img["srcset"].split(",")
                        largest = srcset[-1].strip().split(" ")[0]
                        images.append(largest)

            # 2️⃣ Ha csak 1 kép → scriptből próbáljuk
            if len(images) <= 1:

                scripts = soup.find_all("script")

                for script in scripts:
                    if script.string:
                        text = script.string

                        if "jpg" in text or "png" in text:
                            parts = text.split('"')
                            for part in parts:
                                if part.startswith("http") and any(
                                    ext in part.lower()
                                    for ext in [".jpg", ".jpeg", ".png"]
                                ):
                                    if not any(
                                        x in part.lower()
                                        for x in ["logo", "icon", "sprite", "thumb"]
                                    ):
                                        images.append(part)

            # duplikátum eltávolítás
            images = list(dict.fromkeys(images))

        except Exception:
            return []

        return images

    st.info("ViewSonic galéria képek lekérése...")

    all_images = []

    for _, row in df.iterrows():
        if str(row["Brand"]).strip().lower() == "viewsonic":
            imgs = get_viewsonic_gallery(row["Product link"])
        else:
            imgs = []

        all_images.append(imgs)

    # -------------------------------------------------
    # Pick link oszlopok
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
    # Excel export
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

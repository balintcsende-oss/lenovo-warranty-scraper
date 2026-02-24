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
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # 🔎 1️⃣ próbáljuk a HTML galériát
        container = soup.select_one("div#overviewGallery")
        if container:
            for img in container.find_all("img"):
                if img.has_attr("srcset"):
                    srcset = img["srcset"].split(",")
                    largest = srcset[-1].strip().split(" ")[0]
                    images.append(largest)

        # 🔎 2️⃣ ha csak 1 kép van → keresünk script-ben
        if len(images) <= 1:

            scripts = soup.find_all("script")

            for script in scripts:
                if script.string:
                    text = script.string

                    if "jpg" in text or "png" in text:
                        parts = text.split('"')
                        for part in parts:
                            if part.startswith("http") and any(ext in part.lower() for ext in [".jpg", ".jpeg", ".png"]):

                                # kiszűrjük az ikonokat/logókat
                                if not any(x in part.lower() for x in ["logo", "icon", "thumb", "sprite"]):
                                    images.append(part)

        # duplikátum törlés
        images = list(dict.fromkeys(images))

        return images

    except:
        return []


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

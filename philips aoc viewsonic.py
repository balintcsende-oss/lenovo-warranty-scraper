import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import re

st.title("VPN Product Link + Brand-Specific Gallery Images")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

headers = {
    "User-Agent": "Mozilla/5.0"
}

# ----------------------------
# Product link generálás
# ----------------------------
def generate_link(vpn, brand):
    vpn = str(vpn)
    brand = str(brand).strip()

    if brand == "Philips":
        return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"

    elif brand == "AOC":
        return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"

    elif brand == "Viewsonic":
        return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"

    else:
        return ""


# ----------------------------
# ViewSonic galéria
# ----------------------------
def get_viewsonic_gallery(url):
    images = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Elsődleges galéria
        container = soup.select_one("div#overviewGallery")
        if container:
            for img in container.find_all("img"):
                if img.has_attr("srcset"):
                    srcset = img["srcset"].split(",")
                    largest = srcset[-1].strip().split(" ")[0]
                    images.append(largest)

        # Ha csak 1 kép → script fallback
        if len(images) <= 1:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    text = script.string
                    if "jpg" in text or "png" in text:
                        parts = text.split('"')
                        for part in parts:
                            if part.startswith("http") and any(ext in part.lower() for ext in [".jpg", ".jpeg", ".png"]):
                                if not any(x in part.lower() for x in ["logo", "icon", "thumb", "sprite"]):
                                    images.append(part)

        images = list(dict.fromkeys(images))
        return images

    except:
        return []


# ----------------------------
# AOC galéria
# ----------------------------
def get_aoc_gallery(url):
    images = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        container = soup.select_one("div.image-carousel")
        if container:
            for img in container.find_all("img"):
                src = img.get("data-zoom-image") or img.get("src")
                if src and src.startswith("http"):
                    images.append(src)

        images = list(dict.fromkeys(images))
        return images

    except:
        return []


# ----------------------------
# Philips galéria (Scene7)
# ----------------------------
def get_philips_gallery(url):
    images = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text

        # Minden philipsconsumer asset ID keresése
        pattern = r"philipsconsumer/([a-zA-Z0-9]+)"
        matches = re.findall(pattern, html)

        unique_ids = list(dict.fromkeys(matches))

        for asset_id in unique_ids:
            if any(x in asset_id.lower() for x in ["logo", "icon", "banner"]):
                continue

            large_url = (
                f"https://images.philips.com/is/image/philipsconsumer/"
                f"{asset_id}?$pnglarge$&wid=1250"
            )

            images.append(large_url)

        return images

    except:
        return []


# ----------------------------
# FŐ FUTTATÁS
# ----------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
    else:

        df["Product link"] = df.apply(
            lambda r: generate_link(r["VPN"], r["Brand"]),
            axis=1
        )

        st.info("Galéria képek lekérése...")

        all_images = []

        for _, row in df.iterrows():

            brand = str(row["Brand"]).strip()
            url = row["Product link"]

            if brand == "Viewsonic":
                images = get_viewsonic_gallery(url)

            elif brand == "AOC":
                images = get_aoc_gallery(url)

            elif brand == "Philips":
                images = get_philips_gallery(url)

            else:
                images = []

            all_images.append(images)

        # Dinamikus Pick link oszlopok
        max_imgs = max(len(imgs) for imgs in all_images) if all_images else 0

        for i in range(max_imgs):
            df[f"Pick link {i+1}"] = [
                imgs[i] if i < len(imgs) else ""
                for imgs in all_images
            ]

        st.subheader("Eredmény")
        st.dataframe(df)

        # Excel mentés openpyxl-lel
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

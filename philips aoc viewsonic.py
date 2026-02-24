import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("VPN → Product Link + Gallery Images (Philips / ViewSonic / AOC)")

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
        vpn = str(vpn).strip()
        brand = str(brand).strip().lower()

        if brand == "philips":
            return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"
        elif brand == "aoc":
            return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"
        elif brand == "viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
        return ""

    df["Product link"] = df.apply(
        lambda r: generate_link(r["VPN"], r["Brand"]), axis=1
    )

    headers = {"User-Agent": "Mozilla/5.0"}

    # -------------------------------------------------
    # ViewSonic
    # -------------------------------------------------
    def get_viewsonic_gallery(url):
        images = []
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            container = soup.select_one("div#overviewGallery")
            if container:
                for img in container.find_all("img"):
                    if img.has_attr("srcset"):
                        srcset = img["srcset"].split(",")
                        largest = srcset[-1].strip().split(" ")[0]
                        images.append(largest)

            if len(images) <= 1:
                for script in soup.find_all("script"):
                    if not script.string:
                        continue
                    text = script.string
                    if "jpg" in text.lower() or "png" in text.lower():
                        parts = text.split('"')
                        for part in parts:
                            if part.startswith("http") and any(ext in part.lower() for ext in [".jpg",".jpeg",".png"]):
                                if not any(x in part.lower() for x in ["logo","icon","sprite","thumb"]):
                                    images.append(part)

        except:
            return []

        return list(dict.fromkeys(images))

    # -------------------------------------------------
    # Philips
    # -------------------------------------------------
    import re

def get_philips_gallery(url):
    images = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text

        # Minden philipsconsumer asset ID kinyerése
        pattern = r"philipsconsumer/([a-zA-Z0-9]+)"
        matches = re.findall(pattern, html)

        unique_ids = list(dict.fromkeys(matches))

        for asset_id in unique_ids:
            # kizárjuk a logókat és ikonokat
            if any(x in asset_id.lower() for x in ["logo", "icon", "banner"]):
                continue

            large_url = (
                f"https://images.philips.com/is/image/philipsconsumer/"
                f"{asset_id}?$pnglarge$&wid=1250"
            )

            images.append(large_url)

    except:
        return []

    return images

    return images

        return list(dict.fromkeys(images))

    # -------------------------------------------------
    # AOC
    # -------------------------------------------------
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

        except:
            return []

        return list(dict.fromkeys(images))

    # -------------------------------------------------
    # Feldolgozás
    # -------------------------------------------------
    st.info("Galéria képek lekérése...")

    all_images = []

    for _, row in df.iterrows():
        brand = str(row["Brand"]).strip().lower()
        url = row["Product link"]

        if brand == "viewsonic":
            imgs = get_viewsonic_gallery(url)
        elif brand == "philips":
            imgs = get_philips_gallery(url)
        elif brand == "aoc":
            imgs = get_aoc_gallery(url)
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
        file_name="product_gallery_images.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

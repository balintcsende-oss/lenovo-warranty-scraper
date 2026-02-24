import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("Product gallery high‑res image scraper")

uploaded_file = st.file_uploader("Excel feltöltése", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    def generate_link(vpn, brand):
        vpn = str(vpn)
        brand = str(brand).strip()
        if brand == "Philips":
            return f"https://www.philips.hu/c-p/{vpn.replace('/', '_')}/"
        elif brand == "AOC":
            return f"https://www.aoc.com/hu/gaming/monitors/{vpn.lower()}"
        elif brand == "Viewsonic":
            return f"https://www.viewsonic.com/hu/products/lcd/{vpn}"
        return ""

    df["Product link"] = df.apply(lambda r: generate_link(r["VPN"], r["Brand"]), axis=1)

    def get_high_res_images(url):
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            images = set()

            # keresés srcset attribútum alapján (magas felbontás)
            for tag in soup.find_all("img"):
                if tag.has_attr("srcset"):
                    srcset = tag["srcset"]
                    parts = srcset.split(",")
                    for p in parts:
                        p_url = p.strip().split(" ")[0]
                        if p_url.startswith("//"):
                            p_url = "https:" + p_url
                        if p_url.startswith("http"):
                            images.add(p_url)

            # fallback: csak src attribútum
            if not images:
                for tag in soup.find_all("img"):
                    src = tag.get("src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        if src.startswith("http"):
                            images.add(src)

            return list(images)

        except Exception as e:
            return []

    all_images = []
    for link in df["Product link"]:
        imgs = get_high_res_images(link)
        all_images.append(imgs)

    # Oszlopok dinamikus létrehozása
    max_imgs = max(len(imgs) for imgs in all_images)
    for i in range(max_imgs):
        df[f"Pick link {i+1}"] = [
            imgs[i] if i < len(imgs) else ""
            for imgs in all_images
        ]

    st.dataframe(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        "Letöltés Excel",
        data=output,
        file_name="image_links.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

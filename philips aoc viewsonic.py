import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

st.title("VPN Product Link + High-Res Pick Links")

uploaded_file = st.file_uploader("Töltsd fel az Excel fájlt", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Ellenőrizzük a szükséges oszlopokat
    required_columns = ["VPN", "Brand"]
    if not all(col in df.columns for col in required_columns):
        st.error("Az Excel fájlnak tartalmaznia kell a 'VPN' és 'Brand' oszlopokat!")
    else:

        # Product link generáló
        def generate_link(vpn, brand):
            if pd.isna(vpn) or pd.isna(brand):
                return ""
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

        # Product link oszlop
        df["Product link"] = df.apply(lambda r: generate_link(r["VPN"], r["Brand"]), axis=1)

        # Funkció a nagyfelbontású galéria képek kigyűjtésére
        def get_high_res_images(url):
            try:
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, "html.parser")
                images = set()

                # srcset attribútumok keresése (általában nagy felbontású képek)
                for img in soup.find_all("img"):
                    if img.has_attr("srcset"):
                        srcset = img["srcset"]
                        for part in srcset.split(","):
                            src_url = part.strip().split(" ")[0]
                            if src_url.startswith("//"):
                                src_url = "https:" + src_url
                            if src_url.startswith("http"):
                                images.add(src_url)

                # fallback: src attribútumok, ha nincs srcset
                if not images:
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if src:
                            if src.startswith("//"):
                                src = "https:" + src
                            if src.startswith("http"):
                                images.add(src)

                return list(images)
            except Exception as e:
                return []

        st.info("A product link-ek képeinek lekérése eltarthat néhány másodpercig oldalanként...")

        # Minden product link képeinek kigyűjtése
        all_images = []
        for link in df["Product link"]:
            images = get_high_res_images(link)
            all_images.append(images)

        # Pick link oszlopok létrehozása dinamikusan
        max_imgs = max(len(imgs) for imgs in all_images)
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
            file_name="product_links_with_images.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

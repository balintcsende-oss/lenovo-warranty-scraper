import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

BASE = "https://www.kensington.com"

def get_product_data(sku):
    result = {
        "url": None,
        "images": [],
        "features": [],
        "specs": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ---------- QUICK SEARCH ----------
        search_url = f"{BASE}/GlobalSearch/QuickSearch/?query={sku}"
        page.goto(search_url)
        page.wait_for_timeout(3000)  # 3 sec, hogy a JS render befejeződjön

        # megkeressük az első product URL-t
        links = page.query_selector_all("a")
        for a in links:
            href = a.get_attribute("href")
            if href and "/p/" in href:
                result["url"] = BASE + href if href.startswith("/") else href
                break

        if not result["url"]:
            browser.close()
            return result

        # ---------- PRODUCT PAGE ----------
        page.goto(result["url"])
        page.wait_for_timeout(3000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # ---------- IMAGES ----------
        for img in soup.select("[data-zoom-image]"):
            src = img.get("data-zoom-image")
            if src and src not in result["images"]:
                result["images"].append(src)

        # fallback képek
        if not result["images"]:
            for img in soup.select("img"):
                src = img.get("src")
                if src and "kensington" in src and src not in result["images"]:
                    result["images"].append(src)

        # ---------- FEATURES ----------
        for li in soup.select("li"):
            txt = li.get_text(strip=True)
            if len(txt) > 30:
                result["features"].append(txt)

        # ---------- SPECS ----------
        for row in soup.select("table tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                result["specs"][key] = val

        browser.close()

    return result


# ---------- STREAMLIT UI ----------
st.title("Kensington Playwright Scraper")

file = st.file_uploader("Excel feltöltése (SKU oszlop)", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    if "SKU" not in df.columns:
        st.error("Nincs SKU oszlop")
        st.stop()

    results = []
    skus = df["SKU"].dropna().tolist()
    progress = st.progress(0)

    for i, sku in enumerate(skus):
        st.write("Processing:", sku)
        data = get_product_data(str(sku))

        row = {
            "SKU": sku,
            "URL": data["url"],
            "FEATURES": " | ".join(data["features"]),
            "SPECS": str(data["specs"])
        }

        for n, img in enumerate(data["images"]):
            row[f"IMAGE_{n+1}"] = img

        results.append(row)
        progress.progress((i + 1) / len(skus))
        time.sleep(0.5)

    out = pd.DataFrame(results)
    st.dataframe(out)
    out.to_excel("kensington_output.xlsx", index=False)
    st.success("Kész ✔")

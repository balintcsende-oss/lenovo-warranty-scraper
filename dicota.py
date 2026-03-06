import pandas as pd
from playwright.sync_api import sync_playwright

# Excel feltöltése
from google.colab import files
uploaded = files.upload()
filename = list(uploaded.keys())[0]

df = pd.read_excel(filename)

# SKU oszlop keresése
sku_col = None
for col in df.columns:
    if "sku" in col.lower():
        sku_col = col
        break
if sku_col is None:
    raise Exception("Nem található SKU oszlop")

titles = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for sku in df[sku_col]:
        if pd.isna(sku):
            titles.append("")
            continue

        sku = str(sku).strip()
        url = f"https://www.dicota.com/search?type=product&q={sku}"
        page.goto(url)

        # várunk, amíg a DOM betöltődik
        page.wait_for_selector('[li-object="product.title"]', timeout=5000)

        try:
            title_elem = page.query_selector('[li-object="product.title"]')
            title = title_elem.inner_text().strip() if title_elem else ""
            print(sku, "→", title)
        except:
            title = ""
            print(sku, "→ Nincs találat")

        titles.append(title)

    browser.close()

df["product_title"] = titles

output = "dicota_output.xlsx"
df.to_excel(output, index=False)
files.download(output)

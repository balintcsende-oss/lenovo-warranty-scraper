import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd

async def scrape_emag():
    url = "https://www.emag.hu/brands/brand/doogee?ref=bc"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # fontos!
        context = await browser.new_context()

        page = await context.new_page()
        await page.goto(url, timeout=60000)

        # Várunk, hogy a JS betöltse a termékeket
        await page.wait_for_selector(".card-item", timeout=60000)

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="card-item")

        products = []
        for card in cards:
            name = card.get("data-product-name")
            price = card.get("data-product-price")
            link_tag = card.find("a", class_="card-v2-title")
            link = "https://www.emag.hu" + link_tag["href"] if link_tag else None

            if name and price:
                products.append({
                    "Terméknév": name,
                    "Ár (Ft)": int(price),
                    "Link": link
                })

        return pd.DataFrame(products)

df = asyncio.run(scrape_emag())
print(df)

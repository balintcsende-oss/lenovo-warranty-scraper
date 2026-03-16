import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import json

st.title("Kensington QuickSearch Cloudflare bypass DEBUG")

sku = st.text_input("SKU", "K50416EU")

if st.button("Lekérés"):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)   # first run: False!
        page = browser.new_page()

        url = f"https://www.kensington.com/GlobalSearch/QuickSearch/?query={sku}"

        st.write("Opening:", url)

        page.goto(url, timeout=60000)

        # várunk hogy Cloudflare + JS betöltődjön
        page.wait_for_timeout(8000)

        content = page.inner_text("body")

        st.subheader("RAW RESPONSE")
        st.text(content[:2000])

        # próbáljuk JSON parse
        try:
            data = json.loads(content)

            st.success("JSON parsed")

            if isinstance(data, dict):

                for k, v in data.items():

                    if isinstance(v, list):
                        df = pd.DataFrame(v)
                        st.subheader(f"LIST: {k}")
                        st.dataframe(df)

                    else:
                        st.write(k, v)

        except:
            st.error("Nem tiszta JSON → de látod a választ")

        browser.close()

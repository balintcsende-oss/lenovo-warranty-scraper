import streamlit as st
import pandas as pd
import requests
import json

st.title("Kensington QuickSearch DEBUG")

sku = st.text_input("SKU", "K50416EU")

if st.button("Lekérés"):

    url = "https://www.kensington.com/GlobalSearch/QuickSearch/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        url,
        params={"query": sku},
        headers=headers,
        timeout=30
    )

    st.write("STATUS:", r.status_code)
    st.write("CONTENT TYPE:", r.headers.get("content-type"))

    # próbáljuk JSON-ként
    try:
        data = r.json()

        st.success("JSON válasz")

        st.json(data)

        # ha van Results
        if isinstance(data, dict):
            for k, v in data.items():

                if isinstance(v, list):
                    df = pd.DataFrame(v)
                    st.subheader(f"Lista: {k}")
                    st.dataframe(df)

                else:
                    st.write(k, v)

    except:
        st.error("Nem JSON válasz")

        st.text(r.text[:5000])

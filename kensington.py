import requests

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.kensington.com/",
    "X-Requested-With": "XMLHttpRequest"
}

# FONTOS: először home page → cookie
session.get("https://www.kensington.com/", headers=headers)

def get_url(sku):

    r = session.get(
        "https://www.kensington.com/GlobalSearch/QuickSearch/",
        params={"query": sku},
        headers=headers,
        timeout=30
    )

    print(r.text[:500])   # debug

    data = r.json()

    if data.get("Results"):
        return "https://www.kensington.com" + data["Results"][0]["Url"]

    return None


print(get_url("K50416EU"))

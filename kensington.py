import requests

def get_product_url(sku):

    url = "https://www.kensington.com/GlobalSearch/QuickSearch/"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.kensington.com/",
    }

    cookies = {
        "site": "en-gb"
    }

    r = requests.get(
        url,
        params={"query": sku},
        headers=headers,
        cookies=cookies,
        timeout=30
    )

    data = r.json()

    if data["Results"]:
        rel = data["Results"][0]["Url"]
        return "https://www.kensington.com" + rel

    return None

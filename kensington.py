import requests

sku = "K50416EU"

url = "https://www.kensington.com/api/site-search"

r = requests.get(
    url,
    params={"search": sku},
    headers={"User-Agent": "Mozilla/5.0"}
)

print(r.status_code)
print(r.text[:1000])

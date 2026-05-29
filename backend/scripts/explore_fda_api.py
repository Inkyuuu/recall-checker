import httpx
import json

url = "https://api.fda.gov/food/enforcement.json"

params = {
    "search": 'product_description:"spinach"',
    "limit": 5
}

response = httpx.get(url, params=params)
response.raise_for_status()

data = response.json()
print(json.dumps(data["results"][0], indent=2))
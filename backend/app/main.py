# app/main.py
from fastapi import FastAPI, Query
import httpx

app = FastAPI(title="Recall Checker API")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/recalls/search")
def search_recalls(q: str = Query(...)):
    url = "https://api.fda.gov/food/enforcement.json"
    params = {
        "search": f'product_description:"{q}"',
        "limit": 10
    }

    response = httpx.get(url, params=params)
    response.raise_for_status()

    return response.json()
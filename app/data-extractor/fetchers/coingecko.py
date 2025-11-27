import requests
from datetime import datetime, timezone
from typing import List, Dict
from config.settings import COINS, CURRENCY

def fetch_prices() -> List[Dict]:
    """Fetch the latest crypto prices from the CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(COINS), "vs_currencies": CURRENCY}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    timestamp = datetime.now(timezone.utc).isoformat()

    results = [
        {"coin": coin, "price_usd": info[CURRENCY], "timestamp": timestamp}
        for coin, info in data.items()
    ]
    return results

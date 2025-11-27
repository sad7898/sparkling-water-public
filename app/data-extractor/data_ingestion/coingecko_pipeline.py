from datetime import datetime, timezone
import requests
import json
from save_to_s3 import save_to_s3  # import your friend's function

COINS = ["bitcoin", "ethereum", "solana", "dogecoin", "cardano"]
CURRENCY = "usd"

def fetch_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(COINS), "vs_currencies": CURRENCY}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    timestamp = datetime.now(timezone.utc).isoformat()

    results = []
    for coin, info in data.items():
        results.append({
            "coin": coin,
            "price_usd": info[CURRENCY],
            "timestamp": timestamp
        })
    return results

def main():
    data = fetch_prices()
    print(json.dumps(data, indent=2))

    result = save_to_s3(
        data=data,
        source_name="coingecko",
        prefix="raw/crypto",
        compress=True
    )
    print(f"✅ Uploaded to s3://{result['bucket']}/{result['key']} ({result['size_bytes']} bytes)")

if __name__ == "__main__":
    main()

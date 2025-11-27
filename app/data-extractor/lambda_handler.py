from fetchers.coingecko import fetch_prices
from fetchers.reddit_fetcher import fetch_reddit_posts
from utils.s3_utils import save_to_s3

def handle(event, context):
    data = fetch_prices()
    for entry in data:
        coin_name = entry["coin"]
        save_to_s3(entry, source_name=f"coingecko/{coin_name}")

    reddit_posts = fetch_reddit_posts()
    for post in reddit_posts:
        save_to_s3(post, source_name=f"reddit/cryptocurrency")

    return {
        "statusCode": 200,
        "body": "Data extracted and saved successfully!"
    }

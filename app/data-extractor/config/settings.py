import os

COINS = ["bitcoin", "ethereum", "dogecoin"]
CURRENCY = "usd"

S3_BUCKET = os.getenv("DATA_BUCKET_NAME", "sparkling-water-dev-data-bucket")
PREFIX = "raw"
COMPRESS = True

# Reddit settings
SUBREDDITS = ["Bitcoin", "ethereum", "dogecoin"]
POST_LIMIT = 20
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "sparkling-water-bot")
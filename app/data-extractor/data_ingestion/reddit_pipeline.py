from datetime import datetime, timezone
import json
from fetchers.reddit_fetcher import fetch_reddit_posts
from utils.s3_utils import save_to_s3

def main():
    # Fetch Reddit posts
    posts = fetch_reddit_posts()
    print(f"Fetched {len(posts)} posts.")

    # Save each post individually to S3
    for post in posts:
        result = save_to_s3(
            data=post,
            source_name=f"reddit/{post['subreddit'].lower()}",
            compress=True
        )
        print(f"✅ Uploaded to s3://{result['bucket']}/{result['key']} ({result['size_bytes']} bytes)")

if __name__ == "__main__":
    main()

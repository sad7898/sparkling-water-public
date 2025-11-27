import os
from datetime import datetime, timezone
from typing import List, Dict
import praw
from config.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, SUBREDDITS, POST_LIMIT

def fetch_reddit_posts() -> List[Dict]:
    """
    Fetch the latest posts from the configured subreddits using Reddit API.

    Returns:
        List[Dict]: Each dict contains post id, title, text, subreddit, timestamp, upvotes, and number of comments.
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

    results: List[Dict] = []

    for subreddit_name in SUBREDDITS:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.new(limit=POST_LIMIT):
            results.append({
                "id": post.id,
                "title": post.title,
                "text": post.selftext,
                "subreddit": subreddit_name,
                "timestamp": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                "upvotes": post.score,
                "num_comments": post.num_comments
            })

    return results

if __name__ == "__main__":
    # Quick local test
    posts = fetch_reddit_posts()
    for p in posts[:5]:  # print first 5 posts
        print(p)

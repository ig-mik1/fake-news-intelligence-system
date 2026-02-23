raise Exception("Reddit API not configured yet")

import praw
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="fake_news_detector"
)

def fetch_reddit():
    posts = []

    for submission in reddit.subreddit("news").hot(limit=50):
        posts.append({
            "title": submission.title,
            "content": submission.selftext,
            "source": "reddit",
            "platform": "reddit"
        })

    return pd.DataFrame(posts)
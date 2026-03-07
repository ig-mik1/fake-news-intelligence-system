import requests

def fetch_reddit_evidence(query, limit=10):
    # PullPush doesn't need a key. It's built for researchers.
    url = f"https://api.pullpush.io/reddit/search/submission/?q={query}&size={limit}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        results = []
        for post in data.get('data', []):
            results.append({
                "title": post.get('title'),
                "url": f"https://reddit.com{post.get('permalink')}",
                "source": f"reddit/r/{post.get('subreddit')}",
                "text": post.get('selftext', '')
            })
        return results
    except Exception as e:
        print(f"PullPush Error: {e}")
        return []
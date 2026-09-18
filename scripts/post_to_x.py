#!/usr/bin/env python3
"""
Posts queued items to X (Twitter), spaced out by generate_post.py's schedule.
Run frequently (e.g. hourly) by .github/workflows/post-to-x.yml. Only posts
items whose scheduled time has passed and that aren't already marked posted.
Does not call the Anthropic API - just reads data/x_queue.json.
"""

import json
import os
import sys
from datetime import datetime, timezone

from requests_oauthlib import OAuth1Session

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(REPO_ROOT, "data", "x_queue.json")

X_TWEET_URL = "https://api.twitter.com/2/tweets"
MAX_TWEET_LEN = 280
LINK_RESERVED_LEN = 26  # X shortens any link to 23 chars via t.co + buffer


def build_tweet_text(paragraph, hashtags, url):
    tags = " ".join("#" + h for h in hashtags)
    # Reserve room for a newline + the link (and hashtags if they fit)
    suffix = f"\n{url}"
    budget = MAX_TWEET_LEN - len(suffix) - 1  # -1 safety margin

    tags_suffix = f" {tags}" if tags else ""
    if len(paragraph) + len(tags_suffix) <= budget:
        text = paragraph + tags_suffix
    else:
        # Truncate paragraph to fit, cut at last whole word, add ellipsis
        trim_to = budget - len(tags_suffix) - 1  # -1 for the ellipsis char
        trimmed = paragraph[:trim_to].rsplit(" ", 1)[0]
        text = trimmed + "…" + tags_suffix

    return text + suffix


def post_tweet(text):
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_token_secret = os.environ["X_ACCESS_TOKEN_SECRET"]

    oauth = OAuth1Session(
        api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )
    resp = oauth.post(X_TWEET_URL, json={"text": text})
    if resp.status_code not in (200, 201):
        print(f"ERROR posting to X: {resp.status_code} {resp.text}", file=sys.stderr)
        return False
    return True


def main():
    if not os.path.exists(QUEUE_PATH):
        print("No queue file found - nothing to post.")
        return

    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    now = datetime.now(timezone.utc)
    posted_any = False

    for item in queue:
        if item["posted"]:
            continue
        post_at = datetime.fromisoformat(item["post_at"])
        if post_at > now:
            continue  # not due yet

        text = build_tweet_text(item["paragraph"], item.get("hashtags", []), item["url"])
        print(f"Posting item {item['id']} ({len(text)} chars):\n{text}\n")

        success = post_tweet(text)
        item["posted"] = success
        if success:
            posted_any = True
        else:
            print(f"Failed to post {item['id']}, will retry next run.", file=sys.stderr)

    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
        f.write("\n")

    if not posted_any:
        print("Nothing due to post this run.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Daily oil/refining/products news post generator.

Run by .github/workflows/daily-post.yml on a schedule. Calls the Claude API
with web search enabled, drafts up to 3 post ideas from the last 3 days of
industry news, avoids repeating recent themes (data/post-log.json), writes
a new Jekyll post into _posts/, and updates the log.

Requires env var: ANTHROPIC_API_KEY (set as a GitHub repo secret).
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(REPO_ROOT, "data", "post-log.json")
POSTS_DIR = os.path.join(REPO_ROOT, "_posts")

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"  # update if your account uses a different model string
RECENT_LOOKBACK = 7  # how many past days of log entries to check for staleness


def load_log():
    if not os.path.exists(LOG_PATH):
        return {"posts": []}
    with open(LOG_PATH, "r") as f:
        return json.load(f)


def save_log(log):
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
        f.write("\n")


def recent_themes(log, n=RECENT_LOOKBACK):
    recent = log["posts"][-n:] if log["posts"] else []
    lines = []
    for entry in recent:
        for item in entry.get("items", []):
            tags = ", ".join("#" + h for h in item.get("hashtags", []))
            lines.append(f"- {entry['date']}: {item['theme']} — {item['headline']} ({tags})")
    return "\n".join(lines) if lines else "(no prior entries)"


def call_claude(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    body = {
        "model": MODEL,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Web search can trigger multiple turns; if the API returns a stop reason
    # requiring a follow-up (tool use still pending), loop until we get text.
    # For simplicity, this assumes the server-side web_search tool resolves
    # within a single response (current Anthropic API behavior for this tool).
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    if not text_blocks:
        print("ERROR: no text content in API response:", json.dumps(data)[:2000], file=sys.stderr)
        sys.exit(1)
    return "\n".join(text_blocks)


def extract_json(raw: str) -> dict:
    # Strip markdown code fences if present, then find the first {...} block.
    cleaned = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        print("ERROR: could not find JSON in model output:\n", raw[:2000], file=sys.stderr)
        sys.exit(1)
    return json.loads(match.group(0))


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60]


def build_prompt(avoid: str) -> str:
    return f"""You are drafting content for a crude oil / refining / oil products
industry blog. Use web search to research the last 3 days of news in this
space: crude prices, OPEC+ decisions, refinery outages/maintenance,
supply-demand shifts, geopolitical events, regulatory changes, and major
company moves.

Prioritize timely, specific angles with a clear point of view. Skip generic
recaps. Practical tone, no hype. Lead each post with a forward-looking or
consequence view where possible.

Do NOT repeat these recent themes unless there is a genuinely new
development (in which case frame it explicitly as an update and say what
changed):
{avoid}

Return up to 3 post ideas as ONLY a JSON object, no preamble, no markdown
fences, in exactly this shape:

{{
  "items": [
    {{
      "headline": "string",
      "theme": "short-kebab-case-tag",
      "hashtags": ["NoHashSymbol", "AnotherTag"],
      "paragraph": "up to 100 words, forward/consequence-first"
    }}
  ]
}}
"""


def build_post_markdown(items: list, post_date: date) -> tuple[str, str]:
    headline = items[0]["headline"] if items else "Daily Oil & Refining Notes"
    slug = slugify(headline)
    filename = f"{post_date.isoformat()}-{slug}.md"

    all_tags = sorted({h for item in items for h in item.get("hashtags", [])})
    front_matter = (
        "---\n"
        "layout: post\n"
        f'title: "{headline.replace(chr(34), chr(39))}"\n'
        f"date: {post_date.isoformat()} 12:00:00 +0000\n"
        f"tags: [{', '.join(all_tags)}]\n"
        "---\n\n"
    )

    body_parts = []
    for item in items:
        tag_line = " ".join(
            f'<a href="/daily/search/?tag={h}">#{h}</a>' for h in item.get("hashtags", [])
        )
        
        body_parts.append(
            f"## {item['headline']}\n\n{item['paragraph']}\n\n{tag_line}\n"
        )

    return filename, front_matter + "\n".join(body_parts)


def main():
    log = load_log()
    avoid = recent_themes(log)
    prompt = build_prompt(avoid)

    raw = call_claude(prompt)
    parsed = extract_json(raw)
    items = parsed.get("items", [])[:3]

    if not items:
        print("No items returned; skipping post for today.", file=sys.stderr)
        return

    today = datetime.now(timezone.utc).date()
    filename, content = build_post_markdown(items, today)

    os.makedirs(POSTS_DIR, exist_ok=True)
    with open(os.path.join(POSTS_DIR, filename), "w") as f:
        f.write(content)

    log["posts"].append({
        "date": today.isoformat(),
        "items": [
            {"headline": i["headline"], "theme": i["theme"], "hashtags": i["hashtags"]}
            for i in items
        ],
    })
    save_log(log)

    print(f"Wrote {filename} with {len(items)} item(s) and updated log.")


if __name__ == "__main__":
    main()

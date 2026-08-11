# Oil/Refining Daily Blog — Setup Guide

This repo is a Jekyll site (hosted free on GitHub Pages) with a GitHub
Action that runs daily, researches the last 3 days of crude/refining/
products news via Claude, drafts up to 3 post ideas, and publishes them
straight to the live site.

## 1. Create the GitHub repo
- Create a **new, empty** GitHub repository (public — GitHub Pages free
  tier requires a public repo unless you're on GitHub Pro/Enterprise).
- Upload/push everything in this folder to that repo's `main` branch.

## 2. Get an Anthropic API key
- Go to console.anthropic.com, create an API key.
- This is billed separately from any Claude.ai subscription — usage is
  pay-as-you-go. A daily run like this (research + drafting ~3 short
  items) should cost a small fraction of a dollar per day, but check
  current pricing on the Anthropic site before relying on that estimate.

## 3. Add the key as a repo secret
- In your GitHub repo: **Settings → Secrets and variables → Actions →
  New repository secret**.
- Name: `ANTHROPIC_API_KEY`
- Value: paste your key.
(I can't do this step for you — entering API keys is something only you
should do, directly in GitHub's own settings page.)

## 4. Turn on GitHub Pages
- **Settings → Pages → Build and deployment → Source**: choose
  "Deploy from a branch," branch `main`, folder `/ (root)`.
- GitHub will build the Jekyll site automatically on every push.

## 5. Point your domain at it
- In your domain registrar's DNS settings, add:
  - A records for the apex domain pointing to GitHub's Pages IPs
    (185.199.108.153, .109.153, .110.153, .111.153), **or**
  - A CNAME record for `www` pointing to `yourusername.github.io`
- In the repo, add a file named `CNAME` (no extension) at the root
  containing just your domain, e.g. `example.com`. GitHub Pages reads
  this automatically. It can take up to 24 hours to propagate.

## 6. Test it
- Go to the **Actions** tab in your repo → "Daily oil/refining post" →
  **Run workflow** to trigger it manually the first time, rather than
  waiting for the schedule.
- Check that a new file appeared in `_posts/` and that `data/post-log.json`
  got a new entry.

## Adjusting things later
- **Posting time**: edit the `cron` line in
  `.github/workflows/daily-post.yml` (times are UTC).
- **Model**: edit `MODEL` in `scripts/generate_post.py` if you want to
  point at a different Claude model.
- **Site title/branding**: edit `_config.yml`.
- **Design**: this uses the `minima` theme (built into GitHub Pages) as a
  clean starting point. Swap `theme:` in `_config.yml` for any other
  GitHub Pages-supported theme, or replace with a custom one later.

## What this does NOT do
- It does not review content before publishing — you chose auto-publish,
  so whatever the model drafts goes live daily without a human check. If
  you want a review step later, the workflow can be changed to open a
  pull request instead of pushing directly to `main` — just ask.
- It relies on the Claude API's server-side web search tool, which pulls
  live results at run time; it isn't using this chat's search results.

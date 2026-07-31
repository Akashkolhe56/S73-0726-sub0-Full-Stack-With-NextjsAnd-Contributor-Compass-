"""
fetch_data.py
Pulls pull-requests, issues, and derives contributor first-seen dates from
the GitHub REST API for one or more repos.

USAGE:
    export GITHUB_TOKEN=ghp_xxx        # optional but strongly recommended
    python scripts/fetch_data.py --repos owner/repo1 owner/repo2

Without a token you get 60 requests/hour (shared per IP) which is usually
not enough for repos with more than a couple hundred PRs/issues. With a
token you get 5,000/hour.

Output: writes raw JSON page dumps to data/raw/<repo>/pulls_pageN.json etc.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

API = "https://api.github.com"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def get_headers():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def paginated_get(url, params=None, max_pages=50):
    """Yield each page's JSON list, handling GitHub pagination + rate limits."""
    params = dict(params or {})
    params.setdefault("per_page", 100)
    page = 1
    headers = get_headers()
    while page <= max_pages:
        params["page"] = page
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 1)
            print(f"Rate limited. Sleeping {wait:.0f}s...", file=sys.stderr)
            time.sleep(wait + 1)
            continue
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        yield data
        if len(data) < params["per_page"]:
            break
        page += 1


def fetch_repo(repo: str):
    """repo is 'owner/name'. Saves raw pulls, issues, and commits to disk."""
    safe_name = repo.replace("/", "__")
    out_dir = RAW_DIR / safe_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pull requests (state=all covers open/closed/merged)
    for i, page in enumerate(
        paginated_get(f"{API}/repos/{repo}/pulls", {"state": "all", "sort": "created", "direction": "asc"})
    ):
        (out_dir / f"pulls_page{i}.json").write_text(json.dumps(page, indent=2))
        print(f"[{repo}] pulls page {i}: {len(page)} records")

    # Issues (note: GitHub's issues endpoint includes PRs too; we filter later)
    for i, page in enumerate(
        paginated_get(f"{API}/repos/{repo}/issues", {"state": "all", "sort": "created", "direction": "asc"})
    ):
        (out_dir / f"issues_page{i}.json").write_text(json.dumps(page, indent=2))
        print(f"[{repo}] issues page {i}: {len(page)} records")

    # Contributors (aggregate stats, useful for cross-checking)
    for i, page in enumerate(paginated_get(f"{API}/repos/{repo}/contributors")):
        (out_dir / f"contributors_page{i}.json").write_text(json.dumps(page, indent=2))
        print(f"[{repo}] contributors page {i}: {len(page)} records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", nargs="+", required=True, help="e.g. facebook/react vuejs/vue")
    args = parser.parse_args()

    for repo in args.repos:
        print(f"=== Fetching {repo} ===")
        fetch_repo(repo)

    print("Done. Raw JSON saved under data/raw/<owner>__<repo>/")


if __name__ == "__main__":
    main()

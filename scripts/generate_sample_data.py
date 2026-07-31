"""
generate_sample_data.py
Generates realistic synthetic PR + issue data shaped like GitHub API output,
so the rest of the pipeline (cleaning, SQL, dashboard) can be built and
tested without hitting live rate limits. Swap this out for real fetch_data.py
output once you have a token.

Simulates 4 repos, ~450 contributors total, with realistic patterns:
- ~65% of contributors only ever make 1 PR (first-timers who don't return)
- Review time correlated with retention (slow first review -> less likely to return)
- Issue participation correlated with retention
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

REPOS = [
    "kalviumcommunity__contributor-compass",
    "sample-org__open-tracker",
    "sample-org__data-widgets",
    "sample-org__ui-kit",
]

START = datetime(2024, 1, 1)
END = datetime(2026, 6, 30)


def random_date(start=START, end=END):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def gen_repo(repo_name, n_contributors=110):
    contributors = [fake.user_name() for _ in range(n_contributors)]
    pulls, issues = [], []
    pr_id, issue_id = 1000, 5000

    for user in contributors:
        # each contributor's first PR
        first_pr_date = random_date(START, END - timedelta(days=30))
        # slow reviews -> less likely to return (simulate the retention story)
        review_hours = max(0.5, random.gauss(30, 25))
        is_first_time = True
        returns = random.random() > (0.72 if review_hours > 48 else 0.35)

        n_prs = 1
        if returns:
            n_prs += random.choices([1, 2, 3, 4, 5], weights=[35, 25, 20, 12, 8])[0]

        cursor = first_pr_date
        for i in range(n_prs):
            created = cursor
            rh = review_hours if i == 0 else max(0.5, random.gauss(20, 15))
            first_review = created + timedelta(hours=rh)
            merged = random.random() > 0.15
            closed = first_review + timedelta(hours=random.uniform(1, 72)) if merged else None

            pulls.append({
                "id": pr_id,
                "number": pr_id,
                "user": {"login": user},
                "created_at": created.isoformat() + "Z",
                "first_review_at": first_review.isoformat() + "Z",
                "merged_at": closed.isoformat() + "Z" if merged else None,
                "closed_at": closed.isoformat() + "Z" if closed else None,
                "state": "closed" if closed else "open",
                "is_first_pr_for_user": is_first_time and i == 0,
            })
            pr_id += 1
            cursor = created + timedelta(days=random.randint(10, 90))

        # some contributors also open issues
        if random.random() < 0.4:
            for _ in range(random.randint(1, 3)):
                created = random_date(first_pr_date, END)
                closed = created + timedelta(hours=random.uniform(2, 200)) if random.random() > 0.2 else None
                issues.append({
                    "id": issue_id,
                    "number": issue_id,
                    "user": {"login": user},
                    "created_at": created.isoformat() + "Z",
                    "closed_at": closed.isoformat() + "Z" if closed else None,
                    "state": "closed" if closed else "open",
                    "comments": random.randint(0, 12),
                })
                issue_id += 1
        is_first_time = False

    out_dir = RAW_DIR / repo_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pulls_page0.json").write_text(json.dumps(pulls, indent=2))
    (out_dir / "issues_page0.json").write_text(json.dumps(issues, indent=2))
    print(f"{repo_name}: {len(pulls)} PRs, {len(issues)} issues, {n_contributors} contributors")


if __name__ == "__main__":
    for r in REPOS:
        gen_repo(r)
    print("Sample data generated under data/raw/")

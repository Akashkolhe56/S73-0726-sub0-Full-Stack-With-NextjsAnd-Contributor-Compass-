"""
clean_data.py
Reads raw JSON (from fetch_data.py or generate_sample_data.py), validates,
cleans, and engineers contributor-level + PR-level features. Writes:
  data/processed/pull_requests.csv
  data/processed/issues.csv
  data/processed/contributors.csv   <- one row per (repo, user), the core analysis table
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_json_pages(repo_dir: Path, prefix: str) -> list:
    records = []
    for f in sorted(repo_dir.glob(f"{prefix}_page*.json")):
        records.extend(json.loads(f.read_text()))
    return records


def load_all():
    pr_rows, issue_rows = [], []
    for repo_dir in sorted(RAW_DIR.iterdir()):
        if not repo_dir.is_dir():
            continue
        repo = repo_dir.name
        for p in load_json_pages(repo_dir, "pulls"):
            p["repo"] = repo
            pr_rows.append(p)
        for i in load_json_pages(repo_dir, "issues"):
            # GitHub's /issues endpoint also returns PRs; skip those (they'd have 'pull_request' key)
            if "pull_request" in i:
                continue
            i["repo"] = repo
            issue_rows.append(i)
    return pd.DataFrame(pr_rows), pd.DataFrame(issue_rows)


def clean_pulls(pulls: pd.DataFrame) -> pd.DataFrame:
    df = pulls.copy()
    df["user"] = df["user"].apply(lambda u: u.get("login") if isinstance(u, dict) else u)
    df = df.dropna(subset=["user", "created_at"])

    for col in ["created_at", "first_review_at", "merged_at", "closed_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    df = df.drop_duplicates(subset=["repo", "number"])

    # review time in hours (NaN if never reviewed)
    if "first_review_at" in df.columns:
        df["review_time_hours"] = (df["first_review_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["is_merged"] = df["merged_at"].notna() if "merged_at" in df.columns else df["state"] == "closed"

    # cap absurd review times (data errors) rather than silently dropping rows
    if "review_time_hours" in df.columns:
        df["review_time_hours"] = df["review_time_hours"].clip(lower=0, upper=24 * 60)

    return df.reset_index(drop=True)


def clean_issues(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return issues
    df = issues.copy()
    df["user"] = df["user"].apply(lambda u: u.get("login") if isinstance(u, dict) else u)
    df = df.dropna(subset=["user", "created_at"]).drop_duplicates(subset=["repo", "number"])
    for col in ["created_at", "closed_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    df["comments"] = pd.to_numeric(df.get("comments", 0), errors="coerce").fillna(0).astype(int)
    return df.reset_index(drop=True)


def build_contributor_table(pulls: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """One row per (repo, user): the core table the dashboard and KPIs run on."""
    pulls = pulls.sort_values("created_at")
    grp = pulls.groupby(["repo", "user"])

    contrib = grp.agg(
        first_pr_at=("created_at", "min"),
        last_pr_at=("created_at", "max"),
        total_prs=("number", "count"),
        merged_prs=("is_merged", "sum"),
        avg_review_time_hours=("review_time_hours", "mean"),
        first_review_time_hours=("review_time_hours", "first"),
    ).reset_index()

    contrib["is_returning_contributor"] = contrib["total_prs"] > 1

    # issue participation per contributor
    if not issues.empty:
        issue_counts = issues.groupby(["repo", "user"]).size().rename("issue_count").reset_index()
        contrib = contrib.merge(issue_counts, on=["repo", "user"], how="left")
    else:
        contrib["issue_count"] = 0
    contrib["issue_count"] = contrib["issue_count"].fillna(0).astype(int)
    contrib["participated_in_issues"] = contrib["issue_count"] > 0

    # onboarding quality bucket, driven by first review speed
    bins = [-0.01, 12, 48, 1e9]
    labels = ["fast (<12h)", "moderate (12-48h)", "slow (>48h)"]
    contrib["onboarding_speed_bucket"] = pd.cut(
        contrib["first_review_time_hours"], bins=bins, labels=labels
    )

    contrib["days_active"] = (contrib["last_pr_at"] - contrib["first_pr_at"]).dt.days

    return contrib


def main():
    pulls_raw, issues_raw = load_all()
    pulls = clean_pulls(pulls_raw)
    issues = clean_issues(issues_raw)
    contrib = build_contributor_table(pulls, issues)

    pulls.to_csv(PROCESSED_DIR / "pull_requests.csv", index=False)
    issues.to_csv(PROCESSED_DIR / "issues.csv", index=False)
    contrib.to_csv(PROCESSED_DIR / "contributors.csv", index=False)

    print(f"pull_requests.csv: {len(pulls)} rows")
    print(f"issues.csv: {len(issues)} rows")
    print(f"contributors.csv: {len(contrib)} rows")
    print(f"Overall retention rate: {contrib['is_returning_contributor'].mean():.1%}")


if __name__ == "__main__":
    main()

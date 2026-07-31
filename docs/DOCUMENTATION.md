# Contributor Onboarding Analytics Dashboard — Documentation

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Getting data

**Option A — real GitHub data (recommended for the final submission):**

```bash
export GITHUB_TOKEN=ghp_your_token_here     # avoids the 60 req/hr limit
python scripts/fetch_data.py --repos owner/repo1 owner/repo2 owner/repo3
```

**Option B — synthetic sample data (for local dev / demoing without a token):**

```bash
python scripts/generate_sample_data.py
```

Both write raw JSON to `data/raw/<owner>__<repo>/`.

## Pipeline

```bash
python scripts/clean_data.py     # -> data/processed/{pull_requests,issues,contributors}.csv
python sql/load_db.py            # -> data/contributor_compass.db (SQLite)
```

`sql/kpi_queries.sql` contains the reusable views (`v_repo_kpis`,
`v_onboarding_speed_retention`, `v_issue_participation_retention`) and the
queries answering each core business question. Run them with:

```bash
sqlite3 data/contributor_compass.db < sql/kpi_queries.sql
```

## Dashboard

```bash
streamlit run dashboard/app.py
```

Features: repo + date-range filters, KPI cards, retention-by-repo chart,
onboarding-speed-vs-retention chart, issue-participation-vs-retention chart,
monthly new-contributor trend, and a risk-alert panel that flags any repo
below a 45% retention threshold.

## Contributor table schema (`data/processed/contributors.csv`)

| Column | Meaning |
|---|---|
| repo, user | identity |
| first_pr_at, last_pr_at | first/last PR timestamps |
| total_prs, merged_prs | PR counts |
| avg_review_time_hours, first_review_time_hours | review speed |
| is_returning_contributor | `total_prs > 1` — the core retention label |
| issue_count, participated_in_issues | issue engagement |
| onboarding_speed_bucket | fast/moderate/slow first review |
| days_active | span between first and last PR |

## Known limitations

- "Returning contributor" is defined as `total_prs > 1` in the observed
  window — a contributor whose second PR falls after the data cutoff will
  be misclassified as first-time-only.
- The synthetic dataset simulates plausible patterns for development; it is
  not real data and should not be used for the final submitted analysis.
- Unauthenticated GitHub API calls are capped at 60/hour per IP; use a
  personal access token for anything beyond a couple of small repos.
- GitHub's `/issues` endpoint also returns PRs; `clean_data.py` filters these
  out via the `pull_request` key, so issue counts reflect true issues only.

# Contributor Onboarding Analytics Dashboard

A data product built as part of **Kalvium Simulated Work – Sprint 1**.

## Team Members

| Name | Role |
|------|------|
| Ayush S | Project Admin — data pipeline, SQL, automation |
| Akash R | Documentation & Presentation — dashboard, docs, storytelling |

## Problem Statement

Open-source maintainers have contributor activity, PR review timelines, and
issue participation records, but no workflow reveals which onboarding
experiences discourage first-time contributors from returning.

## Business Objective

Analyze contributor activity data to identify what makes first-time
contributors return vs. churn, and surface where onboarding can improve
retention.

## Quick start

```bash
pip install -r requirements.txt
python scripts/generate_sample_data.py   # or scripts/fetch_data.py for real data
python scripts/clean_data.py
python sql/load_db.py
streamlit run dashboard/app.py
```

Full docs: [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md)

## Tech Stack

Python, Pandas, SQL (SQLite), Streamlit, Plotly, Git & GitHub, GitHub Actions.

## Repository Structure

```
project/
├── data/
│   ├── raw/          (gitignored — generated locally)
│   └── processed/    contributors.csv, pull_requests.csv, issues.csv
├── scripts/          fetch_data.py, generate_sample_data.py, clean_data.py
├── sql/               load_db.py, kpi_queries.sql
├── dashboard/         app.py (Streamlit)
├── docs/              DOCUMENTATION.md
├── .github/workflows/ validate.yml
├── requirements.txt
└── .gitignore
```

pr 1
pr 2

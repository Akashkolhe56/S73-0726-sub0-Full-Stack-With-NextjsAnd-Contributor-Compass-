"""
Contributor Onboarding Analytics Dashboard
Run with: streamlit run dashboard/app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

st.set_page_config(page_title="Contributor Onboarding Analytics", layout="wide")

PRIMARY = "#2E5EAA"
ACCENT = "#E07A3F"
GOOD = "#2E9E6B"
BAD = "#C94F4F"


@st.cache_data
def load_data():
    contrib = pd.read_csv(DATA_DIR / "contributors.csv", parse_dates=["first_pr_at", "last_pr_at"])
    pulls = pd.read_csv(DATA_DIR / "pull_requests.csv", parse_dates=["created_at"])
    issues = pd.read_csv(DATA_DIR / "issues.csv", parse_dates=["created_at"]) if (DATA_DIR / "issues.csv").exists() else pd.DataFrame()
    return contrib, pulls, issues


contrib, pulls, issues = load_data()

if contrib.empty:
    st.warning("No processed data found. Run `python scripts/clean_data.py` first.")
    st.stop()

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
repos = sorted(contrib["repo"].unique())
selected_repos = st.sidebar.multiselect("Repository", repos, default=repos)

date_min = contrib["first_pr_at"].min().date()
date_max = contrib["first_pr_at"].max().date()
date_range = st.sidebar.date_input("First-contribution date range", (date_min, date_max))

if st.sidebar.button("Reset filters"):
    st.rerun()

mask = contrib["repo"].isin(selected_repos)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0], tz="UTC")
    end = pd.Timestamp(date_range[1], tz="UTC")
    mask &= contrib["first_pr_at"].between(start, end)

filtered = contrib[mask]

st.title("Contributor Onboarding Analytics Dashboard")
st.caption("Where first-time contributors drop off, and what onboarding conditions predict retention.")

if filtered.empty:
    st.info("No contributors match the current filters.")
    st.stop()

# ---------------- KPI cards ----------------
total = len(filtered)
returning = int(filtered["is_returning_contributor"].sum())
first_time_only = total - returning
retention_rate = returning / total * 100 if total else 0
avg_review = filtered["first_review_time_hours"].mean()
avg_issue_part = filtered["issue_count"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Contributors", f"{total:,}")
c2.metric("First-Time Only", f"{first_time_only:,}")
c3.metric("Returning", f"{returning:,}")
c4.metric("Retention Rate", f"{retention_rate:.1f}%")
c5.metric("Avg. First Review Time", f"{avg_review:.1f}h")

st.divider()

# ---------------- Charts ----------------
left, right = st.columns(2)

with left:
    st.subheader("Retention rate by repository")
    repo_kpi = (
        filtered.groupby("repo")
        .agg(total=("user", "count"), returning=("is_returning_contributor", "sum"))
        .reset_index()
    )
    repo_kpi["retention_rate_pct"] = repo_kpi["returning"] / repo_kpi["total"] * 100
    fig = px.bar(
        repo_kpi.sort_values("retention_rate_pct"),
        x="retention_rate_pct", y="repo", orientation="h",
        labels={"retention_rate_pct": "Retention rate (%)", "repo": ""},
        color_discrete_sequence=[PRIMARY],
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Onboarding speed vs. retention")
    speed = (
        filtered.dropna(subset=["onboarding_speed_bucket"])
        .groupby("onboarding_speed_bucket")["is_returning_contributor"]
        .mean()
        .mul(100)
        .reset_index(name="retention_rate_pct")
    )
    order = ["fast (<12h)", "moderate (12-48h)", "slow (>48h)"]
    speed["onboarding_speed_bucket"] = pd.Categorical(speed["onboarding_speed_bucket"], categories=order, ordered=True)
    speed = speed.sort_values("onboarding_speed_bucket")
    fig2 = px.bar(
        speed, x="onboarding_speed_bucket", y="retention_rate_pct",
        labels={"onboarding_speed_bucket": "First review speed", "retention_rate_pct": "Retention rate (%)"},
        color="retention_rate_pct", color_continuous_scale=[BAD, ACCENT, GOOD],
    )
    fig2.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

left2, right2 = st.columns(2)

with left2:
    st.subheader("Issue participation vs. retention")
    issue_ret = (
        filtered.groupby("participated_in_issues")["is_returning_contributor"]
        .mean().mul(100).reset_index(name="retention_rate_pct")
    )
    issue_ret["participated_in_issues"] = issue_ret["participated_in_issues"].map({True: "Participated in issues", False: "No issue participation"})
    fig3 = px.bar(
        issue_ret, x="participated_in_issues", y="retention_rate_pct",
        labels={"participated_in_issues": "", "retention_rate_pct": "Retention rate (%)"},
        color_discrete_sequence=[PRIMARY],
    )
    st.plotly_chart(fig3, use_container_width=True)

with right2:
    st.subheader("Contributions over time")
    ts = filtered.set_index("first_pr_at").resample("ME")["user"].count().reset_index(name="new_contributors")
    fig4 = px.line(ts, x="first_pr_at", y="new_contributors", labels={"first_pr_at": "Month", "new_contributors": "New contributors"})
    fig4.update_traces(line_color=PRIMARY)
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ---------------- Alerts ----------------
st.subheader("Onboarding risk alerts")
risk_repos = repo_kpi[repo_kpi["retention_rate_pct"] < 45]
if not risk_repos.empty:
    for _, row in risk_repos.iterrows():
        st.warning(f"**{row['repo']}** has a retention rate of only {row['retention_rate_pct']:.1f}% — review onboarding for this repo.")
else:
    st.success("No repositories currently below the 45% retention threshold.")

st.divider()

# ---------------- Raw data ----------------
with st.expander("View filtered contributor data"):
    st.dataframe(filtered, use_container_width=True)

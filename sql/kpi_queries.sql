-- kpi_queries.sql
-- Core business-metric queries for the Contributor Onboarding Analytics Dashboard.
-- Run against contributor_compass.db (SQLite). Views defined first, then
-- example queries that use them.

-- ============================================================
-- 1. Reusable views
-- ============================================================

CREATE VIEW IF NOT EXISTS v_repo_kpis AS
SELECT
    repo,
    COUNT(*)                                            AS total_contributors,
    SUM(CASE WHEN is_returning_contributor = 0 THEN 1 ELSE 0 END) AS first_time_only_contributors,
    SUM(CASE WHEN is_returning_contributor = 1 THEN 1 ELSE 0 END) AS returning_contributors,
    ROUND(100.0 * SUM(CASE WHEN is_returning_contributor = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS retention_rate_pct,
    ROUND(AVG(first_review_time_hours), 1)              AS avg_first_review_hours,
    ROUND(AVG(issue_count), 2)                          AS avg_issue_participation
FROM contributors
GROUP BY repo;

CREATE VIEW IF NOT EXISTS v_onboarding_speed_retention AS
SELECT
    onboarding_speed_bucket,
    COUNT(*) AS contributors,
    ROUND(100.0 * SUM(CASE WHEN is_returning_contributor = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS retention_rate_pct
FROM contributors
WHERE onboarding_speed_bucket IS NOT NULL
GROUP BY onboarding_speed_bucket
ORDER BY
    CASE onboarding_speed_bucket
        WHEN 'fast (<12h)' THEN 1
        WHEN 'moderate (12-48h)' THEN 2
        WHEN 'slow (>48h)' THEN 3
    END;

CREATE VIEW IF NOT EXISTS v_issue_participation_retention AS
SELECT
    participated_in_issues,
    COUNT(*) AS contributors,
    ROUND(100.0 * SUM(CASE WHEN is_returning_contributor = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS retention_rate_pct
FROM contributors
GROUP BY participated_in_issues;

-- ============================================================
-- 2. Business questions -> queries
-- ============================================================

-- Q: How many first-time contributors return after their initial contribution?
SELECT repo, total_contributors, returning_contributors, retention_rate_pct
FROM v_repo_kpis
ORDER BY retention_rate_pct DESC;

-- Q: How long do PRs take to be reviewed on average, per repo?
SELECT repo, ROUND(AVG(review_time_hours), 1) AS avg_review_hours
FROM pull_requests
WHERE review_time_hours IS NOT NULL
GROUP BY repo
ORDER BY avg_review_hours;

-- Q: Does review time affect contributor retention?
SELECT * FROM v_onboarding_speed_retention;

-- Q: Does issue participation increase return likelihood?
SELECT * FROM v_issue_participation_retention;

-- Q: Which repos have highest/lowest retention?
SELECT repo, retention_rate_pct FROM v_repo_kpis ORDER BY retention_rate_pct DESC;

-- Q: PR merge rate per repo (a secondary onboarding-quality signal)
SELECT
    repo,
    COUNT(*) AS total_prs,
    SUM(is_merged) AS merged_prs,
    ROUND(100.0 * SUM(is_merged) / COUNT(*), 1) AS merge_rate_pct
FROM pull_requests
GROUP BY repo;

-- Q: Issues opened vs closed per repo
SELECT
    repo,
    COUNT(*) AS issues_opened,
    SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) AS issues_closed
FROM issues
GROUP BY repo;

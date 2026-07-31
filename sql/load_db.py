"""
load_db.py
Loads the processed CSVs into a SQLite database (contributor_compass.db)
so we can run real SQL for the analysis layer. Swap the sqlite3 connection
for a Postgres/MySQL connection string later if needed -- the query files
in this folder are standard ANSI SQL and should work with either.
"""
import sqlite3
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "contributor_compass.db"


def main():
    conn = sqlite3.connect(DB_PATH)

    pulls = pd.read_csv(PROCESSED_DIR / "pull_requests.csv")
    issues = pd.read_csv(PROCESSED_DIR / "issues.csv")
    contributors = pd.read_csv(PROCESSED_DIR / "contributors.csv")

    pulls.to_sql("pull_requests", conn, if_exists="replace", index=False)
    issues.to_sql("issues", conn, if_exists="replace", index=False)
    contributors.to_sql("contributors", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_repo_user ON pull_requests(repo, user)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_contrib_repo ON contributors(repo)")
    conn.commit()
    conn.close()
    print(f"Loaded into {DB_PATH}")


if __name__ == "__main__":
    main()

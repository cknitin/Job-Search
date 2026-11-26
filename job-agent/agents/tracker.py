"""SQLite tracker: dedupe, statuses, daily limits, CSV export."""
import csv
import json
import sqlite3
from datetime import date


class Tracker:
    def __init__(self, path="data/jobs.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,
            apply_type TEXT, kw_score REAL, fit_score INT, ats_coverage REAL, status TEXT,
            folder TEXT, notes TEXT, found_on TEXT, applied_on TEXT)""")

    def seen(self, job_id):
        return self.db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone() is not None

    def upsert(self, job, **kw):
        row = {"id": job["id"], "title": job["title"], "company": job["company"], "location": job["location"],
               "url": job["url"], "source": job["source"], "apply_type": job["apply_type"],
               "found_on": date.today().isoformat(), **kw}
        if "notes" in row and not isinstance(row["notes"], str):
            row["notes"] = json.dumps(row["notes"])
        cols = ",".join(row)
        upd = ",".join(f"{k}=excluded.{k}" for k in row if k not in ("id", "found_on"))
        self.db.execute(f"INSERT INTO jobs({cols}) VALUES({','.join('?' * len(row))}) "
                        f"ON CONFLICT(id) DO UPDATE SET {upd}", list(row.values()))
        self.db.commit()

    def set_status(self, job_id, status):
        applied = date.today().isoformat() if status.startswith("submitted") else None
        self.db.execute("UPDATE jobs SET status=?, applied_on=COALESCE(?, applied_on) WHERE id=?",
                        (status, applied, job_id))
        self.db.commit()

    def applied_today(self):
        return self.db.execute("SELECT COUNT(*) FROM jobs WHERE applied_on=?", (date.today().isoformat(),)).fetchone()[0]

    def ready(self):
        cur = self.db.execute("SELECT * FROM jobs WHERE status='ready' ORDER BY fit_score DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def export(self, path="data/tracker.csv"):
        cur = self.db.execute("SELECT * FROM jobs ORDER BY found_on DESC, fit_score DESC")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur.fetchall())
        return path

"""SQLite tracker: dedupe, statuses, daily limits, CSV export."""
import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

from .report import write_excel


class Tracker:
    def __init__(self, path="data/jobs.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,
            apply_type TEXT, kw_score REAL, fit_score INT, ats_coverage REAL, status TEXT,
            folder TEXT, notes TEXT, found_on TEXT, applied_on TEXT)""")

    def seen(self, job_id):
        # Keyword rejections are free to re-check, so a changed resume or config applies to them again.
        return self.db.execute("SELECT 1 FROM jobs WHERE id=? AND status != 'skipped-keywords'",
                               (job_id,)).fetchone() is not None

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

    def get(self, job_id):
        cur = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        return dict(zip([c[0] for c in cur.description], row)) if row else None

    def visible(self):
        """Jobs worth showing: everything except automatic rejections."""
        cur = self.db.execute("SELECT * FROM jobs WHERE status NOT LIKE 'skipped%' AND status != 'hidden' "
                              "ORDER BY found_on DESC, fit_score DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def ready(self):
        cur = self.db.execute("SELECT * FROM jobs WHERE status='ready' ORDER BY fit_score DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def excel_path(self, csv_path):
        csv_path = Path(csv_path)
        return csv_path.with_name(csv_path.stem.replace("tracker", "job_applications") + ".xlsx")

    def export(self, path="data/tracker.csv"):
        """Write the CSV and the Excel tracker next to it."""
        cur = self.db.execute("SELECT * FROM jobs ORDER BY found_on DESC, fit_score DESC")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            rows = cur.fetchall()
            w.writerows(rows)
        names = [c[0] for c in cur.description]
        write_excel([dict(zip(names, r)) for r in rows], self.excel_path(path))
        return path

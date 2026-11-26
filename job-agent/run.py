"""Job Agent orchestrator.

  python run.py hunt            # discover -> score -> tailor resume + cover letter (no applying)
  python run.py apply           # apply to 'ready' jobs (respects apply.mode and daily_limit)
  python run.py all             # hunt + apply  (use this in a daily scheduled task / cron)
  python run.py export          # data/tracker.csv
  python run.py hunt --demo     # offline test with sample jobs + mock LLM
"""
import json
import os
import sys
from pathlib import Path

import yaml

from agents import discover, match, tailor
from agents.apply import apply
from agents.llm import LLM
from agents.tracker import Tracker

ROOT = Path(__file__).parent


def load():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    master = yaml.safe_load((ROOT / "master_resume.yaml").read_text())
    cfg["apply"]["mode"] = os.environ.get("APPLY_MODE", cfg["apply"]["mode"])
    for k in ("name", "email", "phone", "linkedin", "location"):  # keep PII out of the repo
        if os.environ.get(f"CANDIDATE_{k.upper()}"):
            cfg["candidate"][k] = os.environ[f"CANDIDATE_{k.upper()}"]
    return cfg, master


def hunt(cfg, master, tr, demo=False):
    llm = LLM({"provider": "mock"} if demo else cfg["llm"])
    print("1/3 Discovering jobs...")
    jobs = (json.loads((ROOT / "sample_jobs.json").read_text()) if demo else discover.discover(cfg))
    jobs = [j for j in jobs if not tr.seen(j["id"])]
    print(f"    {len(jobs)} new relevant jobs")

    print("2/3 Scoring fit...")
    m = cfg["matching"]
    for j in jobs:
        j["kw"] = match.keyword_score(j, master)
    shortlist = sorted([j for j in jobs if j["kw"] >= m["min_keyword_score"]],
                       key=lambda j: -j["kw"])[: m["max_jobs_per_run"]]
    for j in jobs:
        if j not in shortlist:
            tr.upsert(j, kw_score=j["kw"], status="skipped-keywords")

    print(f"3/3 Tailoring for {len(shortlist)} shortlisted jobs...")
    for j in shortlist:
        fit = match.llm_fit(llm, j, master)
        score = int(fit.get("fit_score", 0))
        if score < m["min_fit_score"]:
            tr.upsert(j, kw_score=j["kw"], fit_score=score, status="skipped-fit", notes=fit)
            print(f"    - {score:>3}  {j['title']} @ {j['company']} (skipped)")
            continue
        folder = ROOT / "output" / f"{tailor.slug(j['company'])}_{tailor.slug(j['title'])}"
        p = tailor.plan(llm, j, master, fit.get("keywords", []))
        resume = folder / f"{tailor.slug(cfg['candidate']['name']) or 'resume'}_resume.docx"
        tailor.render(p, master, cfg["candidate"], resume)
        (folder / "cover_letter.txt").write_text(p.get("cover_letter", ""), encoding="utf-8")
        ats = tailor.ats_check(resume, fit.get("keywords", []))
        (folder / "job.json").write_text(json.dumps({**j, "fit": fit, "ats": ats}, indent=2), encoding="utf-8")
        tr.upsert(j, kw_score=j["kw"], fit_score=score, ats_coverage=ats["coverage"],
                  status="ready", folder=str(folder), notes={"gaps": fit.get("gaps"), "missing": ats["missing"]})
        print(f"    + {score:>3}  {j['title']} @ {j['company']}  ATS {int(ats['coverage']*100)}%  -> {folder.name}")


def do_apply(cfg, tr):
    a, cand = cfg["apply"], cfg["candidate"]
    for row in tr.ready():
        if tr.applied_today() >= a["daily_limit"]:
            print("Daily limit reached.")
            break
        folder = Path(row["folder"])
        job = json.loads((folder / "job.json").read_text())
        resume = next(folder.glob("*_resume.docx"))
        cover = (folder / "cover_letter.txt").read_text()
        print(f"Applying: {row['title']} @ {row['company']} [{row['apply_type']}, mode={a['mode']}]")
        try:
            status = apply(job, cand, resume, cover, a["mode"], a["headless"])
        except Exception as e:
            status = f"error: {e}"[:200]
        tr.set_status(row["id"], status)
        print(f"    -> {status}" + (f"  (apply manually: {row['url']})" if status == "packed" else ""))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "hunt"
    demo = "--demo" in sys.argv
    cfg, master = load()
    (ROOT / "data").mkdir(exist_ok=True)
    tr = Tracker(str(ROOT / ("data/demo.db" if demo else "data/jobs.db")))
    if cmd in ("hunt", "all"):
        hunt(cfg, master, tr, demo)
    if cmd in ("apply", "all"):
        do_apply(cfg, tr)
    print("Tracker:", tr.export(str(ROOT / "data" / ("demo_tracker.csv" if demo else "tracker.csv"))))

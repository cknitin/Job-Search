"""Job Agent orchestrator.

  python run.py find            # search only: save matching jobs and descriptions (no API key needed)
  python run.py hunt            # search -> score -> tailor resume + cover letter (no applying)
  python run.py inbox           # tailor only the jobs you saved in jobs_inbox/
  python run.py apply           # apply to 'ready' jobs (respects apply.mode and daily_limit)
  python run.py all             # hunt + apply  (use this in a daily scheduled task / cron)
  python run.py export          # data/tracker.csv
  python run.py hunt --demo     # offline test with sample jobs and placeholder text
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import yaml

from agents import coach, discover, match, profile, tailor
from agents.apply import apply
from agents.llm import LLM
from agents.tracker import Tracker

ROOT = Path(__file__).parent
INBOX = ROOT / "jobs_inbox"
COMMANDS = ("find", "hunt", "inbox", "apply", "apply-one", "all", "export", "prep")


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}


def load():
    cfg = read_yaml(ROOT / "config.yaml")
    master = read_yaml(ROOT / "master_resume.yaml")
    local = ROOT / "config.local.yaml"  # your contact details; ignored by git
    if local.exists():
        cfg["candidate"].update(read_yaml(local).get("candidate", {}))
    cfg["apply"]["mode"] = os.environ.get("APPLY_MODE") or cfg["apply"]["mode"]
    for k in ("name", "email", "phone", "linkedin", "location"):  # keep PII out of the repo
        if os.environ.get(f"CANDIDATE_{k.upper()}"):
            cfg["candidate"][k] = os.environ[f"CANDIDATE_{k.upper()}"]
    profile.apply_to(cfg, profile.load(ROOT))
    return cfg, master


def folder_for(base: Path, job: dict) -> Path:
    short = hashlib.sha1(job["id"].encode()).hexdigest()[:6]
    return base / f"{tailor.slug(job['company'])}_{tailor.slug(job['title'])}_{short}"


def collect(cfg, master, tr, source):
    """Return (jobs from job sites that pass the keyword filter, jobs from the inbox)."""
    online, manual = [], []
    if source == "demo":
        online = json.loads((ROOT / "sample_jobs.json").read_text(encoding="utf-8"))
        for j in online:
            j.setdefault("partial_description", False)
    else:
        if source != "inbox":
            online = discover.discover(cfg)
        manual = discover.inbox(INBOX)

    mine = cfg["search"].get("skills")  # your search profile, if you set one
    for j in online + manual:
        j["kw"] = profile.skill_score(j, mine) if mine else match.keyword_score(j, master)
    if tr:
        online = [j for j in online if not tr.seen(j["id"])]
        manual = [j for j in manual if not tr.seen(j["id"])]
    m = cfg["matching"]
    good = [j for j in online if j["kw"] >= m["min_keyword_score"] or j.get("partial_description")]
    cities = cfg["search"].get("preferred_cities") or []  # your first city first, then by skill match
    good = sorted(good, key=lambda j: (profile.city_rank(j, cities), -j["kw"]))
    for j in online:
        if tr and j not in good:
            tr.upsert(j, kw_score=j["kw"], status="skipped-keywords")
    print(f"    {len(good)} job(s) from job sites pass the filters, {len(manual)} from your inbox")
    return good[: m["max_jobs_per_run"]], manual


def find(cfg, master):
    """Search and save job details. Uses no AI and records nothing in the tracker."""
    print("Searching...")
    good, manual = collect(cfg, master, None, "online")
    base = ROOT / "output" / "_found"
    shutil.rmtree(base, ignore_errors=True)  # a fresh list every time
    base.mkdir(parents=True)
    index = []
    for j in manual + good:
        folder = folder_for(base, j)
        folder.mkdir(exist_ok=True)
        (folder / "job_details.txt").write_text(tailor.job_details(j), encoding="utf-8")
        index.append(f"[{int(j['kw'] * 100):>3}] {j['title']} @ {j['company']} ({j['location']})\n"
                     f"      {j['url']}\n      {folder.name}")
        print(f"    [{int(j['kw'] * 100):>3}] {j['title']} @ {j['company']} ({j['location']})")
    (base / "found.json").write_text(json.dumps(manual + good, ensure_ascii=False), encoding="utf-8")
    (base / "jobs_found.txt").write_text("\n\n".join(index) or "No matching jobs found.", encoding="utf-8")
    print(f"\nSaved to {base}")


def prepare(llm, cfg, master, tr, job, base, manual) -> None:
    """Score one job and, if it fits, write its resume, cover letter and details."""
    fit = match.llm_fit(llm, job, master)
    score = fit["fit_score"]
    # Jobs you saved yourself are always prepared; the score is information, not a gate.
    if not manual and score < cfg["matching"]["min_fit_score"]:
        tr.upsert(job, kw_score=job["kw"], fit_score=score, status="skipped-fit", notes=fit)
        print(f"    - {score:>3}  {job['title']} @ {job['company']} (below your minimum, skipped)")
        return

    cand = cfg["candidate"]
    folder = folder_for(base, job)
    p = tailor.plan(llm, job, master, fit["keywords"])
    name = tailor.slug(cand["name"]) or "candidate"
    resume = folder / f"{name}_resume.docx"
    tailor.render(p, master, cand, resume, job)
    letter = tailor.cover_letter(p, cand, job)
    (folder / "cover_letter.txt").write_text(letter, encoding="utf-8")
    tailor.render_letter(letter, folder / f"{name}_cover_letter.docx")

    ats = tailor.ats_check(resume, fit["keywords"])
    warnings = []
    odd = tailor.unverified_numbers(" ".join(p["cover_letter_paragraphs"]), master, job)
    if odd:
        warnings.append(f"The cover letter has figures not found in your resume or the job: {', '.join(sorted(odd))}")
    if llm.provider == "mock":
        warnings.append("DEMO output. The scores and cover letter are placeholders. Do not send.")
    (folder / "job_details.txt").write_text(tailor.job_details(job, fit, ats, warnings), encoding="utf-8")
    (folder / "job.json").write_text(json.dumps({**job, "fit": fit, "ats": ats}, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    tr.upsert(job, kw_score=job["kw"], fit_score=score, ats_coverage=ats["coverage"],
              status="ready", folder=str(folder), notes={"gaps": fit["gaps"], "missing": ats["missing"]})
    print(f"    + {score:>3}  {job['title']} @ {job['company']}  -> {folder.name}")
    for w in warnings:
        print(f"           ! {w}")


def hunt(cfg, master, tr, source):
    llm = LLM({"provider": "mock"} if source == "demo" else cfg["llm"])
    print("1/2 Searching...")
    good, manual = collect(cfg, master, tr, source)
    base = ROOT / "output" / "_demo" if source == "demo" else ROOT / "output"
    print(f"2/2 Scoring and writing documents for {len(good) + len(manual)} job(s)...")
    for job, is_manual in [(j, True) for j in manual] + [(j, False) for j in good]:
        try:
            prepare(llm, cfg, master, tr, job, base, is_manual)
        except Exception as e:  # not recorded, so it is retried on the next run
            print(f"    x  {job['title']} @ {job['company']}: {type(e).__name__}: {e}")
    if not (good or manual):
        print("    Nothing new. Save jobs from LinkedIn/Naukri into jobs_inbox/ (see jobs_inbox/_example.txt).")


def apply_row(cfg, tr, row, mode, interactive=True):
    """Apply to one tracked job."""
    a, cand = cfg["apply"], cfg["candidate"]
    if mode != "pack" and "example.com" in cand["email"]:
        raise SystemExit("Set your real contact details in config.local.yaml before applying.")
    folder = Path(row["folder"] or "")
    resumes = list(folder.glob("*_resume.docx"))
    if not resumes or not (folder / "job.json").exists():
        print(f"Skipping {row['title']} @ {row['company']}: files not found in {folder}")
        return
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    cover = (folder / "cover_letter.txt").read_text(encoding="utf-8")
    print(f"Applying: {row['title']} @ {row['company']} [{row['apply_type']}, mode={mode}]")
    try:
        status = apply(job, cand, resumes[0], cover, mode, a["headless"], interactive)
    except Exception as e:
        status = f"error: {e}"[:200]
    tr.set_status(row["id"], status)
    print(f"    -> {status}" + (f"  (apply yourself: {row['url']}; files: {folder})" if status == "packed" else ""))


def do_apply(cfg, tr, interactive=True):
    a = cfg["apply"]
    for row in tr.ready():
        if tr.applied_today() >= a["daily_limit"]:
            print("Daily limit reached.")
            break
        apply_row(cfg, tr, row, a["mode"], interactive)


def apply_one(cfg, tr, job_id, mode):
    """Used by the web UI: apply to the one job you clicked."""
    row = tr.get(job_id)
    if not row:
        raise SystemExit("Job not found in the tracker.")
    if row["status"].startswith("submitted"):
        raise SystemExit("You already applied to this job.")
    if row["apply_type"] not in ("greenhouse", "lever"):
        raise SystemExit("This site does not support form filling. Open the link and apply yourself.")
    if mode == "auto" and tr.applied_today() >= cfg["apply"]["daily_limit"]:
        raise SystemExit("Daily limit reached.")
    apply_row(cfg, tr, row, mode, interactive=False)


def prep(cfg, master, tr, job_id):
    """Write interview_prep.txt for one prepared job."""
    row = tr.get(job_id)
    folder = Path(row["folder"] or "") if row else None
    if not row or not row["folder"] or not (folder / "job.json").is_file():
        raise SystemExit("Create documents for this job first.")
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    llm = LLM(cfg["llm"])
    print(f"Preparing interview questions for {job['title']} at {job['company']} (this can take a minute)...")
    path = coach.prepare_interview(llm, ROOT, job, master, folder)
    print(f"    Saved: {path}")
    print("    Open it with the 'Interview prep' link on the job.")


def main():
    for stream in (sys.stdout, sys.stderr):  # job titles can contain characters Windows consoles lack
        stream.reconfigure(errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cmd = args[0] if args else "hunt"
    demo = "--demo" in sys.argv
    if cmd not in COMMANDS:
        raise SystemExit(__doc__)
    cfg, master = load()
    if cmd == "find":
        return find(cfg, master)

    (ROOT / "data").mkdir(exist_ok=True)
    db = ROOT / ("data/demo.db" if demo else "data/jobs.db")
    if demo and cmd in ("hunt", "all"):
        db.unlink(missing_ok=True)  # the demo starts fresh every time
    tr = Tracker(str(db))
    if cmd == "prep":
        if len(args) < 2:
            raise SystemExit("Usage: python run.py prep <job id from data/tracker.csv>")
        return prep(cfg, master, tr, args[1])
    if cmd == "apply-one":
        apply_one(cfg, tr, args[1], "auto" if "--auto" in sys.argv else "review")
        tr.export(str(ROOT / "data" / "tracker.csv"))
        return
    if cmd in ("hunt", "all", "inbox"):
        hunt(cfg, master, tr, "demo" if demo else "inbox" if cmd == "inbox" else "online")
    if cmd in ("apply", "all"):
        do_apply(cfg, tr, interactive="--ui" not in sys.argv)  # the web page has no keyboard input
    print("Tracker:", tr.export(str(ROOT / "data" / ("demo_tracker.csv" if demo else "tracker.csv"))))


if __name__ == "__main__":
    main()

"""Local web UI for the job agent.   Start:  python ui.py   (or double-click ui.bat)

Runs only on this computer (127.0.0.1). It opens LinkedIn/Naukri/Indeed in your own browser, where you log in
and apply yourself; the agent never sees those passwords and never automates those sites.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import run
import ui_page
from agents import coach, discover, extras, match, profile, tailor
from agents.llm import LLM
from agents.tracker import Tracker

ROOT = Path(__file__).parent
PORT = 8765
TOKEN = secrets.token_urlsafe(24)  # stops other web pages from sending commands to this server
SESSION = {"api_key": "", "message": ""}
TASK = {"proc": None, "name": "", "log": []}
LOCK = threading.Lock()


# ---------- background work ----------
def start_task(name, *args):
    with LOCK:
        if running():
            return "Another task is still running. Wait for it to finish."
        env = dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1")
        if SESSION["api_key"]:
            env["ANTHROPIC_API_KEY"] = SESSION["api_key"]
        proc = subprocess.Popen([sys.executable, str(ROOT / "run.py"), *args], cwd=ROOT, env=env, text=True,
                                encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        TASK.update(proc=proc, name=name, log=[], saved=False)

    log = TASK["log"]

    def read():
        for line in proc.stdout:
            log.append(line.rstrip())
        save_run(name, proc.wait() == 0, log)
        if TASK["proc"] is proc:
            TASK["saved"] = True

    threading.Thread(target=read, daemon=True).start()
    return ""


def running():
    # A task counts as running until its result has been saved, so the page never reloads too early.
    return bool(TASK["proc"]) and not TASK.get("saved")


def runs_file():
    return ROOT / "output" / "last_runs.json"


def last_runs() -> dict:
    try:
        return json.loads(runs_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_run(name, ok, log):
    runs = last_runs()
    runs[name] = {"when": datetime.now().strftime("%d %b %Y, %H:%M"), "order": datetime.now().timestamp(),
                  "ok": ok, "log": "\n".join(log[-200:])}
    runs_file().parent.mkdir(exist_ok=True)
    runs_file().write_text(json.dumps(runs), encoding="utf-8")


# ---------- data ----------
def tracker():
    (ROOT / "data").mkdir(exist_ok=True)
    return Tracker(str(ROOT / "data" / "jobs.db"))


def found_jobs():
    f = ROOT / "output" / "_found" / "found.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def save_to_inbox(title, company, location, url, description):
    one = lambda v: " ".join(v.split())  # header values must stay on one line
    title, company = one(title), one(company)
    if not (title and company):
        return "Enter the job title and company."
    if len(description.split()) < 30:
        return "Paste the full job description (at least 30 words)."
    folder = ROOT / "jobs_inbox"
    folder.mkdir(exist_ok=True)
    name = f"{tailor.slug(company)}_{tailor.slug(title)}".strip("_") or "job"
    path, n = folder / f"{name}.txt", 2
    while path.exists():
        path, n = folder / f"{name}_{n}.txt", n + 1
    body = description.replace("\r\n", "\n").strip()
    path.write_text(f"Title: {title}\nCompany: {company}\nLocation: {one(location)}\nURL: {one(url)}\n---\n{body}\n",
                    encoding="utf-8")
    return f"Saved '{title}' at {company}. Click 'Create documents' when you are ready."


def record_applied(title, company, location, url):
    """Log a job you applied to yourself, so it appears in the Excel tracker."""
    title, company = " ".join(title.split()), " ".join(company.split())
    if not (title and company):
        return "Enter the job title and company."
    url = url.strip()
    key = "manual:" + hashlib.sha1(f"{title}|{company}|{url}".lower().encode()).hexdigest()[:12]
    tr = tracker()
    if tr.get(key):
        return "That application is already recorded."
    tr.upsert({"id": key, "title": title, "company": company, "location": location.strip(), "url": url,
               "source": "manual", "apply_type": "link"}, status="submitted-by-user")
    tr.set_status(key, "submitted-by-user")
    export(tr)
    return f"Recorded your application to {company}."


def export(tr):
    tr.export(str(ROOT / "data" / "tracker.csv"))


def job_files(row):
    """The documents for one job, only if they are inside the output folder."""
    if not row or not row.get("folder"):
        return {}
    folder = Path(row["folder"]).resolve()
    if (ROOT / "output").resolve() not in folder.parents or not folder.is_dir():
        return {}
    wanted = {"details": "job_details.txt", "resume": "*_resume.docx", "letter": "*_cover_letter.docx",
              "lettertext": "cover_letter.txt",
              "prep": "interview_prep.txt", "data": "job.json"}
    return {k: next(folder.glob(v)) for k, v in wanted.items() if any(folder.glob(v))}


def smart_save(page_text, url):
    """Let the AI pick the job out of a whole copied page, then save it to the inbox."""
    if len(page_text.split()) < 30:
        return "Paste the whole job page into the description box first (Ctrl+A, Ctrl+C on the job page)."
    cfg, _ = run.load()
    try:
        job = extras.smart_extract(LLM(cfg["llm"], SESSION["api_key"]), page_text)
    except SystemExit as e:  # missing or rejected key
        return str(e)
    except Exception as e:
        return f"Smart save failed: {e}"
    return save_to_inbox(job["title"], job["company"], job["location"], url, job["description"])


# ---------- page ----------
def render():
    cfg, master = run.load()
    tr = tracker()
    saved = [j for j in discover.inbox(ROOT / "jobs_inbox") if not tr.seen(j["id"])]
    message, SESSION["message"] = SESSION["message"], ""
    cur = tr.db.execute("SELECT * FROM jobs WHERE status='skipped-fit' ORDER BY found_on DESC, fit_score DESC")
    skipped = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    return ui_page.render({
        "outcomes": extras.outcomes(ROOT, tr.visible(), cfg["search"]["titles"]), "alerts": extras.alerts(ROOT),
        "profile": profile.load(ROOT), "followups": coach.follow_ups(ROOT, tr.visible(), cfg["candidate"]),
        "skills": coach.skill_report(list(coach.descriptions(ROOT, tr.visible()).values()), master),
        "runs": last_runs(), "skipped": skipped, "token": TOKEN, "cfg": cfg, "jobs": tr.visible(), "saved": saved, "found": found_jobs(), "files": job_files,
        "today": date.today().isoformat(), "message": message, "busy": running(), "task": TASK["name"],
        "log": "\n".join(TASK["log"][-200:]),
        "has_key": bool(SESSION["api_key"] or os.environ.get("ANTHROPIC_API_KEY")),
        "adzuna": bool(os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY")),
    })


# ---------- server ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _local(self):
        # Rejects requests made under another host name (DNS rebinding).
        return self.headers.get("Host", "") in (f"127.0.0.1:{self.server.server_port}",
                                                f"localhost:{self.server.server_port}")

    def _send(self, body: bytes, kind="text/html; charset=utf-8", code=200, headers=None):
        self.send_response(code)
        for k, v in {"Content-Type": kind, "Content-Length": str(len(body)), "Cache-Control": "no-store",
                     **(headers or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._local():
            return self._send(b"Forbidden", code=403)
        url = urlsplit(self.path)
        if url.path == "/":
            return self._send(render().encode())
        if url.path == "/status":
            data = {"running": running(), "log": "\n".join(TASK["log"][-200:])}
            return self._send(json.dumps(data).encode(), "application/json")
        if url.path == "/excel":
            tr = tracker()
            export(tr)
            path = ROOT / "data" / "job_applications.xlsx"
            if path.exists():
                return self._send(path.read_bytes(), "application/octet-stream",
                                  headers={"Content-Disposition": 'attachment; filename="job_applications.xlsx"'})
        if url.path == "/file":
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            path = job_files(tracker().get(q.get("id", ""))).get(q.get("kind"))
            if path:
                if path.suffix == ".txt":
                    return self._send(path.read_bytes(), "text/plain; charset=utf-8")
                name = re.sub(r"[^A-Za-z0-9._-]", "_", path.name)
                return self._send(path.read_bytes(), "application/octet-stream",
                                  headers={"Content-Disposition": f'attachment; filename="{name}"'})
        self._send(b"Not found", code=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 6_000_000:  # alert emails can be large
            return self._send(b"Too large", code=413)
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8", "replace")).items()}
        if not self._local() or not secrets.compare_digest(form.get("token", ""), TOKEN):
            return self._send(b"Forbidden. Reload the page and try again.", code=403)
        SESSION["message"] = self.act(urlsplit(self.path).path, form) or ""
        tab = form.get("tab", "")
        if urlsplit(self.path).path in ("/task", "/apply", "/prep"):
            tab = "results"  # show what the command produces
        where = f"/#{tab}" if tab in dict(ui_page.TABS) else "/"
        self._send(b"", code=303, headers={"Location": where})

    def act(self, path, f):
        if path == "/task" and f.get("name") in ("find", "hunt", "inbox", "apply", "all", "export"):
            return start_task(f["name"], f["name"], "--ui")
        if path == "/alert":
            cfg, master = run.load()
            return extras.import_alert(ROOT, f.get("raw", ""), cfg["search"]["titles"], sorted(match.resume_terms(master)))
        if path == "/add":
            if f.get("do") == "smart":
                return smart_save(f.get("description", ""), f.get("url", ""))
            if f.get("do") == "applied":
                return record_applied(*(f.get(k, "") for k in ("title", "company", "location", "url")))
            return save_to_inbox(*(f.get(k, "") for k in ("title", "company", "location", "url", "description")))
        if path == "/use":
            jobs, i = found_jobs(), f.get("index", "")
            if i.isdigit() and int(i) < len(jobs):
                j = jobs[int(i)]
                return save_to_inbox(j["title"], j["company"], j["location"], j["url"], j["description"])
        if path == "/apply" and f.get("mode") in ("auto", "review"):
            args = ["apply-one", f.get("id", "")] + (["--auto"] if f["mode"] == "auto" else [])
            return start_task("apply", *args)
        if path == "/mark" and f.get("status") in ("submitted-by-user", "hidden"):
            tr = tracker()
            tr.set_status(f.get("id", ""), f["status"])
            export(tr)
            return ""
        if path == "/prep":
            return start_task("prep", "prep", f.get("id", ""))
        if path == "/followed":
            coach.mark_followed(ROOT, f.get("id", ""))
            return "Marked as followed up."
        if path == "/profile":
            return profile.save(ROOT, *(f.get(k, "") for k in ("skills", "experience", "titles", "locations")),
                                work=[w for w in profile.WORK if f.get(f"work_{w}")])
        if path == "/key":
            SESSION["api_key"] = f.get("key", "").strip()
            return "API key set for this session." if SESSION["api_key"] else "API key cleared."
        return "Unknown action."


class Server(ThreadingHTTPServer):
    # On Windows, "reuse address" lets a second copy share the port, and the browser then reaches the old one.
    allow_reuse_address = os.name != "nt"


def main():
    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        raise SystemExit(f"Port {PORT} is in use. Is the Job Agent already open? http://127.0.0.1:{PORT}")
    address = f"http://127.0.0.1:{PORT}"
    print(f"Job Agent is running at {address}\nKeep this window open. Press Ctrl+C to stop.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, [address]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

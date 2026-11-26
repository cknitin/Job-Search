"""Discovery agent: pulls jobs from public job APIs and normalises them."""
import html
import os
import re
from datetime import datetime, timedelta, timezone

import requests

UA = {"User-Agent": "job-agent/1.0 (personal job search)"}


def _clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _job(source, ext_id, title, company, location, url, description, posted=None, apply_type="link"):
    return {"id": f"{source}:{ext_id}", "source": source, "title": title, "company": company,
            "location": location or "", "url": url, "description": _clean(description),
            "posted": posted or "", "apply_type": apply_type}


def remotive(search):
    out = []
    for t in search["titles"]:
        r = requests.get("https://remotive.com/api/remote-jobs", params={"search": t}, headers=UA, timeout=30)
        for j in r.json().get("jobs", []):
            out.append(_job("remotive", j["id"], j["title"], j["company_name"],
                            j.get("candidate_required_location"), j["url"], j["description"],
                            j.get("publication_date")))
    return out


def adzuna(search, cfg):
    app_id, app_key = os.environ.get(cfg["app_id_env"]), os.environ.get(cfg["app_key_env"])
    if not (app_id and app_key):
        print("  adzuna: keys missing, skipped")
        return []
    out = []
    for t in search["titles"]:
        r = requests.get(f"https://api.adzuna.com/v1/api/jobs/{cfg['country']}/search/1",
                         params={"app_id": app_id, "app_key": app_key, "what": t,
                                 "max_days_old": search["max_age_days"], "results_per_page": 50},
                         headers=UA, timeout=30)
        for j in r.json().get("results", []):
            out.append(_job("adzuna", j["id"], j["title"], j.get("company", {}).get("display_name", ""),
                            j.get("location", {}).get("display_name"), j["redirect_url"],
                            j.get("description"), j.get("created")))
    return out


def greenhouse(slug):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                     params={"content": "true"}, headers=UA, timeout=30)
    return [_job("greenhouse", j["id"], j["title"], slug, j.get("location", {}).get("name"),
                 j["absolute_url"], j.get("content"), j.get("updated_at"), "greenhouse")
            for j in r.json().get("jobs", [])]


def lever(slug):
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}, headers=UA, timeout=30)
    return [_job("lever", j["id"], j["text"], slug, j.get("categories", {}).get("location"),
                 j["hostedUrl"], j.get("descriptionPlain") or j.get("description"),
                 datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc).isoformat(), "lever")
            for j in r.json()]


def discover(cfg) -> list:
    s, src, jobs = cfg["search"], cfg["sources"], []
    tasks = []
    if src.get("remotive"):
        tasks.append(("remotive", lambda: remotive(s)))
    if src.get("adzuna", {}).get("enabled"):
        tasks.append(("adzuna", lambda: adzuna(s, src["adzuna"])))
    for slug in src.get("greenhouse_boards", []):
        tasks.append((f"greenhouse/{slug}", lambda slug=slug: greenhouse(slug)))
    for slug in src.get("lever_companies", []):
        tasks.append((f"lever/{slug}", lambda slug=slug: lever(slug)))
    for name, fn in tasks:
        try:
            got = fn()
            print(f"  {name}: {len(got)} jobs")
            jobs += got
        except Exception as e:  # one bad source must not kill the run
            print(f"  {name}: failed ({e})")
    return [j for j in jobs if _relevant(j, s)]


def _relevant(job, s) -> bool:
    title = job["title"].lower()
    if not any(w.lower() in title for w in ["architect"] + [t.lower() for t in s["titles"]]):
        return False
    text = (job["title"] + " " + job["description"]).lower()
    if any(x.lower() in text for x in s["exclude_words"]):
        return False
    if job["posted"]:
        try:
            d = datetime.fromisoformat(job["posted"].replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if d < datetime.now(timezone.utc) - timedelta(days=s["max_age_days"]):
                return False
        except ValueError:
            pass
    loc = job["location"].lower()
    if loc and not (s.get("remote_ok") and ("remote" in loc or "anywhere" in loc or "worldwide" in loc)):
        if not any(l.lower() in loc for l in s["locations"]):
            return False
    return True

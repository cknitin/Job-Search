"""Discovery agent: pulls jobs from public job APIs and your inbox folder, and normalises them."""
import hashlib
import html
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

UA = {"User-Agent": "job-agent/1.0 (personal job search)"}
# Words that only disqualify a job when they are in its TITLE ("mentor junior developers" is fine).
TITLE_ONLY_EXCLUDES = {"junior", "intern", "internship", "fresher", "trainee"}


def has_word(text: str, word: str) -> bool:
    """Whole-word, case-insensitive match: 'intern' must not match 'internal' or 'international'."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def _clean(s: str) -> str:
    """HTML -> readable plain text that keeps paragraphs and bullet points."""
    s = html.unescape(s or "")
    s = re.sub(r"(?i)<li[^>]*>", "\n- ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|ul|ol|tr)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _job(source, ext_id, title, company, location, url, description, posted=None, apply_type="link", partial=False):
    return {"id": f"{source}:{ext_id}", "source": source, "title": (title or "").strip(),
            "company": (company or "").strip(), "location": location or "", "url": url or "",
            "description": _clean(description), "posted": posted or "", "apply_type": apply_type,
            "partial_description": partial}


def _get(url, **params):
    r = requests.get(url, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def remotive(search):
    out = []
    for t in search["titles"]:
        for j in _get("https://remotive.com/api/remote-jobs", search=t).get("jobs", []):
            out.append(_job("remotive", j["id"], j["title"], j["company_name"],
                            j.get("candidate_required_location") or "Remote", j["url"], j["description"],
                            j.get("publication_date")))
    return out


def adzuna(search, cfg):
    app_id, app_key = os.environ.get(cfg["app_id_env"]), os.environ.get(cfg["app_key_env"])
    if not (app_id and app_key):
        print("  adzuna: keys missing, skipped")
        return []
    out = []
    for t in search["titles"]:
        data = _get(f"https://api.adzuna.com/v1/api/jobs/{cfg['country']}/search/1", app_id=app_id, app_key=app_key,
                    what_phrase=t, max_days_old=search["max_age_days"], results_per_page=50)
        for j in data.get("results", []):
            # Adzuna's API returns only the opening lines of each description.
            out.append(_job("adzuna", j["id"], j["title"], j.get("company", {}).get("display_name", ""),
                            j.get("location", {}).get("display_name"), j["redirect_url"],
                            j.get("description"), j.get("created"), partial=True))
    return out


def greenhouse(slug):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", content="true")
    return [_job("greenhouse", j["id"], j["title"], j.get("company_name") or slug.title(),
                 j.get("location", {}).get("name"), j["absolute_url"], j.get("content"),
                 j.get("first_published") or j.get("updated_at"), "greenhouse")
            for j in data.get("jobs", [])]


def lever(slug):
    out = []
    for j in _get(f"https://api.lever.co/v0/postings/{slug}", mode="json"):
        # Lever splits a posting into an intro, several lists (requirements etc.) and a closing note.
        body = j.get("description") or j.get("descriptionPlain") or ""
        for block in j.get("lists", []):
            body += f"<p>{block.get('text', '')}</p><ul>{block.get('content', '')}</ul>"
        body += j.get("additional") or ""
        out.append(_job("lever", j["id"], j["text"], slug.title(), j.get("categories", {}).get("location"),
                        j["hostedUrl"], body,
                        datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc).isoformat(), "lever"))
    return out


def inbox(folder: Path) -> list:
    """Jobs you saved by hand (LinkedIn, Naukri, email...). See jobs_inbox/_example.txt."""
    out = []
    for f in sorted(folder.glob("*.txt")):
        if f.name.startswith("_"):
            continue
        raw = f.read_text(encoding="utf-8-sig", errors="replace")
        head, sep, body = raw.partition("\n---")
        fields = dict(re.findall(r"(?mi)^(title|company|location|url)\s*:[ \t]*(.*?)\s*$", head)) if sep else {}
        fields = {k.lower(): v for k, v in fields.items()}
        body = body.lstrip("-\n ") if sep else raw
        if not (fields.get("title") and fields.get("company") and len(body.split()) >= 30):
            print(f"  inbox: {f.name} skipped (needs Title, Company, a '---' line and the full job description)")
            continue
        key = hashlib.sha1(" ".join(raw.split()).encode()).hexdigest()[:12]
        job = _job("inbox", key, fields["title"], fields["company"], fields.get("location"),
                   fields.get("url"), "")
        job["description"] = body.strip()
        out.append(job)
    return out


def discover(cfg) -> list:
    s, src, jobs = cfg["search"], cfg["sources"], []
    tasks = []
    if src.get("remotive"):
        tasks.append(("remotive", lambda: remotive(s)))
    if src.get("adzuna", {}).get("enabled"):
        tasks.append(("adzuna", lambda: adzuna(s, src["adzuna"])))
    for slug in src.get("greenhouse_boards") or []:
        tasks.append((f"greenhouse/{slug}", lambda slug=slug: greenhouse(slug)))
    for slug in src.get("lever_companies") or []:
        tasks.append((f"lever/{slug}", lambda slug=slug: lever(slug)))
    for name, fn in tasks:
        try:
            got = fn()
            print(f"  {name}: {len(got)} jobs")
            jobs += got
        except Exception as e:  # one bad source must not kill the run
            # Never print the exception text: for Adzuna it contains the API key in the URL.
            status = getattr(getattr(e, "response", None), "status_code", "")
            print(f"  {name}: failed ({type(e).__name__} {status})")

    unique = {j["id"]: j for j in jobs}.values()
    kept, dropped, seen = [], Counter(), set()
    for j in unique:
        reason = rejection(j, s)
        key = (j["company"].lower(), j["title"].lower(), j["location"].lower())
        if not reason and key in seen:
            reason = "duplicate"
        if reason:
            dropped[reason] += 1
        else:
            seen.add(key)
            kept.append(j)
    print("  filtered out: " + (", ".join(f"{n} {r}" for r, n in dropped.most_common()) or "none"))
    return kept


def location_ok(location: str, s: dict) -> bool:
    loc = (location or "").lower()
    if not loc:
        return True
    if s.get("remote_only") and not any(has_word(loc, w) for w in ("remote", "worldwide", "anywhere")):
        return False
    places = [p for p in s["locations"] if p.lower() != "remote"]
    if any(has_word(loc, p) for p in places):
        return True
    if not s.get("remote_ok"):
        return False
    if any(has_word(loc, w) for w in ("worldwide", "anywhere", "apac", "asia")):
        return True
    # "Remote" alone is fine; "Remote, United States" is not open to someone in India.
    return has_word(loc, "remote") and not re.sub(r"remote|fully|global|[^a-z]", "", loc)


def rejection(job, s):
    """Why this job is not relevant, or None if it is."""
    title = job["title"].lower()
    if not any(has_word(title, w) for w in ["architect"] + s["titles"]):
        return "other job title"
    text = title + " " + job["description"].lower()
    for x in s.get("exclude_words") or []:
        if has_word(title if x.lower() in TITLE_ONLY_EXCLUDES else text, x):
            return f"excluded word '{x}'"
    if job["posted"]:
        try:
            d = datetime.fromisoformat(job["posted"].replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if d < datetime.now(timezone.utc) - timedelta(days=s["max_age_days"]):
                return "too old"
        except ValueError:
            pass
    if not location_ok(job["location"], s):
        return "location"
    if not job.get("partial_description"):
        from .profile import experience_problem  # imported here: profile.py uses has_word from this file
        problem = experience_problem(job["description"], s.get("experience"))
        if problem:
            return problem
    must = s.get("must_have_any") or []
    if must and not job.get("partial_description") and not any(has_word(text, w) for w in must):
        return "none of the must-have words"
    return None

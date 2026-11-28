"""Your search profile (skills, experience, titles, cities), saved from the Settings tab."""
import re
from pathlib import Path

import yaml

from .discover import has_word

FILE = "profile.local.yaml"  # ignored by git
WORK = ("remote", "hybrid", "onsite")


def _items(text: str, limit: int) -> list:
    """'C#, Azure,\\n .NET' -> ['C#', 'Azure', '.NET'] without blanks or repeats."""
    out = {}
    for part in re.split(r"[,;\n]+", text or ""):
        part = " ".join(part.split())[:60]
        if part:
            out.setdefault(part.lower(), part)
    return list(out.values())[:limit]


def load(root: Path) -> dict:
    try:
        return yaml.safe_load((root / FILE).read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


def save(root: Path, skills: str, experience: str, titles: str, locations: str, work=()) -> str:
    experience = (experience or "").strip()
    if experience and not (experience.isdigit() and int(experience) <= 45):
        return "Experience must be a whole number of years, for example 17."
    data = {"skills": _items(skills, 30), "experience": int(experience) if experience else None,
            "titles": _items(titles, 10), "locations": _items(locations, 15),
            "work": [w for w in WORK if w in work]}
    (root / FILE).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return "Search profile saved. Portal searches and the automatic search now use it."


def apply_to(cfg: dict, profile: dict):
    """Anything left empty in the profile keeps the value from config.yaml."""
    search = cfg["search"]
    for key in ("titles", "locations"):
        if profile.get(key):
            search[key] = profile[key]
    search["skills"] = profile.get("skills") or []
    search["experience"] = profile.get("experience")
    work = profile.get("work") or []
    search["work"] = work
    search["preferred_cities"] = [c for c in profile.get("locations") or [] if c.lower() != "remote"]
    if work:  # ticking nothing keeps the setting in config.yaml
        search["remote_ok"] = "remote" in work or any(c.lower() == "remote" for c in profile.get("locations") or [])
    search["remote_only"] = work == ["remote"]


def city_rank(job: dict, cities: list) -> int:
    """0 for your first city, 1 for the second... Jobs elsewhere (including remote) come after them."""
    return next((i for i, c in enumerate(cities) if has_word(job.get("location") or "", c)), len(cities))


def skill_score(job: dict, skills: list) -> float:
    """Share of your skills the job mentions. Mentioning five or more counts as a full match."""
    text = job["title"] + " " + job["description"]
    return round(min(1.0, sum(has_word(text, s) for s in skills) / max(1, min(5, len(skills)))), 2)


YEARS = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*(\d{1,2})\s*\+?\s*)?(?:years?|yrs?)\b", re.I)


def required_years(description: str):
    """(minimum, maximum or None) years of experience the job asks for, or None if it does not say."""
    best = None
    for m in YEARS.finditer(description):
        around = description[max(0, m.start() - 40): m.end() + 60].lower()
        low, high = int(m.group(1)), int(m.group(2)) if m.group(2) else None
        if "experience" in around and low <= 30 and (best is None or low > best[0]):
            best = (low, high)  # the largest requirement is usually the overall one
    return best


def experience_problem(description: str, mine):
    """Why your experience does not suit the job, or None."""
    need = required_years(description) if mine is not None else None
    if not need:
        return None
    low, high = need
    if low > mine:
        return "needs more experience"
    if high is not None and high + 5 < mine:
        return "meant for much less experience"
    return None

"""Matching agent: cheap keyword score first, then an LLM fit score for survivors."""
import json
import re

from .discover import has_word

SYSTEM = ("You are a senior technical recruiter screening for a Solution Architect. "
          "Be strict and honest. Score how well the candidate fits the job, 0-100.")

STRINGS = {"type": "array", "items": {"type": "string"}}
FIT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["fit_score", "reasons", "gaps", "keywords"],
    "properties": {"fit_score": {"type": "integer"}, "reasons": STRINGS, "gaps": STRINGS, "keywords": STRINGS},
}

# Shorter spellings that job descriptions use for skills in the master resume.
ALIASES = {".net core": [".net", "asp.net core"], "azure kubernetes service (aks)": ["aks"],
           "restful apis": ["rest api", "rest apis", "restful"], "microservices": ["microservice"],
           "azure active directory": ["azure ad", "entra id"], "ci/cd": ["continuous integration"],
           "sql server 2008+": ["sql server", "sql"], "cloud-native": ["azure", "cloud"]}


def resume_terms(master: dict) -> set:
    return {t.lower() for group in master["skills"].values() for t in group}


def keyword_score(job: dict, master: dict) -> float:
    text = job["title"] + " " + job["description"]
    hits = 0
    for term in resume_terms(master):
        variants = [term, re.sub(r"\s*\(.*?\)", "", term)] + ALIASES.get(term, [])
        hits += any(has_word(text, v) for v in variants)
    return round(min(1.0, hits / 20), 2)  # ~1.0 = very strong overlap


def llm_fit(llm, job: dict, master: dict) -> dict:
    prompt = f"""TASK: FIT
JOB TITLE: {job['title']} at {job['company']} ({job['location']})
JOB DESCRIPTION:
{job['description'][:15000]}

CANDIDATE MASTER RESUME (JSON):
{json.dumps(master, ensure_ascii=False)}

The candidate lives in Noida, India. A job they cannot legally or practically take from there scores below 50.
Give fit_score (0-100), reasons and gaps as short sentences, and keywords: up to 15 exact skill words or
phrases from the job description that the candidate's resume genuinely supports."""
    fit = llm.json(SYSTEM, prompt, FIT_SCHEMA)
    fit["fit_score"] = max(0, min(100, fit["fit_score"]))
    return fit

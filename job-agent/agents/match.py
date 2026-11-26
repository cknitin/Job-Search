"""Matching agent: cheap keyword score first, then an LLM fit score for survivors."""
import json
import re

SYSTEM = ("You are a senior technical recruiter screening for a Solution Architect. "
          "Be strict and honest. Score how well the candidate fits the job, 0-100.")


def resume_terms(master: dict) -> set:
    terms = set()
    for group in master["skills"].values():
        terms.update(t.lower() for t in group)
    return terms


def keyword_score(job: dict, master: dict) -> float:
    text = job["description"].lower() + " " + job["title"].lower()
    terms = resume_terms(master)
    hits = [t for t in terms if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text)]
    return round(len(hits) / max(8, len(terms) * 0.4), 2)  # normalised; ~1.0 = very strong overlap


def llm_fit(llm, job: dict, master: dict) -> dict:
    prompt = f"""TASK: FIT
JOB TITLE: {job['title']} at {job['company']} ({job['location']})
JOB DESCRIPTION:
{job['description'][:6000]}

CANDIDATE MASTER RESUME (JSON):
{json.dumps(master)[:6000]}

Return JSON: {{"fit_score": int 0-100, "reasons": [str], "gaps": [str],
"keywords": [up to 15 exact ATS keywords/phrases from the JD the candidate genuinely has]}}"""
    return llm.json(SYSTEM, prompt, 800)

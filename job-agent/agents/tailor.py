"""Tailoring agent: selects/rephrases master-resume facts for one JD and renders ATS-safe documents.

ATS rules enforced by the renderer: single column, no tables/text boxes/images/headers-footers,
standard section names, plain bullets, standard fonts, contact info in the body.
"""
import json
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .discover import has_word

SYSTEM = ("You tailor resumes and write cover letters. HARD RULE: never invent employers, titles, dates, "
          "metrics, team sizes, certifications or skills. You may only select, reorder and rephrase facts "
          "already in the master resume, mirroring the job description's wording where truthful. "
          "If the job asks for something the resume does not show, leave it out.")

STRINGS = {"type": "array", "items": {"type": "string"}}


def _obj(**props):
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


PICKS = {"type": "array", "items": _obj(index={"type": "integer"},
                                        bullets={"type": "array", "items": {"type": "integer"}})}
PLAN_SCHEMA = _obj(headline={"type": "string"}, summary={"type": "string"}, skills_order=STRINGS,
                   experience=PICKS, projects=PICKS,
                   rewrites={"type": "array", "items": _obj(ref={"type": "string"}, text={"type": "string"})},
                   cover_letter_paragraphs=STRINGS)

SKILL_LABELS = {"cloud_architecture": "Cloud & Azure", "languages": "Languages & Frameworks",
                "architecture": "Architecture", "security": "Security", "practices": "Engineering Practices",
                "tools": "Tools", "leadership": "Leadership"}


def plan(llm, job, master, keywords) -> dict:
    prompt = f"""TASK: TAILOR
JOB: {job['title']} at {job['company']} ({job['location']})
JOB DESCRIPTION:
{job['description'][:15000]}

TARGET KEYWORDS: {keywords}
MASTER RESUME (JSON): {json.dumps(master, ensure_ascii=False)}

Indexes below are 0-based positions in the master resume.
- headline: one line aimed at this role.
- summary: 3-4 sentences, using target keywords only where truthful.
- skills_order: skill group names, most relevant first.
- experience: for every employer, its bullet indexes, most relevant first (up to 8 for the current role).
- projects: every project, most relevant project first, with its bullet indexes (up to 5).
- rewrites: optional rephrasings. ref is "e<employer>.<bullet>" or "p<project>.<bullet>". Keep every number
  exactly as in the original bullet.
- cover_letter_paragraphs: 4 complete paragraphs, 250-350 words in total, in the first person:
  (1) the role, the company and why the candidate suits it; (2) the most relevant achievement with its
  numbers; (3) how other experience meets the job's main requirements; (4) a short close asking for a
  conversation. Refer to specifics from the job description. No greeting, no sign-off, no placeholders
  in brackets, no cliches."""
    result = llm.json(SYSTEM, prompt, PLAN_SCHEMA)
    words = len(" ".join(result["cover_letter_paragraphs"]).split())
    if llm.provider != "mock" and words < 200:
        result = llm.json(SYSTEM, prompt + f"\n\nThe cover letter must be 250-350 words, not {words}.", PLAN_SCHEMA)
    return result


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")))


def unverified_numbers(text: str, master: dict, job: dict) -> set:
    """Numbers in AI-written text that appear in neither the resume nor the job description."""
    return _numbers(text) - _numbers(json.dumps(master, ensure_ascii=False) + " " + job["description"])


def _select(items: list, picks: list, reorder: bool):
    """Yield (index, item, bullet indexes) honouring the AI's choices but never dropping an item."""
    chosen = {p["index"]: p["bullets"] for p in picks if 0 <= p["index"] < len(items)}
    order = list(chosen) if reorder else []
    order += [i for i in range(len(items)) if i not in order]
    for i in order:
        n = len(items[i]["bullets"])
        idxs = list(dict.fromkeys(b for b in chosen.get(i, []) if 0 <= b < n))
        yield i, items[i], idxs or list(range(n))


def _new_document():
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.6)
        s.left_margin = s.right_margin = Inches(0.7)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    st.paragraph_format.space_after = Pt(2)
    return doc


def _para(doc, text="", bold=False, italic=False, size=None, color=None, after=None, before=None, style=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    return p


def _heading(doc, text):
    p = _para(doc, text.upper(), bold=True, size=11.5, color="1F3864", before=9, after=4)
    p.paragraph_format.keep_with_next = True
    border, bottom = OxmlElement("w:pBdr"), OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "1F3864")):
        bottom.set(qn(f"w:{k}"), v)
    border.append(bottom)
    p._p.get_or_add_pPr().append(border)


def _contact(cand):
    return " | ".join(x for x in [cand["email"], cand["phone"], cand["location"], cand["linkedin"]] if x)


def render(plan_: dict, master: dict, cand: dict, path: Path, job: dict):
    doc = _new_document()
    rewrites = {r["ref"]: r["text"] for r in plan_.get("rewrites", [])}

    def bullet(kind, i, b, original):
        text = rewrites.get(f"{kind}{i}.{b}", original).strip()
        if _numbers(text) != _numbers(original):  # a rewrite that changes figures is rejected
            text = original
        _para(doc, text, style="List Bullet", after=1)

    summary = (plan_.get("summary") or "").strip()
    if not summary or unverified_numbers(summary, master, {"description": ""}):
        summary = " ".join(master["summary"].split())

    _para(doc, cand["name"].upper(), bold=True, size=18, color="1F3864", after=0)
    _para(doc, plan_.get("headline") or master["headline"], bold=True, size=11, after=1)
    _para(doc, _contact(cand), size=9.5)

    _heading(doc, "Professional Summary")
    _para(doc, summary)

    _heading(doc, "Skills")
    order = [g for g in plan_.get("skills_order", []) if g in master["skills"]]
    order += [g for g in master["skills"] if g not in order]
    for g in order:
        p = _para(doc, f"{SKILL_LABELS.get(g, g.replace('_', ' ').title())}: ", bold=True, after=1)
        p.add_run(", ".join(master["skills"][g]))

    _heading(doc, "Professional Experience")
    for i, exp, idxs in _select(master["experience"], plan_.get("experience", []), reorder=False):
        _para(doc, f"{exp['title']}, {exp['company']}", bold=True, before=4, after=0)
        _para(doc, f"{exp['location']} | {exp['start']} – {exp['end']}", italic=True, size=9.5)
        for b in idxs:
            bullet("e", i, b, exp["bullets"][b])

    if master.get("projects"):
        _heading(doc, "Key Projects")
        for i, pr, idxs in _select(master["projects"], plan_.get("projects", []), reorder=True):
            _para(doc, f"{pr['name']} – {pr['domain']}", bold=True, before=4, after=0)
            _para(doc, f"Technologies: {pr['technologies']}", italic=True, size=9.5)
            for b in idxs:
                bullet("p", i, b, pr["bullets"][b])

    _heading(doc, "Education")
    for ed in master["education"]:
        _para(doc, f"{ed['degree']}, {ed['school']} ({ed['result']})", after=1)
    if master.get("certifications"):
        _heading(doc, "Certifications")
        for c in master["certifications"]:
            _para(doc, c, style="List Bullet", after=1)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def cover_letter(plan_: dict, cand: dict, job: dict) -> str:
    paragraphs = [p.strip() for p in plan_.get("cover_letter_paragraphs", []) if p.strip()]
    today = date.today()
    parts = [f"{today.day} {today:%B %Y}",
             f"Application for {job['title']} – {job['company']}",
             "Dear Hiring Team,", *paragraphs,
             "\n".join(x for x in ["Kind regards,", cand["name"], cand["phone"], cand["email"], cand["linkedin"]] if x)]
    return "\n\n".join(parts) + "\n"


def render_letter(text: str, path: Path):
    doc = _new_document()
    for block in text.strip().split("\n\n"):
        _para(doc, block, size=11, after=9)
    doc.save(path)


def docx_text(path: Path) -> str:
    return "\n".join(p.text for p in Document(path).paragraphs)


def ats_check(path: Path, keywords: list) -> dict:
    """Simulates ATS parsing: plain-text extraction + keyword coverage."""
    text = docx_text(path).lower()
    found = [k for k in keywords if has_word(text, k)]
    missing = [k for k in keywords if k not in found]
    sections = all(s in text for s in ["professional summary", "skills", "professional experience", "education"])
    return {"coverage": round(len(found) / max(1, len(keywords)), 2), "missing": missing, "sections_ok": sections}


def job_details(job: dict, fit: dict = None, ats: dict = None, warnings: list = None) -> str:
    """Human-readable record of one job: where to apply, how you match, and the full description."""
    lines = [f"Job title : {job['title']}", f"Company   : {job['company']}",
             f"Location  : {job['location'] or 'not stated'}", f"Posted    : {job['posted'][:10] or 'not stated'}",
             f"Source    : {job['source']}", f"Apply link: {job['url'] or 'not provided'}"]
    if "kw" in job:
        lines.append(f"Skill keyword score: {int(job['kw'] * 100)}/100")
    if fit:
        lines.append(f"AI fit score       : {fit['fit_score']}/100")
        for label, key in (("Why you match", "reasons"), ("Gaps to prepare for", "gaps"), ("Keywords", "keywords")):
            lines += ["", f"{label}:"] + [f"  - {x}" for x in fit.get(key, [])]
    if ats:
        lines += ["", f"Resume keyword coverage: {int(ats['coverage'] * 100)}%",
                  f"Keywords missing from resume: {', '.join(ats['missing']) or 'none'}"]
    if warnings:
        lines += ["", "CHECK BEFORE SENDING:"] + [f"  ! {w}" for w in warnings]
    if job.get("partial_description"):
        lines += ["", "NOTE: this source gives only the start of the description. Open the apply link,",
                  "copy the full text into jobs_inbox/ and run the agent again for a better resume."]
    lines += ["", "=" * 70, "FULL JOB DESCRIPTION", "=" * 70, "", job["description"] or "(none provided)"]
    return "\n".join(lines) + "\n"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40].strip("-")

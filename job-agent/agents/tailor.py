"""Tailoring agent: selects/rephrases master-resume facts for one JD and renders an ATS-safe .docx.

ATS rules enforced by the renderer: single column, no tables/text boxes/images/headers-footers,
standard section names, plain bullets, standard fonts, contact info in the body.
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt

SYSTEM = ("You tailor resumes for ATS systems. HARD RULE: never invent employers, titles, dates, "
          "metrics, certifications or skills. You may only select, reorder and rephrase facts "
          "already in the master resume, mirroring the job description's wording where truthful.")


def plan(llm, job, master, keywords) -> dict:
    prompt = f"""TASK: TAILOR
JOB: {job['title']} at {job['company']}
JD: {job['description'][:6000]}
TARGET KEYWORDS: {keywords}
MASTER RESUME: {json.dumps(master)[:7000]}

Return JSON:
{{"headline": str, "summary": "3 lines max, uses target keywords truthfully",
 "skills_order": [skill group names, most relevant first],
 "experience": [{{"index": int, "bullets": [bullet indexes, most relevant first, max 6]}}],
 "rewrites": {{"<exp_index>.<bullet_index>": "rephrased bullet using JD wording, same facts"}},
 "cover_letter": "150-220 words, specific to this company, no clichés"}}"""
    return llm.json(SYSTEM, prompt, 3000)


def render(plan_: dict, master: dict, cand: dict, path: Path):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)

    def heading(text):
        p = doc.add_paragraph()
        r = p.add_run(text.upper())
        r.bold, r.font.size = True, Pt(12)

    name = doc.add_paragraph()
    r = name.add_run(cand["name"])
    r.bold, r.font.size = True, Pt(16)
    doc.add_paragraph(plan_.get("headline") or master["headline"])
    doc.add_paragraph(" | ".join(x for x in [cand["email"], cand["phone"], cand["location"], cand["linkedin"]] if x))

    heading("Professional Summary")
    doc.add_paragraph(plan_.get("summary") or master["summary"].strip())

    heading("Skills")
    order = [g for g in plan_.get("skills_order", []) if g in master["skills"]]
    order += [g for g in master["skills"] if g not in order]
    for g in order:
        label = {"cloud_architecture": "Cloud & Azure", "languages": "Languages & Frameworks"}.get(g, g.replace("_", " ").title())
        doc.add_paragraph(f"{label}: {', '.join(master['skills'][g])}")

    heading("Professional Experience")
    rewrites = plan_.get("rewrites", {})
    chosen = {e["index"]: e["bullets"] for e in plan_.get("experience", [])}
    for i, exp in enumerate(master["experience"]):
        p = doc.add_paragraph()
        p.add_run(f"{exp['title']}, {exp['company']}").bold = True
        doc.add_paragraph(f"{exp['location']} | {exp['start']} – {exp['end']}")
        idxs = [b for b in chosen.get(i, range(len(exp["bullets"]))) if 0 <= b < len(exp["bullets"])]
        for b in idxs:
            doc.add_paragraph(rewrites.get(f"{i}.{b}", exp["bullets"][b]), style="List Bullet")

    heading("Education")
    for ed in master["education"]:
        doc.add_paragraph(f"{ed['degree']}, {ed['school']}, {ed['year']}")
    if master.get("certifications"):
        heading("Certifications")
        for c in master["certifications"]:
            doc.add_paragraph(c, style="List Bullet")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def docx_text(path: Path) -> str:
    return "\n".join(p.text for p in Document(path).paragraphs)


def ats_check(path: Path, keywords: list) -> dict:
    """Simulates ATS parsing: plain-text extraction + keyword coverage."""
    text = docx_text(path).lower()
    found = [k for k in keywords if re.search(r"(?<![a-z0-9])" + re.escape(k.lower()) + r"(?![a-z0-9])", text)]
    missing = [k for k in keywords if k not in found]
    sections = all(s in text for s in ["professional summary", "skills", "professional experience", "education"])
    return {"coverage": round(len(found) / max(1, len(keywords)), 2), "missing": missing, "sections_ok": sections}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

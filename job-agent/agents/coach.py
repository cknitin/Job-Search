"""Coaching features: follow-up reminders, a skill gap report and interview preparation."""
import json
from datetime import date
from pathlib import Path

from .discover import has_word, inbox
from .report import _kept

FOLLOW_UP_DAYS = 7
APPLIED = ("submitted", "submitted-by-user")

# Skills that architect job descriptions often ask for. Add any you want to track.
SKILLS = {
    "AWS": ["aws", "amazon web services"], "Google Cloud": ["gcp", "google cloud"], "Azure": ["azure"],
    "Kubernetes": ["kubernetes", "aks", "eks"], "Docker": ["docker"], "Terraform": ["terraform"], "Bicep": ["bicep"],
    "Databricks": ["databricks"], "Snowflake": ["snowflake"], "PostgreSQL": ["postgresql", "postgres"],
    "Oracle": ["oracle"], "MongoDB": ["mongodb"], "Cosmos DB": ["cosmos db", "cosmosdb"], "Redis": ["redis"],
    "SQL Server": ["sql server"], "Kafka": ["kafka"], "RabbitMQ": ["rabbitmq"], "Elasticsearch": ["elasticsearch", "opensearch"],
    "Java": ["java"], "Python": ["python"], "Spring Boot": ["spring boot"], "Node.js": ["node.js", "nodejs"],
    ".NET": [".net", "asp.net"], "React": ["react"], "Angular": ["angular"], "GraphQL": ["graphql"], "gRPC": ["grpc"],
    "Generative AI": ["generative ai", "genai", "llm", "llms"], "Machine Learning": ["machine learning"],
    "TOGAF": ["togaf"], "Microservices": ["microservices", "microservice"], "Event-driven": ["event-driven", "event driven"],
    "GitHub Actions": ["github actions"], "Jenkins": ["jenkins"], "Observability": ["observability", "prometheus", "grafana", "datadog"],
    "Power BI": ["power bi"], "Data Lake": ["data lake", "lakehouse"],
}


# ---------- follow-ups ----------
def _followed_file(root: Path) -> Path:
    return root / "data" / "followups.json"


def followed(root: Path) -> dict:
    try:
        return json.loads(_followed_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mark_followed(root: Path, job_id: str):
    done = followed(root)
    done[job_id] = date.today().isoformat()
    _followed_file(root).parent.mkdir(exist_ok=True)
    _followed_file(root).write_text(json.dumps(done), encoding="utf-8")


def follow_ups(root: Path, jobs: list, cand: dict, today: date = None) -> list:
    """Applications with no news after FOLLOW_UP_DAYS days, each with a draft message."""
    today = today or date.today()
    excel = root / "data" / "job_applications.xlsx"
    try:  # the Stage you set in Excel: anything other than 'Applied' means you have heard back
        stages = {k: v.get("Stage") for k, v in _kept(excel).items()} if excel.exists() else {}
    except PermissionError:
        stages = {}
    done, out = followed(root), []
    for j in jobs:
        if j["status"] not in APPLIED or not j["applied_on"] or j["id"] in done:
            continue
        if stages.get(j["id"]) not in (None, "", "Applied"):
            continue
        applied = date.fromisoformat(j["applied_on"])
        days = (today - applied).days
        if days < FOLLOW_UP_DAYS:
            continue
        message = (f"Subject: Following up: {j['title']} application\n\nHello,\n\n"
                   f"I applied for the {j['title']} role at {j['company']} on {applied.day} {applied:%B %Y} and wanted to "
                   f"check on its status. I remain very interested and would be glad to share more about my experience "
                   f"or answer any questions.\n\nThank you for your time.\n\nKind regards,\n{cand['name']}\n"
                   f"{cand['phone']}\n{cand['email']}")
        out.append({**j, "days": days, "message": message})
    return sorted(out, key=lambda j: -j["days"])


# ---------- skill gaps ----------
def descriptions(root: Path, jobs: list) -> dict:
    """Every job description on disk, keyed by company and title so one job counts once."""
    found = {}

    def add(job):
        if job.get("description") and job.get("source") != "demo":
            found[(job.get("company", "").lower(), job.get("title", "").lower())] = f"{job['title']} {job['description']}"

    for j in jobs:
        f = Path(j.get("folder") or "") / "job.json"
        if j.get("folder") and f.is_file():
            add(json.loads(f.read_text(encoding="utf-8")))
    for j in inbox(root / "jobs_inbox"):
        add(j)
    results = root / "output" / "_found" / "found.json"
    if results.is_file():
        for j in json.loads(results.read_text(encoding="utf-8")):
            add(j)
    return found


def skill_report(texts: list, master: dict) -> dict:
    """How many of your target jobs mention each skill, split by whether your resume shows it."""
    resume = json.dumps(master, ensure_ascii=False)
    gaps, strengths = [], []
    for skill, words in SKILLS.items():
        count = sum(any(has_word(t, w) for w in words) for t in texts)
        if count:
            (strengths if any(has_word(resume, w) for w in words) else gaps).append((skill, count))
    key = lambda item: (-item[1], item[0])
    return {"jobs": len(texts), "gaps": sorted(gaps, key=key), "strengths": sorted(strengths, key=key)}


# ---------- interview preparation ----------
STRINGS = {"type": "array", "items": {"type": "string"}}
PREP_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["questions", "gap_plan", "ask_them"],
    "properties": {
        "questions": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["question", "answer_points", "source"],
            "properties": {"question": {"type": "string"}, "answer_points": STRINGS, "source": {"type": "string"}}}},
        "gap_plan": STRINGS, "ask_them": STRINGS},
}
SYSTEM = ("You coach a candidate for an architect interview. HARD RULE: never invent experience, projects or numbers. "
          "Answer points may use only facts from the resume and the candidate's notes. Where the candidate lacks a "
          "requirement, say how to answer honestly.")


def notes(root: Path, limit=150_000) -> str:
    """The candidate's own interview notes (the Questions folder, or numbered files in the project folder)."""
    base = root.parent
    folder = base / "Questions" if (base / "Questions").is_dir() else base
    text = ""
    for f in sorted(folder.glob("*.md")):
        if folder == base and not (f.name[:2].isdigit() or f.name.startswith("Case Study")):
            continue
        part = f"\n\n## {f.name}\n{f.read_text(encoding='utf-8', errors='replace')}"
        if len(text) + len(part) > limit:
            print(f"    Notes are long: stopped before {f.name}")
            break
        text += part
    return text


def prepare_interview(llm, root: Path, job: dict, master: dict, folder: Path) -> Path:
    fit = job.get("fit") or {}
    prompt = f"""TASK: INTERVIEW
JOB: {job['title']} at {job['company']}
JOB DESCRIPTION:
{job['description'][:15000]}

KNOWN GAPS: {fit.get('gaps', [])}
RESUME (JSON): {json.dumps(master, ensure_ascii=False)}
CANDIDATE'S OWN NOTES:
{notes(root)}

Give: 12 likely questions, each with 3-5 short answer points and the source (resume, or the note file name,
or "gap"); a short plan to prepare for each important gap; and 5 good questions to ask the interviewer."""
    result = llm.json(SYSTEM, prompt, PREP_SCHEMA)
    lines = [f"INTERVIEW PREPARATION: {job['title']} at {job['company']}",
             "Check every point is true before you use it.", ""]
    for n, q in enumerate(result["questions"], 1):
        lines += [f"{n}. {q['question']}", *[f"   - {p}" for p in q["answer_points"]], f"   (from: {q['source']})", ""]
    lines += ["PREPARE FOR YOUR GAPS", *[f"- {g}" for g in result["gap_plan"]], "",
              "QUESTIONS TO ASK THEM", *[f"- {a}" for a in result["ask_them"]]]
    path = folder / "interview_prep.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

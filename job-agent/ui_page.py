"""The web page shown by ui.py: a dashboard, one tab per job portal, your jobs and settings."""
import json
from html import escape
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

import learn
from agents.report import STATUS, _site as site_of

TABS = [("home", "🏠 Home"), ("linkedin", "LinkedIn"), ("naukri", "Naukri"), ("indeed", "Indeed"),
        ("company", "Company sites"), ("results", "📊 Results"), ("jobs", "📋 My jobs"), ("grow", "🎯 Grow"), ("learn", "📚 Learn"), ("settings", "⚙️ Settings")]
PORTALS = {
    "linkedin": {"name": "LinkedIn", "color": "#0a66c2", "login": "https://www.linkedin.com/login",
                 "example": "https://www.linkedin.com/jobs/view/..."},
    "naukri": {"name": "Naukri", "color": "#275df5", "login": "https://www.naukri.com/nlogin/login",
               "example": "https://www.naukri.com/job-listings-..."},
    "indeed": {"name": "Indeed", "color": "#2557a7", "login": "https://secure.indeed.com/auth",
               "example": "https://in.indeed.com/viewjob?jk=..."},
}
DONE = ("submitted", "submitted-by-user")
COMMANDS = {"inbox": "Create documents", "find": "Search company sites", "hunt": "Search and create documents",
            "apply": "Apply to ready jobs", "all": "Search, create and apply", "export": "Update Excel tracker", "prep": "Interview preparation"}


def safe_url(url):
    return url if urlsplit(url or "").scheme in ("http", "https") else ""


def link(url, label, css="btn"):
    return f'<a class="{css}" href="{escape(url)}" target="_blank" rel="noopener noreferrer">{label}</a>'


class Page:
    def __init__(self, ctx):
        self.c = ctx

    def form(self, action, tab, inner, hidden=None, confirm="", css="inline"):
        fields = {"token": self.c["token"], "tab": tab, **(hidden or {})}
        inputs = "".join(f'<input type="hidden" name="{k}" value="{escape(str(v))}">' for k, v in fields.items())
        ask = f' onsubmit="return confirm({escape(json.dumps(confirm))})"' if confirm else ""
        return f'<form method="post" action="/{action}" class="{css}"{ask}>{inputs}{inner}</form>'

    def button(self, action, tab, label, hidden=None, confirm="", css=""):
        return self.form(action, tab, f'<button class="{css}">{label}</button>', hidden, confirm)

    # ---------- pieces ----------
    def job_card(self, r, tab):
        files = self.c["files"](r)
        docs = "".join(link(f"/file?id={quote_plus(r['id'])}&kind={k}", label, "chip")
                       for k, label in (("resume", "📄 Resume"), ("letter", "✉️ Cover letter"),
                                        ("lettertext", "Letter text"), ("details", "ℹ️ Details"), ("prep", "🎤 Interview prep")) if k in files)
        url, status = safe_url(r["url"]), r["status"]
        applied = status in DONE
        actions = link(url, "View job ↗" if applied else "Open &amp; apply ↗") if url else ""
        if not applied:
            if r["apply_type"] in ("greenhouse", "lever") and files:
                actions += self.button("apply", tab, "Fill form", {"id": r["id"], "mode": "review"}, css="ghost")
                actions += self.button("apply", tab, "Auto apply", {"id": r["id"], "mode": "auto"},
                                       f"Submit your application to {r['company']} now? Read the resume and cover "
                                       "letter first. A submitted application cannot be undone.", "warn")
            actions += self.button("mark", tab, "✓ Mark applied", {"id": r["id"], "status": "submitted-by-user"},
                                   css="ok")
            actions += self.button("mark", tab, "Hide", {"id": r["id"], "status": "hidden"}, css="ghost")
        if "data" in files:
            actions += self.button("prep", tab, "Redo interview prep" if "prep" in files else "Prepare for interview",
                                   {"id": r["id"]}, "Create interview questions for this job? This uses API credit and "
                                   "sends your resume and interview notes to Anthropic.", "ghost")
        score = r["fit_score"]
        level = "none" if score is None else "high" if score >= 70 else "mid" if score >= 50 else "low"
        kind = "applied" if applied else "check" if status.startswith(("check", "error")) else "todo"
        text = f"{r['title']} {r['company']} {r['location']}".lower()
        return f"""<article class="job" data-kind="{kind}" data-text="{escape(text)}">
<div class="score {level}" title="AI fit score">{'–' if score is None else score}</div>
<div class="body"><h3>{escape(r['title'])}</h3>
<p class="muted">{escape(r['company'])} · {escape(r['location'] or 'location not stated')}</p>
<p><span class="pill">{escape(site_of(r))}</span> <span class="pill {kind}">{escape(STATUS.get(status, status[:80]))}</span>
{f'<span class="muted">on {escape(r["applied_on"])}</span>' if r['applied_on'] else ''}</p>
<div>{docs}</div><div class="actions">{actions}</div></div></article>"""

    def waiting(self, jobs, tab):
        if not jobs:
            return ""
        items = "".join(f"<li><b>{escape(j['title'])}</b> · {escape(j['company'])}</li>" for j in jobs)
        return (f'<div class="card soft"><h3>Saved, waiting for documents ({len(jobs)})</h3><ul>{items}</ul>'
                + self.button("task", tab, "Create documents now", {"name": "inbox"}) + "</div>")

    def add_form(self, tab, example, url_required):
        return self.form("add", tab, f"""
<button type="button" class="ghost" data-paste>📥 Paste copied job</button><span class="muted paste-note" aria-live="polite">
Copied with the Chrome extension? One click fills everything.</span>
<div class="row"><label>Job title<input name="title" required placeholder="Solution Architect"></label>
<label>Company<input name="company" required placeholder="Company name"></label>
<label>Location<input name="location" placeholder="Noida / Remote"></label></div>
<label>Job link<input name="url" {'required' if url_required else ''} placeholder="{escape(example)}"></label>
<label>Full job description<textarea name="description" rows="6"
 placeholder="Open the job, select the whole description, copy and paste it here"></textarea></label>
<button name="do" value="save">💾 Save job</button>
<button name="do" value="smart" class="ghost" formnovalidate title="Paste a whole job page into the description box">
✨ Smart save: AI reads a whole pasted page (uses API credit)</button>
<button name="do" value="applied" class="ghost">I already applied: just record it</button>""", css="stack")

    # ---------- tabs ----------
    def home(self):
        c, cfg = self.c, self.c["cfg"]
        jobs = c["jobs"]
        applied = [j for j in jobs if j["status"] in DONE]
        stats = [("To apply", sum(j["status"] not in DONE for j in jobs)), ("Saved, no documents", len(c["saved"])),
                 ("Applied today", sum(j["applied_on"] == c["today"] for j in applied)),
                 ("Applied in total", len(applied))]
        tiles = "".join(f'<div class="stat"><b>{n}</b><span>{label}</span></div>' for label, n in stats)

        todo = []
        if "example.com" in cfg["candidate"]["email"]:
            todo.append("Set your contact details in <code>config.local.yaml</code>.")
        if not c["has_key"]:
            todo.append('No Anthropic API key: search works, creating documents does not. <a href="#settings">Add it</a>.')
        if not c["adzuna"]:
            todo.append("No Adzuna keys: the automatic search will find very little for India (SETUP.md step 6.5).")
        setup = (f'<div class="card alert"><h3>Finish setting up</h3><ul>{"".join(f"<li>{t}</li>" for t in todo)}</ul></div>'
                 if todo else "")

        portals = "".join(f'<a class="portal" style="--c:{p["color"]}" href="#{key}"><b>{p["name"]}</b>'
                          f'<span>Search, add and track jobs →</span></a>' for key, p in PORTALS.items())

        mode = cfg["apply"]["mode"]
        how = {"auto": "SUBMITS applications without asking again", "pack": "only marks jobs for you to apply yourself",
               "review": "fills forms for you to check and submit"}.get(mode, mode)
        sure = (f"Apply mode is '{mode}': this {how}, for every ready job (up to {cfg['apply']['daily_limit']} a day). "
                "Read the documents first. Continue?")
        commands = [("inbox", "Create documents", "For the jobs you saved. Uses API credit.", "", ""),
                    ("find", "Search company sites", "Free, no AI. Results are under Company sites.", "", ""),
                    ("hunt", "Search and create documents", "Includes saved jobs. Uses API credit.", "", ""),
                    ("apply", "Apply to ready jobs", f"Mode '{escape(mode)}': {how}.", sure, "warn"),
                    ("all", "Search, create and apply", "hunt, then apply. Uses API credit.", sure, "warn"),
                    ("export", "Update Excel tracker", "Rebuild the CSV and Excel files.", "", "ghost")]
        cards = "".join(f'<div class="card"><h3>{title}</h3><p class="muted">{note}</p>'
                        f'{self.button("task", "home", f"python run.py {name}", {"name": name}, confirm, css)}</div>'
                        for name, title, note, confirm, css in commands)
        hero = ('<div class="hero"><h2>Land your next architect role, faster.</h2>'
                '<p>Search the big portals, tailor your resume and cover letter to each job, and track every application.</p>'
                '<a class="btn" href="#linkedin">Start searching →</a><a class="btn dark" href="#jobs">View my jobs</a></div>')
        return f"""{hero}<div class="stats">{tiles}</div>{setup}
<h2>Where do you want to look?</h2><div class="grid">{portals}</div>
<h2>How it works</h2><ol class="steps"><li><b>Find</b> a job in a portal tab</li><li><b>Paste</b> it and save</li>
<li><b>Create documents</b></li><li><b>Review</b>, apply, mark applied</li></ol>
<h2>Actions</h2><div class="grid">{cards}</div>"""

    def portal(self, key):
        search = self.c["cfg"]["search"]
        p, titles = PORTALS[key], search["titles"]
        skills, years = search.get("skills") or [".NET", "Azure"], search.get("experience")
        words = f"{titles[0]} {' '.join(skills[:2])}"  # a long list of words returns almost nothing
        city = next((c for c in search["locations"] if c.lower() not in ("remote", "india")), "India")
        chips = "".join(f'<button type="button" class="chip" data-fill="{key}-kw" data-value="{escape(t)} {escape(" ".join(skills[:2]))}">'
                        f'{escape(t)}</button>' for t in titles[:6])
        work = search.get("work") or []
        cities = search.get("preferred_cities") or [c for c in search["locations"] if c.lower() not in ("remote", "india")]
        places = "".join(f'<option value="{escape(c)}">' for c in cities)
        codes = ",".join(code for w, code in (("onsite", "1"), ("hybrid", "3"), ("remote", "2")) if w in work)
        combined = (f'<option value="{codes}" selected>My preference</option>' if len(work) > 1 else "")
        pick = lambda code: " selected" if codes == code else ""
        age = ('<label>Posted<select id="{k}-age"><option value="1">Last 24 hours</option><option value="3">Last 3 days'
               '</option><option value="7" selected>Last week</option><option value="30">Last month</option></select>'
               '</label>').format(k=key)
        if key == "linkedin":
            extra = f"""<label>Level<select id="linkedin-level"><option value="">Any</option><option value="4">Mid-Senior</option>
<option value="5">Director</option></select></label><label>Workplace<select id="linkedin-work"><option value="">Any</option>{combined}
<option value="1"{pick("1")}>On-site</option><option value="3"{pick("3")}>Hybrid</option><option value="2"{pick("2")}>Remote</option></select></label>
<label class="check"><input type="checkbox" id="linkedin-easy"> Easy Apply only</label>"""
        elif key == "naukri":
            extra = ('<label>Experience (years)<input id="naukri-exp" type="number" min="0" max="40" '
                     f'value="{years if years is not None else ""}" placeholder="17"></label>')
        else:
            extra = ('<label>Distance<select id="indeed-radius"><option value="">Default</option><option value="25">25 km'
                     '</option><option value="50">50 km</option></select></label><label class="check">'
                     '<input type="checkbox" id="indeed-new"> Newest first</label>')
        mine = [j for j in self.c["jobs"] if site_of(j) == p["name"]]
        cards = "".join(self.job_card(j, key) for j in mine) or f"<p class='empty'>No {p['name']} jobs yet.</p>"
        saved = [j for j in self.c["saved"] if site_of(j) == p["name"]]
        return f"""<div class="banner" style="--c:{p['color']}"><div><h2>{p['name']}</h2>
<p>Log in and apply in your own browser. The agent never sees your password.</p>
<p><a href="#settings" style="color:#fff">🧩 Copy jobs faster with the Chrome extension</a></p></div>
{link(p['login'], f"Log in to {p['name']} ↗", "btn light")}</div>
<div class="columns"><div class="card"><h3><span class="n">1</span> Search</h3><div class="stack">
<label>Keywords<input id="{key}-kw" value="{escape(words)}"></label><div class="chips">{chips}</div>
<div class="row"><label>Location<input id="{key}-loc" value="{escape(city)}" list="{key}-places"><datalist id="{key}-places">{places}</datalist></label>{age}{extra}</div>
<button type="button" class="big" style="background:{p['color']}" onclick="search('{key}')">🔍 Search {p['name']}</button></div></div>
<div class="card"><h3><span class="n">2</span> Add the job you like</h3>{self.add_form(key, p['example'], True)}</div></div>
{self.waiting(saved, key)}
<h2><span class="n">3</span> Your {p['name']} jobs</h2>{cards}"""

    def company(self):
        found = []
        for i, j in enumerate(self.c["found"]):
            if j["source"] == "inbox":
                continue
            url = safe_url(j["url"])
            use = (self.button("use", "company", "+ Add to my list", {"index": i}) if not j.get("partial_description")
                   else "<span class='muted'>Only part of the text. Open it and paste the full description below.</span>")
            found.append(f'<article class="job"><div class="score none" title="Skill match">{int(j["kw"] * 100)}</div>'
                         f'<div class="body"><h3>{escape(j["title"])}</h3><p class="muted">{escape(j["company"])} · '
                         f'{escape(j["location"])}</p><div class="actions">{link(url, "Open ↗") if url else ""}{use}</div>'
                         f'</div></article>')
        known = {p["name"] for p in PORTALS.values()}
        mine = "".join(self.job_card(j, "company") for j in self.c["jobs"] if site_of(j) not in known)
        saved = [j for j in self.c["saved"] if site_of(j) not in known]
        return f"""<div class="banner" style="--c:#0f766e"><div><h2>Company sites and other sources</h2>
<p>Automatic search (Adzuna, Remotive, Greenhouse, Lever), plus jobs from email or company websites.</p></div>
{self.button("task", "company", "🔍 Search now (free)", {"name": "find"}, css="light")}</div>
<h2>Search results</h2>{''.join(found) or "<p class='empty'>Nothing yet. Click Search now.</p>"}
<div class="card"><h3>Add a job from anywhere else</h3>{self.add_form("company", "https://company.com/careers/...", False)}</div>
{self.waiting(saved, "company")}
<h2>Your jobs from these sources</h2>{mine or "<p class='empty'>No jobs yet.</p>"}"""

    def results(self):
        runs, jobs = self.c["runs"], self.c["jobs"]
        outcome = ""
        for name, r in sorted(runs.items(), key=lambda item: -item[1]["order"]):
            badge = '<span class="pill applied">Finished</span>' if r["ok"] else '<span class="pill check">Failed</span>'
            problems = sum(line.lstrip().startswith(("x ", "!")) for line in r["log"].splitlines())
            if r["ok"] and problems:
                badge += f' <span class="pill check">{problems} warning(s)</span>'
            outcome += (f'<div class="card"><h3>{COMMANDS.get(name, escape(name))} <code>{escape(name)}</code></h3>'
                        f'<p>{badge} <span class="muted">{escape(r["when"])}</span></p>'
                        f'<pre class="out">{escape(r["log"]) or "(no output)"}</pre></div>')

        ready = [j for j in jobs if j["status"] not in DONE]
        ready_cards = "".join(self.job_card(j, "results") for j in ready)

        rows = "".join(f'<tr><td>{int(j["kw"] * 100)}</td><td>{escape(j["title"])}</td><td>{escape(j["company"])}</td>'
                       f'<td>{escape(j["location"])}</td><td>{link(safe_url(j["url"]), "View ↗", "chip") if safe_url(j["url"]) else ""}'
                       f'</td></tr>' for j in self.c["found"])
        found = (f'<div class="card scroll"><table><tr><th>Skill match</th><th>Job</th><th>Company</th><th>Location</th><th></th></tr>'
                 f'{rows}</table></div>') if rows else "<p class='empty'>No search results yet. Run find.</p>"

        low = ""
        for j in self.c["skipped"]:
            try:
                gaps = json.loads(j["notes"] or "{}").get("gaps") or []
            except (ValueError, AttributeError):
                gaps = []
            url = safe_url(j["url"])
            low += (f'<tr><td>{j["fit_score"]}</td><td>{escape(j["title"])}</td><td>{escape(j["company"])}</td>'
                    f'<td>{escape("; ".join(gaps[:3]))}</td><td>{link(url, "View ↗", "chip") if url else ""}</td></tr>')
        low = (f'<h2>Not prepared: fit score too low ({len(self.c["skipped"])})</h2><div class="card scroll"><table>'
               f'<tr><th>Fit</th><th>Job</th><th>Company</th><th>Main gaps</th><th></th></tr>{low}</table></div>') if low else ""

        per_day = {}
        for j in jobs:
            if j["status"] in DONE and j["applied_on"]:
                per_day.setdefault(j["applied_on"], []).append(j["company"])
        days = "".join(f'<tr><td>{escape(d)}</td><td>{len(c)}</td><td>{escape(", ".join(c))}</td></tr>'
                       for d, c in sorted(per_day.items(), reverse=True))
        applied = (f'<div class="card scroll"><table><tr><th>Date</th><th>Applied</th><th>Companies</th></tr>{days}</table></div>'
                   if days else "<p class='empty'>No applications recorded yet.</p>")

        return f"""<h2>Command results</h2>{outcome or "<p class='empty'>Run an action on the Home tab to see its result here.</p>"}
<h2>Ready for you to apply ({len(ready)})</h2>{ready_cards or "<p class='empty'>No jobs are waiting.</p>"}
<h2>Company search results ({len(self.c["found"])})</h2>{found}{low}
<h2>Applications by date</h2>{applied}<p><a class="btn ok" href="/excel">⬇ Download Excel tracker</a></p>"""

    def grow(self):
        follow = ""
        for j in self.c["followups"]:
            follow += (f'<div class="card"><h3>{escape(j["title"])}</h3><p class="muted pii">{escape(j["company"])} · applied '
                       f'{j["days"]} days ago</p><textarea rows="7" class="pii" aria-label="Follow-up message">'
                       f'{escape(j["message"])}</textarea><div class="actions">'
                       f'<button type="button" data-copy>📋 Copy message</button>'
                       f'{self.button("followed", "grow", "✓ I followed up", {"id": j["id"]}, css="ok")}</div></div>')
        s = self.c["skills"]

        def bars(items):
            return "".join(f'<div class="bar"><span>{escape(name)}</span><i style="width:{round(100 * n / s["jobs"])}%"></i>'
                           f'<b>{n}</b></div>' for name, n in items[:12])

        if s["jobs"]:
            report = (f'<p class="muted">Based on {s["jobs"]} job description(s) on this computer'
                      f'{". Add more jobs for a reliable picture" if s["jobs"] < 10 else ""}.</p>'
                      f'<div class="columns"><div class="card"><h3>Asked for, not on your resume</h3>'
                      f'{bars(s["gaps"]) or "<p class=muted>Nothing missing.</p>"}</div>'
                      f'<div class="card"><h3>Asked for, and you have it</h3>'
                      f'{bars(s["strengths"]) or "<p class=muted>No matches yet.</p>"}</div></div>')
        else:
            report = "<p class='empty'>Save or search some jobs to see what they ask for.</p>"
        o = self.c["outcomes"]
        tables = ""
        for name, rows in o["groups"]:
            body = "".join(f'<tr><td>{escape(k)}</td><td>{v["applied"]}</td><td>{v["responses"]}</td><td>{v["interviews"]}</td></tr>'
                           for k, v in rows)
            tables += (f'<div class="card scroll"><h3>{name}</h3><table><tr><th></th><th>Applied</th><th>Replies</th>'
                       f'<th>Interviews</th></tr>{body}</table></div>')
        if o["applied"]:
            few = " Too few applications to draw conclusions yet." if o["applied"] < 20 else ""
            learned = (f'<div class="stats"><div class="stat"><b>{o["per_ten"]}</b><span>Interviews per 10 applications</span></div>'
                       f'<div class="stat"><b>{o["applied"]}</b><span>Applications</span></div></div>'
                       f'<p class="muted">From the Stage you set in the Excel file.{few}</p><div class="grid">{tables}</div>')
        else:
            learned = "<p class='empty'>Appears once you have recorded applications. Set each one's Stage in the Excel file.</p>"

        options = "".join(f'<option data-title="{escape(j["title"])}" data-company="{escape(j["company"])}" '
                          f'data-url="{escape(safe_url(j["url"]))}">{escape(j["company"])}: {escape(j["title"])}</option>'
                          for j in self.c["jobs"] if j["status"] not in DONE)
        me = self.c["cfg"]["candidate"]
        referral = (f"""<div class="card stack" id="referral" data-me="{escape(me['name'])}" data-link="{escape(me['linkedin'])}">
<div class="row"><label>Job<select id="ref-job" class="pii">{options}</select></label>
<label>Your contact's first name<input id="ref-name" placeholder="Priya"></label></div>
<label>Message (edit before sending)<textarea id="ref-text" rows="7" class="pii"></textarea></label>
<div><button type="button" data-copy>📋 Copy message</button></div></div>""" if options
                    else "<p class='empty'>Add a job you have not applied to yet to draft a referral note.</p>")

        found = "".join(f'<tr><td>{j["score"]}</td><td>{escape(j["title"])}</td><td>{escape(j["site"])}</td>'
                        f'<td>{link(safe_url(j["url"]), "Open ↗", "chip")}</td></tr>' for j in self.c["alerts"][:40])
        alert_form = self.form("alert", "grow", '<input type="hidden" name="raw"><label>Saved alert email (.eml file)'
                               '<input type="file" accept=".eml,.html,.htm" data-alert></label>', css="stack")
        alerts = (f'<div class="card">{alert_form}<p class="muted">In Gmail: open the alert, ⋮ menu, Download message. '
                  'Links are listed, never opened automatically.</p></div>'
                  + (f'<div class="card scroll"><table><tr><th>Match</th><th>Job</th><th>Site</th><th></th></tr>{found}</table></div>'
                     if found else ""))

        return f"""<h2>What is working</h2>{learned}
<h2>Ask for a referral</h2>{referral}
<h2>Job alert import</h2>{alerts}
<h2>Follow up ({len(self.c["followups"])})</h2>
{follow or "<p class='empty'>Nothing due. Applications appear here 7 days after you apply, unless you set another Stage in Excel.</p>"}
<h2>Skill gap report</h2>{report}
<h2>Interview preparation</h2><p class="muted">Click <b>Prepare for interview</b> on any job that has documents, under
My jobs. It uses your resume and the notes in your Questions folder.</p>"""

    def jobs(self):
        cards = "".join(self.job_card(j, "jobs") for j in self.c["jobs"])
        return f"""<div class="toolbar"><input id="filter" placeholder="🔎 Search title, company or city" aria-label="Filter jobs">
<span class="filters"><button type="button" class="chip on" data-show="">All</button>
<button type="button" class="chip" data-show="todo">To apply</button>
<button type="button" class="chip" data-show="applied">Applied</button>
<button type="button" class="chip" data-show="check">Check</button></span>
<a class="btn ok" href="/excel">⬇ Download Excel tracker</a></div>
<p class="muted">File: data/job_applications.xlsx. "Fill form" and "Auto apply" work only for Greenhouse and Lever forms.
For LinkedIn, Naukri and Indeed, use "Open &amp; apply", upload the resume yourself, then "Mark applied".</p>
<div id="all-jobs">{cards or "<p class='empty'>No jobs yet. Start from a portal tab.</p>"}</div>
{self.waiting(self.c["saved"], "jobs")}"""

    def extension_card(self):
        return f"""<div class="card"><h3>🧩 Chrome extension: Job Agent Copier</h3>
<p class="muted">Hover a job on LinkedIn, Naukri or Indeed, copy it, then click <b>Paste copied job</b> here.</p>
<ol><li>In Chrome, open <code>chrome://extensions</code></li><li>Turn on <b>Developer mode</b> (top right)</li>
<li>Click <b>Load unpacked</b> and choose this folder:<br><code class="pii">{escape(str(Path(__file__).parent / 'chrome-extension'))}</code></li>
<li>Reload any job site tab that was already open</li></ol>
<p class="muted">Open a job before copying to get its full description. The extension acts only when you click and
sends nothing anywhere. These sites' terms restrict copying tools, LinkedIn's in particular, so use it sparingly.</p></div>"""

    def profile_card(self):
        saved, search = self.c["profile"], self.c["cfg"]["search"]
        field = lambda key: escape(", ".join(saved.get(key) or []))
        years = saved.get("experience")
        boxes = "".join(f'<label class="check"><input type="checkbox" name="work_{key}" value="yes"'
                        f'{" checked" if key in (saved.get("work") or []) else ""}> {label}</label>'
                        for key, label in (("remote", "Remote"), ("hybrid", "Hybrid"), ("onsite", "On-site")))
        inner = f"""<label>Your skills, separated by commas (most important first)<textarea name="skills" rows="3"
 placeholder=".NET Core, Azure, Microservices, C#, AKS">{field("skills")}</textarea></label>
<label>Years of experience<input name="experience" type="number" min="0" max="45" value="{'' if years is None else years}"
 placeholder="17"></label>
<label>Job titles<input name="titles" value="{field("titles")}" placeholder="{escape(", ".join(search["titles"][:3]))}"></label>
<label>Preferred cities, best first<input name="locations" value="{field("locations")}"
 placeholder="Noida, Gurugram, Delhi"></label><label>Work preference</label><div class="row">{boxes}</div>
<button>💾 Save search profile</button>"""
        return f"""<div class="card"><h3>🎯 Search profile</h3>{self.form("profile", "settings", inner, css="stack")}
<p class="muted">Used to search and rank jobs. The first two skills go into portal searches. Jobs asking for more
experience than yours, or for far less, are left out of the automatic search. It does not change your resume:
that comes from master_resume.yaml. Empty boxes use the defaults.</p></div>"""

    def settings(self):
        cand = self.c["cfg"]["candidate"]
        state = "✅ A key is set" if self.c["has_key"] else "❌ No key yet"
        key_form = self.form("key", "settings",
                             '<label>Anthropic API key<input type="password" name="key" autocomplete="off" '
                             'placeholder="Paste your key"></label><button>Use key</button>', css="stack")
        return f"""{self.profile_card()}<div class="columns"><div class="card"><h3>API key (this session only)</h3><p>{state}</p>{key_form}
<p class="muted">Kept in memory until you close the agent. It is not saved to disk.</p></div>
<div class="card"><h3>Your details on resumes</h3><p class="pii"><b>{escape(cand['name'])}</b><br>{escape(cand['email'])}<br>
{escape(cand['phone'])}<br>{escape(cand['location'])}<br>{escape(cand['linkedin'])}</p>
<p class="muted">Change them in <code>job-agent/config.local.yaml</code>. Your experience is in
<code>job-agent/master_resume.yaml</code>.</p></div></div>{self.extension_card()}"""


CSS = """
:root{--bg:#0b0b14;--card:rgba(255,255,255,.055);--solid:#15152252;--text:#f2f1fa;--muted:#a3a1bd;--line:rgba(255,255,255,.11);
--brand:#8b5cf6;--pink:#ec4899;--lime:#c6f432;--field:rgba(255,255,255,.06);--grad:linear-gradient(110deg,#7c3aed,#db2777 55%,#f97316);
--head:"Bricolage Grotesque","Segoe UI",sans-serif;--bodyfont:"Inter","Segoe UI",Arial,sans-serif;color-scheme:dark}
:root[data-theme=light]{--bg:#f6f5fc;--card:rgba(255,255,255,.82);--text:#17152b;--muted:#625f7e;--line:#e4e1f2;
--field:#fff;color-scheme:light}
*{box-sizing:border-box} body{margin:0;min-height:100vh;color:var(--text);font:15px/1.6 var(--bodyfont);
background:radial-gradient(900px 500px at 8% -8%,#7c3aed38,transparent 60%),radial-gradient(800px 500px at 100% 0,#ec489930,transparent 60%),
radial-gradient(700px 600px at 50% 110%,#06b6d424,transparent 60%),var(--bg);background-attachment:fixed}
h1,h2,h3,.stat b,.score,.logo{font-family:var(--head);font-weight:800;letter-spacing:-.02em;font-optical-sizing:auto}
body{-webkit-font-smoothing:antialiased;font-feature-settings:"cv11","ss01"}
.top{max-width:1120px;margin:auto;padding:18px 20px 0;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:12px} .logo i{font-style:normal;width:44px;height:44px;border-radius:14px;background:var(--grad);
display:grid;place-items:center;font-size:22px;box-shadow:0 8px 24px #db277755} .logo h1{margin:0;font-size:22px;line-height:1.1}
.who{margin:0;color:var(--muted);font:13px var(--bodyfont)} .tools{display:flex;gap:8px}
header{position:sticky;top:0;z-index:5;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);
background:color-mix(in srgb,var(--bg) 72%,transparent);border-bottom:1px solid var(--line);padding-bottom:12px}
nav{max-width:1120px;margin:12px auto 0;padding:0 20px;display:flex;flex-wrap:wrap;gap:6px}
nav a{color:var(--muted);text-decoration:none;padding:7px 15px;border-radius:99px;font-weight:600;font-size:14px;border:1px solid transparent;
transition:.2s} nav a:hover{color:var(--text);border-color:var(--line)}
nav a.active{background:var(--text);color:var(--bg)} nav a span{background:var(--grad);color:#fff;border-radius:99px;padding:0 7px;margin-left:6px;font-size:11px}
main{max-width:1120px;margin:auto;padding:22px 20px 60px} h2{font-size:21px;margin:30px 0 12px} h3{margin:0 0 8px;font-size:17px}
.js .tab{display:none} .js .tab.active{display:block;animation:rise .35s ease}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card,.job,.stat{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:20px;backdrop-filter:blur(14px);
box-shadow:0 10px 30px #0000001f}
.card{margin-bottom:14px} .alert{border-color:#f59e0b66;background:#f59e0b17}
.hero{border-radius:28px;padding:38px 34px;background:var(--grad);color:#fff;position:relative;overflow:hidden;margin-bottom:14px}
.hero:after{content:"";position:absolute;right:-70px;top:-90px;width:300px;height:300px;border-radius:50%;background:#ffffff24}
.hero h2{margin:0;font-size:clamp(28px,5vw,46px);line-height:1.08;max-width:620px} .hero p{margin:12px 0 20px;max-width:520px;opacity:.93}
.hero .btn{position:relative;z-index:1;margin-right:8px;background:#fff;color:#1a1033} .hero .btn.dark{background:#1a103366;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px} .grid .card{margin:0;transition:.2s}
.grid .card:hover,.job:hover{border-color:#8b5cf680;transform:translateY(-2px)}
.columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:14px;align-items:start;margin-top:14px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:14px}
.stat b{display:block;font-size:44px;line-height:1.05;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.stat span{color:var(--muted);font-weight:600;font-size:13px}
.portal{display:block;background:linear-gradient(135deg,var(--c),#111133);color:#fff;text-decoration:none;border-radius:22px;padding:26px;
min-height:130px;transition:.2s} .portal b{display:block;font:800 26px var(--head)} .portal span{opacity:.85}
.portal:hover{transform:translateY(-4px) rotate(-.4deg);box-shadow:0 18px 36px #00000045}
.steps{display:flex;flex-wrap:wrap;gap:10px;list-style:none;padding:0;counter-reset:s}
.steps li{counter-increment:s;background:var(--card);border:1px solid var(--line);border-radius:99px;padding:9px 18px}
.steps li:before{content:"0" counter(s) "  ";font:700 13px var(--head);color:var(--pink);white-space:pre}
.banner{background:linear-gradient(120deg,var(--c),#1b1240);color:#fff;border-radius:26px;padding:24px 26px;display:flex;
justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px} .banner h2{margin:0;font-size:30px} .banner p{margin:4px 0;opacity:.88}
.n{display:inline-block;width:27px;height:27px;line-height:27px;text-align:center;border-radius:9px;background:var(--grad);
color:#fff;font-size:13px;margin-right:8px}
.stack{display:flex;flex-direction:column;gap:12px;align-items:stretch} .row{display:flex;flex-wrap:wrap;gap:10px}
.row label{flex:1 1 130px} label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:var(--muted)}
label.check{flex-direction:row;align-items:center;gap:6px;padding-top:20px}
input,select,textarea{font:14px var(--bodyfont);color:var(--text);padding:11px 13px;border:1px solid var(--line);border-radius:13px;
background:var(--field);width:100%} option{background:#fff;color:#17152b} input[type=checkbox]{width:auto;accent-color:var(--brand)}
input:focus,select:focus,textarea:focus,button:focus-visible,a:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
button,.btn{font:700 14px var(--bodyfont);background:var(--grad);color:#fff;border:1px solid transparent;border-radius:99px;
padding:9px 18px;cursor:pointer;text-decoration:none;display:inline-block;transition:.18s}
button:hover,.btn:hover{transform:translateY(-1px);box-shadow:0 8px 22px #7c3aed55}
.big{font-size:16px;padding:13px} .ok{background:var(--lime);color:#17210a} .warn{background:#ea580c}
.ghost{background:transparent;color:var(--text);border-color:var(--line)} .light{background:#fff;color:#17152b}
.chip{display:inline-block;background:#8b5cf61f;color:var(--text);border:1px solid #8b5cf648;border-radius:99px;padding:4px 13px;
margin:0 6px 6px 0;font-size:13px;font-weight:600;text-decoration:none} .chip.on{background:var(--grad);border-color:transparent;color:#fff}
.chips{margin-bottom:-6px} .inline{display:inline}
.job{display:flex;gap:16px;margin-bottom:12px;transition:.2s} .job p{margin:2px 0 8px} .job h3{margin:0} .body{flex:1;min-width:0}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.score{flex:0 0 56px;height:56px;border-radius:18px;display:grid;place-items:center;font-weight:700;font-size:20px;
background:var(--field);border:1px solid var(--line);color:var(--muted)}
.score.high{background:var(--lime);color:#17210a;border:0} .score.mid{background:#fbbf24;color:#291c00;border:0}
.score.low{background:#fb7185;color:#2c0610;border:0}
.pill{display:inline-block;background:var(--field);border:1px solid var(--line);border-radius:99px;padding:1px 11px;font-size:12px;font-weight:700}
.pill.applied{background:#22c55e26;border-color:#22c55e66} .pill.todo{background:#8b5cf62b;border-color:#8b5cf673}
.pill.check{background:#f43f5e2b;border-color:#f43f5e73}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center} .toolbar input{flex:1 1 240px;width:auto}
.filters .chip{margin:0 4px 0 0;cursor:pointer}
.muted{color:var(--muted)} .empty{color:var(--muted);border:1.5px dashed var(--line);border-radius:22px;padding:24px;text-align:center}
.note{background:#8b5cf624;border:1px solid #8b5cf666;border-radius:16px;padding:11px 16px;margin-bottom:14px}
details{background:#08080f;color:#d9d7f0;border:1px solid var(--line);border-radius:18px;padding:12px 16px;margin-bottom:16px}
summary{cursor:pointer;font-weight:700}
pre{max-height:240px;overflow:auto;white-space:pre-wrap;margin:8px 0 0;font-size:13px}
pre.out{background:#08080f;color:#d9d7f0;border-radius:14px;padding:12px 14px}
.bar{display:grid;grid-template-columns:130px 1fr 28px;gap:10px;align-items:center;margin:7px 0;font-size:13px}
.bar i{height:10px;border-radius:99px;background:var(--grad);min-width:6px} .bar b{text-align:right}
code{background:#8b5cf626;border-radius:7px;padding:1px 7px;font-size:13px} .scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse} th,td{text-align:left;padding:9px 10px;border-top:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-size:12px;border-top:0}
.private .who,.private .pii,.private .job h3+p,.private .soft li,.private textarea.pii,.private td,.private pre{filter:blur(6px);user-select:none}
.private .alert{display:none}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media(max-width:480px){.columns{grid-template-columns:1fr}.hero{padding:26px 20px}header{position:static}}
"""

JS = r"""
const $ = id => document.getElementById(id);
const v = id => ($(id) ? $(id).value.trim() : '');
const slug = s => s.toLowerCase().replace(/\.net/g, 'dot net').replace(/c#/g, 'c sharp').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const go = url => window.open(url, '_blank', 'noopener');

const searches = {
  linkedin() {
    const q = new URLSearchParams({keywords: v('linkedin-kw'), location: v('linkedin-loc') || 'India',
                                   f_TPR: 'r' + v('linkedin-age') * 86400});
    if (v('linkedin-level')) q.set('f_E', v('linkedin-level'));
    if (v('linkedin-work')) q.set('f_WT', v('linkedin-work'));
    if ($('linkedin-easy').checked) q.set('f_AL', 'true');
    return 'https://www.linkedin.com/jobs/search/?' + q;
  },
  naukri() {
    const q = new URLSearchParams({k: v('naukri-kw'), jobAge: v('naukri-age')});
    let path = (slug(v('naukri-kw')) || 'architect') + '-jobs';
    if (v('naukri-loc')) { path += '-in-' + slug(v('naukri-loc')); q.set('l', v('naukri-loc')); }
    if (v('naukri-exp')) q.set('experience', v('naukri-exp'));
    return 'https://www.naukri.com/' + path + '?' + q;
  },
  indeed() {
    const q = new URLSearchParams({q: v('indeed-kw'), l: v('indeed-loc'), fromage: v('indeed-age')});
    if (v('indeed-radius')) q.set('radius', v('indeed-radius'));
    if ($('indeed-new').checked) q.set('sort', 'date');
    return 'https://in.indeed.com/jobs?' + q;
  }
};
const search = portal => go(searches[portal]());

// Look and privacy settings are remembered in this browser.
const root = document.documentElement;
const remember = (k, val) => { try { localStorage.setItem(k, val); } catch (e) {} };
const recall = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
if (recall('theme') === 'light') root.dataset.theme = 'light';
document.body.classList.toggle('private', recall('private') === 'yes');
$('theme').onclick = () => {
  const light = root.dataset.theme !== 'light';
  root.dataset.theme = light ? 'light' : 'dark';
  remember('theme', root.dataset.theme);
};
$('privacy').onclick = () => remember('private', document.body.classList.toggle('private') ? 'yes' : 'no');

function showTab() {
  const wanted = location.hash.slice(1);
  const tab = $('tab-' + wanted) ? wanted : 'home';
  document.querySelectorAll('.tab').forEach(e => e.classList.toggle('active', e.id === 'tab-' + tab));
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + tab));
  window.scrollTo(0, 0);
}
document.documentElement.classList.add('js');
window.addEventListener('hashchange', showTab);
showTab();

document.querySelectorAll('[data-fill]').forEach(b => b.onclick = () => { $(b.dataset.fill).value = b.dataset.value; });

// A job copied by the extension starts with "Title:" and has a --- line before the description.
function parseJob(text) {
  const clean = text.replace(/\r/g, '');
  const cut = clean.indexOf('\n---');
  if (!/^\s*Title:/i.test(clean) || cut < 0) return null;
  const head = clean.slice(0, cut);
  const field = name => (head.match(new RegExp('^\\s*' + name + ':[ \\t]*(.*)$', 'im')) || [])[1] || '';
  return {title: field('Title').trim(), company: field('Company').trim(), location: field('Location').trim(),
          url: field('URL').trim(), description: clean.slice(cut + 4).replace(/^-*\n/, '').trim()};
}
function fillForm(form, text) {
  const job = parseJob(text);
  const note = form.querySelector('.paste-note');
  if (!job) { note.textContent = 'The clipboard has no copied job. Copy one with the extension first.'; return false; }
  Object.entries(job).forEach(([name, value]) => { form.querySelector(`[name=${name}]`).value = value; });
  const missing = Object.keys(job).filter(k => !job[k]);
  note.textContent = missing.length ? 'Filled. Please add: ' + missing.join(', ') : 'Filled. Check it, then click Save job.';
  return true;
}
document.querySelectorAll('[data-paste]').forEach(button => button.onclick = async () => {
  try { fillForm(button.form, await navigator.clipboard.readText()); }
  catch (e) { button.form.querySelector('.paste-note').textContent = 'Clipboard blocked. Click in the description box and press Ctrl+V.'; }
});
// Ctrl+V of a copied job into any box of the form also fills every field.
document.querySelectorAll('form[action="/add"]').forEach(form => form.addEventListener('paste', e => {
  const text = e.clipboardData.getData('text');
  if (parseJob(text)) { e.preventDefault(); fillForm(form, text); }
}));

document.querySelectorAll('[data-copy]').forEach(button => button.onclick = async () => {
  const box = button.closest('.card').querySelector('textarea');
  try { await navigator.clipboard.writeText(box.value); button.textContent = '✓ Copied'; }
  catch (e) { box.select(); button.textContent = 'Press Ctrl+C'; }
});

// Referral note: rebuilt from the chosen job and contact name. You send it yourself.
const referral = $('referral');
if (referral) {
  const write = () => {
    const job = $('ref-job').selectedOptions[0].dataset;
    $('ref-text').value = `Hi ${v('ref-name') || 'there'},\n\nI hope you are doing well. I am applying for the ${job.title} role at ` +
      `${job.company}${job.url ? ' (' + job.url + ')' : ''}. Would you be comfortable referring me, or pointing me to the ` +
      `right person? I can send my resume.\n\nMy profile: ${referral.dataset.link}\n\nThank you,\n${referral.dataset.me}`;
  };
  $('ref-job').onchange = write;
  $('ref-name').oninput = write;
  write();
}

document.querySelectorAll('[data-alert]').forEach(input => input.onchange = async () => {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 1500000) { alert('That file is too large for a job alert email.'); return; }
  input.form.querySelector('[name=raw]').value = await file.text();
  input.form.submit();
});

let show = '';
function filterJobs() {
  const text = v('filter').toLowerCase();
  document.querySelectorAll('#all-jobs .job').forEach(j => {
    j.style.display = (!show || j.dataset.kind === show) && j.dataset.text.includes(text) ? '' : 'none';
  });
}
$('filter').oninput = filterJobs;
document.querySelectorAll('[data-show]').forEach(b => b.onclick = () => {
  show = b.dataset.show;
  document.querySelectorAll('[data-show]').forEach(x => x.classList.toggle('on', x === b));
  filterJobs();
});

const log = $('log'); if (log) log.scrollTop = log.scrollHeight;
if (document.body.dataset.busy === 'yes') {
  const timer = setInterval(async () => {
    const s = await (await fetch('/status')).json();
    log.textContent = s.log; log.scrollTop = log.scrollHeight;
    // Reload when finished, but never while you are typing in a form.
    const typing = [...document.querySelectorAll('textarea, [name=title], [name=company], [name=key]')].some(e => e.value);
    if (!s.running) {
      clearInterval(timer);
      if (typing) document.querySelector('summary').textContent = 'Finished. Reload the page to see the results.';
      else location.reload();
    }
  }, 1500);
}
"""


def render(ctx) -> str:
    page = Page(ctx)
    cand = ctx["cfg"]["candidate"]
    counts = {"jobs": len(ctx["jobs"]), "grow": len(ctx["followups"])}
    for key, p in PORTALS.items():
        counts[key] = sum(site_of(j) == p["name"] for j in ctx["jobs"])
    nav = "".join(f'<a href="#{k}">{label}{f"<span>{counts[k]}</span>" if counts.get(k) else ""}</a>' for k, label in TABS)
    bodies = {"home": page.home(), **{k: page.portal(k) for k in PORTALS}, "company": page.company(),
              "results": page.results(), "jobs": page.jobs(), "grow": page.grow(), "learn": learn.render(), "settings": page.settings()}
    tabs = "".join(f'<section class="tab" id="tab-{k}">{bodies[k]}</section>' for k, _ in TABS)
    activity = ""
    if ctx["busy"] or ctx["log"]:
        title = f"⏳ Running: {escape(ctx['task'])}…" if ctx["busy"] else f"Last activity: {escape(ctx['task'])}"
        activity = f'<details {"open" if ctx["busy"] else ""}><summary>{title}</summary><pre id="log">{escape(ctx["log"])}</pre></details>'
    note = f'<div class="note">{escape(ctx["message"])}</div>' if ctx["message"] else ""
    fonts = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800"
             "&family=Inter:wght@400;500;600;700&display=swap")
    return f"""<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Job Agent</title>
<link rel="stylesheet" href="{fonts}"><style>{CSS}{learn.CSS}</style></head>
<body data-busy="{'yes' if ctx['busy'] else 'no'}"><header><div class="top"><div class="logo"><i>🚀</i><div><h1>Job Agent</h1>
<p class="who">{escape(cand['name'])} · {escape(cand['email'])}</p></div></div><div class="tools">
<button type="button" class="ghost" id="privacy" title="Blur personal details before showing your screen">🙈 Privacy</button>
<button type="button" class="ghost" id="theme" title="Switch light or dark">🌗 Theme</button></div></div><nav>{nav}</nav></header>
<main>{note}{activity}{tabs}</main><script>{JS}{learn.JS}</script></body></html>"""

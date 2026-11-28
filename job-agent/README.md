# Job Agent: automated job hunt for a Solution Architect

Four agents in a pipeline:

| Agent | What it does |
|---|---|
| **Discover** | Pulls jobs from Remotive, Adzuna (India), and any Greenhouse / Lever company boards you list. Filters by title, location, age, and excluded words. |
| **Match** | Cheap keyword overlap first, then Claude scores fit 0–100 with reasons, gaps, and the ATS keywords you actually have. |
| **Tailor** | Claude selects, reorders, and rephrases facts from `master_resume.yaml` (it never invents anything), renders an ATS-safe .docx and a cover letter, then re-parses the .docx to check keyword coverage. |
| **Apply** | Playwright fills Greenhouse/Lever forms. `review` = fills and waits for you to submit · `auto` = submits (falls back to review if there are custom screening questions) · `pack` = files only. |

A SQLite tracker dedupes jobs across runs, enforces a daily limit, and exports `data/tracker.csv`.

## Setup (10 min)
```bash
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com
python run.py all --demo                   # offline test, no key needed
```
1. Check `master_resume.yaml`: every fact in it can appear in a resume you send.
2. Put your contact details in `config.local.yaml` (ignored by git). Set titles and locations in `config.yaml`.
3. Get a free Adzuna key (developer.adzuna.com), the main source for India: set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
4. `python run.py find` searches without AI. `python run.py hunt` also writes resumes and cover letters.
5. Save LinkedIn/Naukri jobs into `jobs_inbox/` (see `_example.txt`), then `python run.py inbox`.
6. Review `output/<company>_<role>_<id>/`, then `python run.py apply`.

Windows step-by-step guide: [../SETUP.md](../SETUP.md).

## Hosted on GitHub Actions (this repo)
`.github/workflows/job-agent.yml` runs every day at 09:00 IST, and also from **Actions → job-agent → Run workflow**.

Add these under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | from console.anthropic.com (required) |
| `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `CANDIDATE_PHONE`, `CANDIDATE_LINKEDIN` | your contact details (kept out of the public code) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | from developer.adzuna.com (recommended). Used automatically once set |

Each run uploads an **applications-N** artifact with the tailored resumes and cover letters, and commits `data/tracker.csv` so jobs aren't processed twice.
⚠️ This repo is public, so the tracker (companies you applied to) and the run artifacts can be seen by others. Make the repo private if that matters to you. Nothing else needs to change.

## Run it daily (fully hands-off)
- **Linux/Mac cron:** `0 9 * * * cd ~/job-agent && python run.py all >> data/run.log 2>&1` (use `apply.mode: auto` or `pack`)
- **Windows Task Scheduler:** `python C:\job-agent\run.py all`
- **Azure:** containerise it and run as an Azure Container Apps Job on a cron trigger, with the key in Key Vault.

## Web page and Excel tracker
Double-click `ui.bat` (or run `python ui.py`). Applications are logged by date in `data/job_applications.xlsx`.

## Why there's no LinkedIn, Naukri or Indeed bot
Their terms forbid automated applying, and accounts get restricted. On those sites the agent still finds and tailors (through Adzuna, which aggregates many Indian listings), and you click Apply with the prepared resume. Easy Apply volume rarely converts for architect roles anyway. Referrals and direct company boards do.

## Extending
- Add a source: write a function in `agents/discover.py` that returns `_job(...)` dicts.
- Add an ATS (Workday, SmartRecruiters): add a selector map in `agents/apply.py`.
- Port to .NET: same design. Use `HttpClient` against the Anthropic Messages API, `DocumentFormat.OpenXml` for the .docx, and `Microsoft.Playwright` for forms.

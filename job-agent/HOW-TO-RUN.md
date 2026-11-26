# How to Run the Job Agent

The agent finds Solution Architect jobs, scores how well you fit each one, writes a tailored ATS-friendly resume and cover letter for each good match, and keeps track of everything it has processed.

You can run it in three ways:

| Option | Cost | Best for |
|---|---|---|
| **A. GitHub Actions** (recommended) | Free hosting | Fully automatic daily runs, laptop not needed |
| **B. Your laptop** | Free | Testing, and `review` mode (the browser fills forms, you click Submit) |
| **C. Oracle Cloud Free VM** | Free | An always-on server you control |

> The only paid part is the **Claude API key**: you pay a small amount per day, based on how many jobs it scores and tailors.

---

## Before you start: get a Claude API key

1. Go to **https://console.anthropic.com** and sign in.
2. Open **Billing** and add a small amount of credit.
3. Open **API Keys** → **Create Key**.
4. Copy the key (it starts with `sk-ant-`) and keep it safe. Never commit it to the repo.

---

## Option A: GitHub Actions (free, automatic)

The workflow file is already in the repo at `.github/workflows/job-agent.yml`.

### Step 1: Merge the pull request
Open **https://github.com/cknitin/Job-Search/pull/1**, tap **Merge pull request**, then **Confirm merge**.
Scheduled jobs only run from the `main` branch.

### Step 2: Add your secrets
In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key (**required**) |
| `CANDIDATE_NAME` | Your full name |
| `CANDIDATE_EMAIL` | Your email |
| `CANDIDATE_PHONE` | Your phone number |
| `CANDIDATE_LINKEDIN` | Your LinkedIn URL |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | *Optional.* Free keys from https://developer.adzuna.com. Adds many more Indian job listings |

Secrets stay hidden even though the repo is public.

### Step 3: Run it once manually
1. Open the **Actions** tab.
2. Choose **job-agent** on the left.
3. Tap **Run workflow** → **Run workflow**.
4. Wait 3–5 minutes.
   - ✅ Green tick = success
   - ❌ Red cross = something failed. Open the run and read the error (see Troubleshooting below)

### Step 4: Download your tailored resumes
1. Open the finished run.
2. Scroll down to **Artifacts** and download **applications-N**.
3. Unzip it. There is one folder per job:
   - `*_resume.docx`: the tailored ATS resume
   - `cover_letter.txt`: the cover letter
   - `job.json`: the job link, fit score, gaps and missing keywords

### Step 5: Apply
Open the job link from `job.json`, upload that folder's resume and paste the cover letter.
`job-agent/data/tracker.csv` in the repo lists every job found, with its fit score and status.

### Step 6: Let it run daily
It runs automatically every day at **9:00 AM IST** and skips jobs it has already handled.

---

## Option B: Run on your laptop

### Step 1: Install the tools (one time)
- **Python 3.10+**: https://www.python.org/downloads/ (on Windows, tick **"Add Python to PATH"**)
- **Git**: https://git-scm.com/downloads

### Step 2: Download the project
```bash
git clone https://github.com/cknitin/Job-Search
cd Job-Search/job-agent
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Do a test run (no API key needed)
```bash
python run.py all --demo
```
This uses two sample jobs and a fake AI response. You should see one job tailored and one skipped, and a resume in the `output/` folder.

### Step 5: Set your API key and details
**Windows (Command Prompt):**
```bat
set ANTHROPIC_API_KEY=sk-ant-your-key
set CANDIDATE_NAME=Your Name
set CANDIDATE_EMAIL=you@example.com
set CANDIDATE_PHONE=+91-XXXXXXXXXX
set CANDIDATE_LINKEDIN=https://www.linkedin.com/in/your-profile/
```
**Mac / Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
export CANDIDATE_NAME="Your Name"
export CANDIDATE_EMAIL=you@example.com
export CANDIDATE_PHONE=+91-XXXXXXXXXX
export CANDIDATE_LINKEDIN=https://www.linkedin.com/in/your-profile/
```

### Step 6: Run it for real
```bash
python run.py hunt      # find, score and tailor only (nothing is submitted)
python run.py apply     # apply to jobs marked "ready"
python run.py all       # hunt + apply together
python run.py export    # refresh data/tracker.csv
```

### Step 7 (optional): Schedule it daily
- **Windows:** Task Scheduler → Create Basic Task → Daily, 9:00 AM → Action: *Start a program* → Program: `python`, Arguments: `run.py all`, Start in: the `job-agent` folder path.
- **Mac/Linux:** run `crontab -e` and add:
  ```
  0 9 * * * cd ~/Job-Search/job-agent && python3 run.py all >> data/run.log 2>&1
  ```

---

## Option C: Oracle Cloud Always Free VM

1. Sign up at **https://www.oracle.com/cloud/free/** and create an **Always Free** Ubuntu VM.
2. Connect with SSH and run:
   ```bash
   sudo apt update && sudo apt install -y python3-pip git
   git clone https://github.com/cknitin/Job-Search
   cd Job-Search/job-agent
   pip3 install -r requirements.txt
   python3 run.py all --demo
   ```
3. Add your keys to `~/.bashrc` (the same `export` lines as Option B, Step 5), then run `source ~/.bashrc`.
4. Schedule it with `crontab -e`:
   ```
   0 9 * * * . $HOME/.bashrc; cd ~/Job-Search/job-agent && python3 run.py all >> data/run.log 2>&1
   ```

---

## Apply modes

Set `apply.mode` in `config.yaml` (GitHub Actions overrides it with `APPLY_MODE: pack`):

| Mode | What happens |
|---|---|
| `pack` | Creates the resume and cover letter only. You apply manually. **Safest; used on GitHub.** |
| `review` | Opens a browser, fills Greenhouse/Lever forms and uploads your resume, then waits for **you** to click Submit. Laptop only. |
| `auto` | Submits Greenhouse/Lever forms by itself. Switches to review if the form has custom questions. Test locally first. |

LinkedIn and Naukri are **not** auto-applied, because their terms ban bots and accounts get restricted. Apply on those sites manually with the prepared resume.

---

## Customising

| What | Where |
|---|---|
| Your experience, bullets, skills | `master_resume.yaml` (the agent only uses facts written here, so keep it complete and truthful) |
| Job titles, locations, excluded words | `config.yaml` → `search` |
| Companies to watch | `config.yaml` → `greenhouse_boards` / `lever_companies` (the slug from `boards.greenhouse.io/<slug>` or `jobs.lever.co/<slug>`) |
| Minimum fit score (default 70) | `config.yaml` → `matching.min_fit_score` |
| Jobs per run / daily limit | `matching.max_jobs_per_run`, `apply.daily_limit` |
| Run time on GitHub | `cron:` line in `.github/workflows/job-agent.yml` (UTC; `30 3 * * *` = 9:00 AM IST) |
| Lower cost | Raise `matching.min_keyword_score` so fewer jobs reach Claude |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Set ANTHROPIC_API_KEY` error | The key is missing. Add the secret (GitHub) or run the `set`/`export` line (laptop) |
| `401` / `authentication_error` | Wrong or revoked key. Create a new one |
| `credit balance too low` | Add credit in console.anthropic.com → Billing |
| `0 new relevant jobs` | Normal on some days. Widen `titles`/`locations`, raise `max_age_days`, or enable Adzuna |
| A source shows `failed` | That job site was temporarily down. The other sources still run |
| Workflow doesn't run on schedule | Make sure the PR is merged to `main`. GitHub pauses schedules in repos with no activity for 60 days, so re-enable it in the Actions tab |
| No artifact on the run | No job scored above `min_fit_score` that day |

---

## Privacy note

This repo is **public**. Your contact details stay safe in Secrets, but `data/tracker.csv` (the companies you've applied to) and run artifacts can be seen by others. To keep your job search private, go to **Settings → General → Danger Zone → Change visibility → Private**. Everything keeps working.

# How to run the job agent

First time on this computer? Do [SETUP.md](SETUP.md) first.

## Start

Open the `job-agent` folder in File Explorer and double-click **`ui.bat`**.

Or from Command Prompt or PowerShell (change the path if your copy is elsewhere):

```
D:\Projects\Job-Search\job-agent\ui.bat
```

Your browser opens at http://127.0.0.1:8765.
Keep the black window open while you use it. To stop, press `Ctrl+C` in that window.

## The tabs

| Tab | What you do there |
|---|---|
| Home | See your counts and setup warnings; run `inbox`, `find`, `hunt`, `apply`, `all`, `export` |
| LinkedIn, Naukri, Indeed | Log in, search with that portal's filters, add a job, see that portal's jobs |
| Company sites | Automatic search results, and jobs from email or company websites |
| Results | What each command produced, jobs ready to apply, search results, low-score jobs, applications by date |
| My jobs | All jobs, with search and filters; download the Excel tracker |
| Grow | What is working, referral note, job alert import, follow-ups, skill gap report |
| Learn | Short Linux and Git lessons with real work examples and practice tasks |
| Settings | Paste your API key; check the details printed on your resume |

At the top right, **Privacy** blurs your name, email, company names and logs before you show your screen,
and **Theme** switches between dark and light. Privacy does not blur job titles or files you open or download,
so check the screen before a demo.

## Search profile

Under **Settings**, enter your skills (most important first), years of experience, job titles, preferred cities (best first) and
work preference, then click
**Save search profile**.

- Portal searches start with your first title, first two skills and first city. Naukri also gets your experience.
- `find` and `hunt` rank jobs by your skills and leave out jobs that ask for more experience than yours, or for far
  less. Experience is read from the job text, so it can be wrong.
- Results in your first city are listed first. Without **Remote** ticked, remote-only jobs are left out; with only
  **Remote** ticked, you get only remote jobs. **Hybrid** and **On-site** only set LinkedIn's workplace filter.
- It does not change your resume, which comes from `job-agent\master_resume.yaml`.

## Copy jobs with the Chrome extension

Install once:

1. In Chrome, open `chrome://extensions`.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose `D:\Projects\Job-Search\job-agent\chrome-extension`.
4. Reload any LinkedIn, Naukri or Indeed tabs that were already open.

Then:

1. Open a job on the portal, so its full description is on screen.
2. Hover the job and click **Copy job**, or click **Copy this job** at the bottom right.
3. Check the details in the small panel. If something is missing, type it, or select the description on the page
   and click **Use selected text**.
4. Click **Copy for Job Agent**.
5. In Job Agent, on that portal's tab, click **Paste copied job**, then **Save job**.

The extension acts only when you click and sends nothing anywhere. These sites' terms restrict tools that copy
their content, LinkedIn's in particular, so use it sparingly. When a site changes its pages, a field may come out
empty; use **Use selected text**.

## Use

1. **Settings:** paste your Anthropic API key and click **Use key**. It is needed only to create documents.
2. **LinkedIn, Naukri or Indeed:** search, and open a job you like.
3. On the same tab, paste the title, company, link and full job description, then click **Save job**.
4. Click **Create documents now** and watch the activity box.
5. Read the resume and cover letter, apply on the site, then click **Mark applied**.

Already applied somewhere? Enter the title, company and link and click **I already applied: just record it**.

## Commands

The buttons are on the **Home** tab, under **Actions**.

| Button | What it does | API key |
|---|---|---|
| `python run.py inbox` | Creates documents for the jobs you saved | Needed |
| `python run.py hunt` | Searches job sites and creates documents, saved jobs included | Needed |
| `python run.py find` | Searches job sites only; results appear under Company sites | Not needed |
| `python run.py apply` | Applies to jobs that are ready (asks you to confirm) | Not needed |
| `python run.py all` | `hunt`, then `apply` (asks you to confirm) | Needed |
| `python run.py export` | Rebuilds `data\tracker.csv` and the Excel tracker | Not needed |

A job that already has documents is not prepared again.

What `apply` does depends on `apply.mode` in `job-agent\config.yaml`: `review` (default) fills Greenhouse and
Lever forms for you to submit, `auto` submits them, `pack` submits nothing. Jobs from other sites are never
submitted for you. After checking a form, close the browser window and click **Mark applied**.

To run a command in a terminal instead, first go to the folder and activate the environment:

```bat
cd /d D:\Projects\Job-Search\job-agent
.venv\Scripts\activate
python run.py find
```

## Grow

- **What is working:** interviews per 10 applications, by site, job title and fit score. It reads the **Stage** you
  set in the Excel file.
- **Referral note:** pick a job, type your contact's name, copy the message and send it yourself.
- **Job alert import:** in Gmail, open a portal's alert email, choose **Download message** from the menu, and select
  that `.eml` file on the page. Jobs are ranked by title; links are never opened automatically.
- **Smart save** (on every add-job form): paste a whole job page into the description box; the AI picks out the
  title, company, location and description. It uses API credit. Check the saved job.
- **Follow-ups:** 7 days after applying, a draft message appears. Copy it, send it yourself, then click
  **I followed up**. Setting a different **Stage** in the Excel file also removes it.
- **Skill gap report:** counts skills in the job descriptions on your computer against your resume. It needs no
  API key, and is only reliable with ten or more jobs.
- **Interview prep:** under **My jobs**, click **Prepare for interview** on a job with documents. It uses API credit
  and sends your resume and the notes in `Questions` to Anthropic. Check every answer point is true.

See [roadmap.md](roadmap.md) for what could come next.

## Where things are

| What | Where |
|---|---|
| Applications by date | `job-agent\data\job_applications.xlsx` |
| Resume, cover letter and job details | `job-agent\output\` (one folder per job) |
| Jobs you saved | `job-agent\jobs_inbox\` |

## Problems

| Message | Fix |
|---|---|
| `Run setup.ps1 first` | Do step 4 of [SETUP.md](SETUP.md) |
| `Port 8765 is in use` | It is already running: open http://127.0.0.1:8765 |
| `ANTHROPIC_API_KEY is not set` | Do step 1 above |
| `Close job_applications.xlsx in Excel` | Close the file; it updates on the next change |

More fixes are under "Troubleshooting" in [SETUP.md](SETUP.md).

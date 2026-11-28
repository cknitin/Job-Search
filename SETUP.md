# Setting up the job agent on Windows

Follow the steps in order. Commands are for **Command Prompt** unless a step says otherwise.
Examples use `D:\Projects\Job-Search`; change the path if your copy is elsewhere.
For what the agent does, see [job-agent/README.md](job-agent/README.md).

## Quick start

Already installed? Do this:

1. Double-click `job-agent\ui.bat`.
2. Open the **LinkedIn**, **Naukri** or **Indeed** tab, search, and open a job you like.
3. Paste it on the same tab, click **Save job**, then **Create documents now** (needs an API key).
4. Read the resume and cover letter, apply, and click **Mark applied**.

First time? Start at step 1. Set your keys and details (step 6) before creating documents.

## 1. What you need

- Windows with `git` and `winget`
- An internet connection (the browser download is a few hundred MB)
- An Anthropic API key from console.anthropic.com, for real runs only

## 2. Get the code

```bat
cd /d D:\Projects
git clone https://github.com/cknitin/Job-Search.git
cd Job-Search
```

## 3. Fix the file names Windows rejects

Four files in the repository have `:` in their names, which Windows does not allow.
Git reports `error: invalid path` for them. Skip this step if you see no such error.

**3.1** Restore all the other files. The four `invalid path` errors are expected.

```bat
git restore --source=HEAD --staged --worktree -- .
```

**3.2** Open **Git Bash** in the repository folder and save the four files with ` -` instead of `:`.

```bash
git ls-tree -r --name-only -z HEAD | while IFS= read -r -d '' p; do
  case "$p" in *:*) n="${p//:/ -}"; [ -e "$n" ] || git cat-file blob "HEAD:$p" > "$n";; esac
done
```

**3.3** Make the rename permanent (recommended). Check that `git status` shows four renames before you commit.

```bat
git add -- "07 - Problem*" "13 - Design*" "Case Study - 01*" "Case Study - 02*"
git status
git commit -m "Rename files with colons so the repo checks out on Windows"
git push
```

> **Warning:** until you do 3.3, git shows the four original names as staged deletions.
> A commit made in that state removes those files from the repository.

## 4. Install everything

```bat
powershell -ExecutionPolicy Bypass -File D:\Projects\Job-Search\job-agent\setup.ps1
```

[setup.ps1](job-agent/setup.ps1) does the following, and is safe to run again:

| Step | What it does |
|---|---|
| 1/5 | Installs Python 3.12 with `winget`, if missing |
| 2/5 | Creates the virtual environment `job-agent\.venv` |
| 3/5 | Installs the packages in `requirements.txt` |
| 4/5 | Installs the Chromium browser used by Playwright |
| 5/5 | Runs the offline demo (`run.py all --demo`) |

It ends with `Setup complete.` A pip "new release" notice is harmless.

### Manual alternative

Use this instead of the script if you prefer to run each step yourself.

```bat
winget install -e --id Python.Python.3.12 --source winget
```

Close all terminals (restart VS Code if you use its terminal), open a new one, then:

```bat
cd /d D:\Projects\Job-Search\job-agent
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python run.py all --demo
```

### Optional: add Python to PATH

This makes `python` and `pip` work in any terminal.

```bat
powershell -ExecutionPolicy Bypass -File D:\Projects\Job-Search\job-agent\set-python-path.ps1
```

[set-python-path.ps1](job-agent/set-python-path.ps1) puts the Python 3.12 and `Scripts` folders at the front of your user `PATH`.
If it changes anything, it first saves the old value to `path-backup-*.txt` in your user folder.
Close all terminals (restart VS Code too), open a new one, and check:

```bat
python --version
pip --version
```

The project's packages are in `.venv`, so you still need to activate it to run the agent from a terminal (step 7.1).

## 5. Check the demo result

The demo needs no API key, uses two sample jobs and opens no browser. It checks the installation only:
**its cover letter and score are placeholders, so never send them.**

Look in `job-agent\output\_demo\`. Each run starts the demo again.

## 6. Configure for real use

**6.1** Check [job-agent/master_resume.yaml](job-agent/master_resume.yaml) line by line. Every fact in it can appear in a resume you send.

**6.2** Review [job-agent/config.yaml](job-agent/config.yaml):

| Setting | Meaning |
|---|---|
| `search` | Job titles, locations, excluded words, maximum age |
| `sources` | Remotive, Adzuna, Greenhouse boards, Lever companies |
| `matching.min_fit_score` | Minimum score before a resume is tailored (default 70) |
| `apply.mode` | `review` (default): you submit. `auto`: it submits. `pack`: files only |
| `apply.daily_limit` | Maximum applications per day (default 10) |

**6.3** Set your API key. The README uses `export`, which is for Linux and Mac and does not work on Windows.

| Terminal | Command | Lasts |
|---|---|---|
| Command Prompt | `set ANTHROPIC_API_KEY=your-key-here` | Until the terminal closes |
| PowerShell | `$env:ANTHROPIC_API_KEY = "your-key-here"` | Until the terminal closes |
| Either | `setx ANTHROPIC_API_KEY "your-key-here"` | Permanently, for new terminals only |

In Command Prompt `set`, use no quotes and no spaces around `=`.
After `setx`, close all terminals and restart VS Code. `setx` stores the key unencrypted in your Windows user settings.

Check that the key is set without displaying it:

```bat
if defined ANTHROPIC_API_KEY (echo Key is set) else (echo Key is NOT set)
```

```powershell
if ($env:ANTHROPIC_API_KEY) { "Key is set" } else { "Key is NOT set" }
```

> **Keep the key private.** Do not paste it into a chat, an issue or a file in this repository.
> If you do, delete that key at console.anthropic.com and create a new one.

**6.4** Set your contact details in `job-agent\config.local.yaml`. Git ignores this file, so it is not pushed.

```yaml
candidate:
  name: "Your Name"
  email: "you@example.com"
  phone: "+91-00000-00000"
  location: "Noida, India"
  linkedin: "https://linkedin.com/in/your-profile"
```

**6.5** Get a free key at developer.adzuna.com. Adzuna is the main source of jobs in India; without it
the search finds very little.

```bat
setx ADZUNA_APP_ID "your-id"
setx ADZUNA_APP_KEY "your-key"
```

Close all terminals and restart VS Code after `setx`.

## 7. Daily use

### The web page (easiest)

Double-click `job-agent\ui.bat`. Your browser opens `http://127.0.0.1:8765`. Keep the black window open
while you use it. The page works only on your computer.

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

Portal sites open in your own browser, so the agent never sees your password. A job appears on a portal's tab
when its link is on that site. After reading the resume and cover letter, choose:

| Button | What it does | Works for |
|---|---|---|
| Open & apply | Opens the job; you apply yourself | All sites |
| Mark applied | Records the application | All sites |
| Fill form | Fills the form; you check it and click Submit; close the window, then Mark applied | Greenhouse, Lever |
| Auto apply | Asks you to confirm, then submits if every required field is filled | Greenhouse, Lever |

LinkedIn, Naukri and Indeed are never logged in to, read or applied to automatically. Their terms forbid it
and your account could be restricted.

Set the keys from 6.3 and 6.5 with `setx` so the page can use them, or paste the Anthropic key on the
**Settings** tab for that session.

If auto apply shows `check-submission`, no confirmation was detected. Check your email before applying again;
if it went through, click **Mark applied**.

### Excel tracker

`job-agent\data\job_applications.xlsx` (also **Download Excel tracker** on the page):

| Sheet | Content |
|---|---|
| Applications | Every job you applied to, newest date first |
| Daily Summary | Number of applications and companies for each date |
| All Jobs | Every job found, with its status |

On the Applications sheet you can set **Stage**, **Follow-up date** and **My notes**; they are kept when the
file is rebuilt. Other changes are overwritten. Close the file in Excel while the agent updates it.
The file is ignored by git. `python run.py export` rebuilds it.

### Command line

**7.1** Open a terminal and activate the environment, then set the key from 6.3.

```bat
cd /d D:\Projects\Job-Search\job-agent
.venv\Scripts\activate
```

In PowerShell, skip activation and call the environment's Python directly:

```powershell
cd D:\Projects\Job-Search\job-agent
.\.venv\Scripts\python.exe run.py find
```

**7.2** Search without AI. This is free and needs no API key.

```bat
python run.py find
```

Matches are listed in `output\_found\jobs_found.txt`, with a `job_details.txt` for each.

**7.3** Add jobs you find on LinkedIn, Naukri or in email. Copy `jobs_inbox\_example.txt` to a new name
without the underscore, for example `jobs_inbox\acme.txt`, and paste the **full** job description.

**7.4** Write resumes and cover letters. This uses API credit and applies to nothing.

```bat
python run.py inbox
```

for the jobs you saved only, or

```bat
python run.py hunt
```

for your saved jobs and the job sites. Jobs you saved are always prepared. Jobs from sites are prepared
only if they reach `matching.min_fit_score`.

**7.5** Each job gets a folder in `output\`:

| File | Content |
|---|---|
| `job_details.txt` | Apply link, fit score, why you match, gaps, full description, warnings |
| `*_resume.docx` | Tailored resume |
| `*_cover_letter.docx`, `cover_letter.txt` | Cover letter |
| `job.json` | The same job data for programs |

**Read both documents before you send them.** The AI can still word something badly or overstate it.

**7.6** Apply.

```bat
python run.py apply
```

In `review` mode, Greenhouse and Lever forms open in a browser. Check the form, click **Submit**, then answer
the `Did you submit it?` question in the terminal. Other jobs are marked `packed`; apply to those yourself
using the link shown.

| Command | What it does |
|---|---|
| `python run.py find` | Search only, no AI |
| `python run.py inbox` | Tailor the jobs you saved |
| `python run.py hunt` | Search, score and tailor |
| `python run.py apply` | Apply to jobs that are ready |
| `python run.py all` | `hunt` then `apply` |
| `python run.py export` | Write `data\tracker.csv` |

A job is prepared once. `data\jobs.db` holds that memory **and your application history**. Deleting it
starts over, and the Excel tracker is then rebuilt without your past applications and notes. Copy
`data\job_applications.xlsx` somewhere else first.

## Chrome extension (optional)

`job-agent\chrome-extension` copies the job you are viewing so you can paste it into the page. Installation and
use are described in [run.md](run.md).

## 8. Before you commit

A real run creates `data\jobs.db` and `data\tracker.csv`. They list the companies you are considering
and applying to, and the repository is public. The GitHub workflow commits them to remember jobs between runs, so decide
whether to keep the repository public. Git ignores `config.local.yaml`, your saved jobs, the Excel file and `output\`.

To run the agent daily on GitHub instead of your PC, see "Hosted on GitHub Actions" in the
[README](job-agent/README.md).

## Troubleshooting

| Message or symptom | Cause | Fix |
|---|---|---|
| `error: invalid path '...:...'` | `:` in a file name | Step 3 |
| `'pip' is not recognized` | Python is not installed, or the environment is not active | Step 4, then 7.1 |
| `'py' is not recognized` | Python is not installed, or the terminal was opened before the install | Use `setup.ps1`, or open a new terminal |
| `Python was not found; run without arguments to install...` | Only the Microsoft Store shortcut exists | Step 4 |
| `python.exe :` with `NativeCommandError` | An older `setup.ps1` treated a pip notice as fatal | Use the current script, which uses `Continue` |
| `The system cannot find the path specified` on activate | `.venv` was not created | Step 4 |
| `ANTHROPIC_API_KEY is not set` | The key is not set in this terminal | Step 6.3 |
| `0 job(s) from job sites pass the filters` | Few sources are active | Steps 6.5 and 7.3 |
| `Anthropic API error 400` mentioning credit | No API credit | Add credit at console.anthropic.com |
| `check-submission` after auto apply | No confirmation was detected | Check your email before applying again |
| `Close job_applications.xlsx in Excel` | The file is open, so it could not be saved | Close it, then run `python run.py export` |
| `No module named 'openpyxl'` | A package was added | Run `setup.ps1` again |
| `Port 8765 is in use` | The page is already running | Open http://127.0.0.1:8765 |
| `'export' is not recognized` | `export` is a Linux and Mac command | Step 6.3 |
| `UnicodeDecodeError` after editing a `.yaml` file | The file is not saved as UTF-8 | In VS Code, save it with UTF-8 encoding |

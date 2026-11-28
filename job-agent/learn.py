"""Short lessons for the Learn tab: Linux first, then Git. Written for a beginner.

Each lesson: (title, plain idea, [(command or folder, what it does, real work example)], try it yourself)
"""
from html import escape

LINUX_START = ("Practise safely on Windows with WSL: open PowerShell as administrator, run <code>wsl --install</code> and "
               "restart. Then open <b>Ubuntu</b> from the Start menu. Git Bash also runs many of these commands, "
               "but it does not have the real Linux folders.")

LINUX = [
    ("1. The folder map", "Linux keeps everything in one tree that starts at / (called root). Think of a school: one "
     "building, with each room used for one thing.",
     [("/", "The top of the tree", "Every path begins here"),
      ("/home", "Each user's own files", "/home/nitin holds your documents and code"),
      ("/root", "Home of the administrator", "Only the admin can open it"),
      ("/etc", "Settings files", "Change a web server's port in /etc/nginx"),
      ("/var/log", "Diary of what happened", "The website is down: read the error log here"),
      ("/var/www", "Website files (common place)", "Put the company website here"),
      ("/tmp", "Short-term files, may be deleted", "A download you need only once"),
      ("/usr/bin", "Installed programs", "git and python usually live here"),
      ("/opt", "Extra software", "A company's own app installed in /opt/myapp"),
      ("/dev, /proc", "Devices and live system information", "/proc/meminfo shows memory use")],
     "Run ls / and match each folder you see with this list."),
    ("2. Moving around", "Like walking between rooms: know where you are, look around, then move.",
     [("pwd", "Shows where you are", "Check your folder before deleting anything"),
      ("ls -la", "Lists everything, including hidden files", "Find the hidden .env settings file"),
      ("cd /var/log", "Goes to a folder", "Go to the logs after an error"),
      ("cd ..", "Goes up one folder", "Step back from /var/log to /var"),
      ("cd ~", "Goes to your home folder", "Return to your own space")],
     "Go to /etc, list it, then come back home."),
    ("3. Files and folders", "Make, copy, move and delete, like using a file manager with your keyboard.",
     [("mkdir -p project/src", "Makes folders, including parents", "Set up a new project"),
      ("touch notes.txt", "Makes an empty file", "Create a to-do file"),
      ("cp app.conf app.conf.bak", "Copies a file", "Back up a setting before changing it"),
      ("mv old.txt new.txt", "Renames or moves", "Rename a report"),
      ("rm -i file.txt", "Deletes after asking. There is no recycle bin", "Remove an old file"),
      ("rm -r folder", "Deletes a folder and everything in it", "Remove an old build. Check pwd first")],
     "Make a folder practice, create a file in it, copy it, rename the copy."),
    ("4. Reading files", "Look inside a file without changing it.",
     [("cat file.txt", "Shows the whole file", "Read a short settings file"),
      ("less big.log", "Reads page by page (press q to quit)", "Browse a very large log"),
      ("head -n 5 data.csv", "First 5 lines", "See a data file's column names"),
      ("tail -f app.log", "Shows new lines as they arrive (Ctrl+C stops)", "Watch errors while a user tests"),
      ("nano file.txt", "Simple text editor (Ctrl+O saves, Ctrl+X exits)", "Fix one line on a server")],
     "Run cat /etc/os-release to find your Linux version."),
    ("5. Finding things", "Search for a file by name, or for words inside files.",
     [("find . -name '*.log'", "Finds files by name", "List all log files in a project"),
      ("grep -i error app.log", "Finds lines containing a word", "Pull the errors out of 10,000 lines"),
      ("grep -rn 'password' src/", "Searches all files and shows line numbers", "Check no password is left in code"),
      ("which python3", "Shows where a program is", "Check which Python will run")],
     "Search /etc/passwd for your own user name with grep."),
    ("6. Joining commands", "A pipe | passes one command's output to the next, like an assembly line.",
     [("ls -l | wc -l", "Counts lines of output", "Roughly count files in a folder"),
      ("grep error app.log | tail -n 20", "Last 20 errors", "See what failed most recently"),
      ("echo 'done' > status.txt", "Writes to a file, replacing it", "Save a status"),
      ("date >> status.txt", "Adds to the end of a file", "Keep a history of runs"),
      ("history | grep ssh", "Searches commands you typed", "Find yesterday's server command")],
     "Save the list of your home folder into list.txt, then read it."),
    ("7. Permissions", "Each file says who may read (r), write (w) and run (x): the owner, the group, everyone else.",
     [("ls -l", "Shows permissions such as -rw-r--r--", "See why a file cannot be edited"),
      ("chmod +x deploy.sh", "Makes a script runnable", "Fix 'Permission denied' on your script"),
      ("chmod 600 key.pem", "Only you can read and write", "Protect a server login key"),
      ("chown www-data site/", "Changes the owner", "Let the web server use its folder"),
      ("sudo <command>", "Runs as administrator. Read it twice first", "Install software")],
     "Make hello.sh containing echo hello, give it +x, run ./hello.sh."),
    ("8. Running programs", "Every running program is a process with a number (PID).",
     [("ps aux", "Lists processes", "Check the app is running"),
      ("top", "Live view of CPU and memory (q quits)", "The server is slow: find the cause"),
      ("kill 1234", "Asks process 1234 to stop", "Stop a stuck app. Use kill -9 only if needed"),
      ("systemctl status nginx", "Checks a service", "Is the web server up?"),
      ("sudo systemctl restart nginx", "Restarts a service", "Apply new settings")],
     "Run sleep 100 &, find it with ps, then kill it."),
    ("9. Disk, network and software", "Check space, connections and installed tools.",
     [("df -h", "Free disk space", "Uploads fail: is the disk full?"),
      ("du -sh *", "Size of each item here", "Find what is filling the disk"),
      ("ping -c 4 google.com", "Tests the connection", "Is the server online?"),
      ("curl -I https://example.com", "Asks a website for its headers", "Check a site returns 200 OK"),
      ("ssh user@server", "Logs in to another computer", "Work on a cloud server"),
      ("tar -czf backup.tar.gz folder/", "Packs and compresses", "Back up before an update"),
      ("sudo apt update && sudo apt install git", "Installs software (Ubuntu)", "Add git to a new server"),
      ("man ls", "Built-in help (q quits)", "Look up what an option means")],
     "Run df -h and find how full your main disk is."),
]

GIT_START = ("Git saves snapshots of your work, like save points in a game. <b>GitHub</b> is a website that keeps a copy "
             "online. Install Git from git-scm.com and practise in a new, empty folder.")

GIT = [
    ("1. Set up once", "Tell Git who you are, so each save has your name.",
     [('git config --global user.name "Asha"', "Sets your name", "Teammates see who changed what"),
      ('git config --global user.email "asha@example.com"', "Sets your email", "Links your work to your account"),
      ("git --version", "Checks Git is installed", "First check on a new laptop")],
     "Set your name, then run git config --global user.name to check it."),
    ("2. Start a project", "A repository (repo) is a folder whose history Git remembers.",
     [("git init", "Starts a repo in this folder", "Begin your school project"),
      ("git clone <url>", "Downloads a repo with its history", "Join a project on your first day at work")],
     "Make a folder shop, go into it, run git init."),
    ("3. The daily cycle", "Change files, choose what to save (stage), then save with a message (commit).",
     [("git status", "Shows what changed", "Look before every commit"),
      ("git diff", "Shows the exact lines changed", "Review your own work"),
      ("git add menu.txt", "Stages one file", "Choose only the finished file"),
      ('git commit -m "Add lunch menu"', "Saves a snapshot", "A clear note for your future self"),
      ("git log --oneline", "Short history", "Find when something changed")],
     "Create menu.txt, add it, commit it, then view the log."),
    ("4. Branches", "A branch is a side path where you try something without breaking the main version.",
     [("git branch", "Lists branches", "See where you are"),
      ("git switch -c add-payment", "Creates a branch and moves to it", "Start a new feature"),
      ("git switch main", "Goes back to main", "Fix an urgent bug"),
      ("git merge add-payment", "Brings a branch's work into the current one", "The feature is tested: add it")],
     "Make a branch, change menu.txt, commit, switch to main and merge."),
    ("5. Share with a team", "Push sends your commits online. Pull brings your teammates' commits to you.",
     [("git remote add origin <url>", "Connects your repo to GitHub", "First upload of a project"),
      ("git push -u origin main", "Uploads (first time)", "Publish your work"),
      ("git pull", "Downloads and merges", "Start of every work day"),
      ("git push -u origin add-payment", "Uploads your branch", "Then open a pull request for review")],
     "Create an empty repo on GitHub and push your practice project."),
    ("6. Merge conflicts", "If two people change the same line, Git asks you to choose.",
     [("<<<<<<<  =======  >>>>>>>", "Marks the two versions in the file", "Keep the right text, delete the marks"),
      ("git add file.txt", "Marks the conflict as solved", "After editing the file"),
      ("git commit", "Finishes the merge", "Record your choice"),
      ("git merge --abort", "Cancels the merge", "Not sure yet: go back and ask")],
     "Change the same line on two branches, merge, and solve it."),
    ("7. Undo safely", "Mistakes are normal. Use the gentlest fix.",
     [("git restore file.txt", "Throws away unsaved changes in a file (cannot be undone)", "You broke a file and want it back"),
      ("git restore --staged file.txt", "Un-stages, keeps your changes", "You added the wrong file"),
      ("git commit --amend", "Edits the last commit (before pushing)", "Fix a spelling in the message"),
      ("git revert <id>", "New commit that cancels an old one", "Safely undo something already shared"),
      ("git stash", "Puts changes aside; git stash pop brings them back", "Switch tasks in a hurry")],
     "Edit a file, then use git restore to bring it back."),
    ("8. Keep secrets out", "Anything you push may be seen and copied. Passwords and keys must never be committed.",
     [(".gitignore", "A file listing what Git should skip", "Add .env and node_modules/"),
      ("git rm --cached .env", "Stops tracking a file, keeps it on your computer", "It was added by mistake"),
      ("(change the key)", "A pushed secret is exposed, even if you delete it later", "Make a new key at once")],
     "Add secret.txt to .gitignore and check git status no longer shows it."),
]

COURSES = [("linux", "🐧 Linux", LINUX_START, LINUX), ("git", "🌿 Git", GIT_START, GIT)]


def render() -> str:
    switches, courses = "", ""
    for n, (key, name, start, lessons) in enumerate(COURSES):
        switches += f'<button type="button" class="chip{" on" if n == 0 else ""}" data-course="{key}">{name}</button>'
        body = ""
        for i, (title, idea, rows, practice) in enumerate(lessons):
            table = "".join(f'<tr><td><code class="cmd" tabindex="0" title="Click to copy">{escape(c)}</code></td>'
                            f'<td>{escape(what)}</td><td class="muted">{escape(example)}</td></tr>' for c, what, example in rows)
            body += (f'<details class="lesson"{" open" if i == 0 else ""}><summary>{escape(title)}'
                     f'<label class="done"><input type="checkbox" data-lesson="{key}-{i}"> Done</label></summary>'
                     f'<p>{escape(idea)}</p><div class="scroll"><table><tr><th>Type this</th><th>What it does</th>'
                     f'<th>Real work example</th></tr>{table}</table></div><p class="try">🎯 <b>Try it:</b> {escape(practice)}</p></details>')
        courses += (f'<div class="course" id="course-{key}"{"" if n == 0 else " hidden"}><div class="card">{start}</div>'
                    f'<p class="muted"><span id="progress-{key}">0</span> of {len(lessons)} lessons done</p>{body}</div>')
    return (f'<h2>Learn, one small step at a time</h2><p class="muted">Start with Linux, then Git. Click a command to copy it.</p>'
            f'<div>{switches}</div>{courses}')


CSS = """
.lesson{background:var(--card);color:var(--text)} .lesson summary{display:flex;justify-content:space-between;gap:10px;
font:800 17px var(--head);list-style-position:inside} .lesson .done{flex-direction:row;align-items:center;font:600 12px var(--bodyfont)}
.cmd{cursor:pointer;white-space:pre-wrap;font-size:13px} .try{background:#8b5cf61f;border-radius:12px;padding:10px 14px}
.private #tab-learn td{filter:none;user-select:auto}
"""

JS = r"""
document.querySelectorAll('[data-course]').forEach(button => button.onclick = () => {
  document.querySelectorAll('[data-course]').forEach(b => b.classList.toggle('on', b === button));
  document.querySelectorAll('.course').forEach(c => { c.hidden = c.id !== 'course-' + button.dataset.course; });
});
function countLessons() {
  ['linux', 'git'].forEach(key => {
    $('progress-' + key).textContent = document.querySelectorAll(`[data-lesson^="${key}-"]:checked`).length;
  });
}
document.querySelectorAll('[data-lesson]').forEach(box => {
  box.checked = recall('lesson-' + box.dataset.lesson) === 'yes';
  box.onchange = () => { remember('lesson-' + box.dataset.lesson, box.checked ? 'yes' : 'no'); countLessons(); };
});
countLessons();
document.querySelectorAll('.cmd').forEach(code => {
  const copy = async () => {
    try { await navigator.clipboard.writeText(code.textContent); code.title = 'Copied'; code.style.outline = '2px solid var(--lime)';
          setTimeout(() => { code.style.outline = ''; code.title = 'Click to copy'; }, 900); } catch (e) {}
  };
  code.onclick = copy;
  code.onkeydown = e => { if (e.key === 'Enter') copy(); };
});
"""

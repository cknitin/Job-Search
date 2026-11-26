"""Apply agent: fills Greenhouse / Lever hosted forms with Playwright.

mode=review -> fills everything, uploads resume, then WAITS for you to check & click Submit.
mode=auto   -> clicks Submit (only for Greenhouse/Lever, never for unknown sites).
mode=pack   -> no browser; just leaves resume + cover letter + link in the output folder.

Deliberately NOT automated: LinkedIn, Naukri, Indeed, etc. Their terms forbid bots and accounts get
restricted. For those, the agent prepares the pack and you apply in one click.
"""
from pathlib import Path

GREENHOUSE = {"first_name": "#first_name", "last_name": "#last_name", "email": "#email",
              "phone": "#phone", "resume": "input[type=file]#resume, input[type=file]",
              "cover": "textarea#cover_letter_text", "submit": "button[type=submit], #submit_app"}
LEVER = {"name": "input[name=name]", "email": "input[name=email]", "phone": "input[name=phone]",
         "linkedin": "input[name='urls[LinkedIn]']", "resume": "input[type=file][name=resume]",
         "cover": "textarea[name=comments]", "submit": "button[type=submit]"}


def apply(job: dict, cand: dict, resume: Path, cover: str, mode: str, headless: bool) -> str:
    if mode == "pack" or job["apply_type"] not in ("greenhouse", "lever"):
        return "packed"
    from playwright.sync_api import sync_playwright

    first, _, last = cand["name"].partition(" ")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless and mode == "auto")
        page = browser.new_page()
        if job["apply_type"] == "lever":
            page.goto(job["url"].rstrip("/") + "/apply")
            s = LEVER
            _fill(page, s["name"], cand["name"])
            _fill(page, s["linkedin"], cand["linkedin"])
        else:
            page.goto(job["url"])
            s = GREENHOUSE
            _fill(page, s["first_name"], first)
            _fill(page, s["last_name"], last or first)
        _fill(page, s["email"], cand["email"])
        _fill(page, s["phone"], cand["phone"])
        _fill(page, s["cover"], cover)
        try:
            page.set_input_files(s["resume"], str(resume))
        except Exception:
            pass
        if mode == "auto":
            unanswered = page.locator("input[required]:not([type=file]), select[required], textarea[required]")
            empties = [i for i in range(unanswered.count()) if not unanswered.nth(i).input_value()]
            if empties:  # custom screening questions -> never guess answers
                print(f"    {len(empties)} required custom questions; switching to review")
                mode = "review"
            else:
                page.click(s["submit"])
                page.wait_for_timeout(4000)
                browser.close()
                return "submitted"
        print("    Form filled. Review it in the browser, click Submit, then press Enter here.")
        input()
        browser.close()
        return "submitted-by-user"


def _fill(page, sel, val):
    if not val:
        return
    try:
        loc = page.locator(sel).first
        if loc.count():
            loc.fill(val)
    except Exception:
        pass

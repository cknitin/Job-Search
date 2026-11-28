"""Apply agent: fills Greenhouse / Lever hosted forms with Playwright.

mode=review -> fills the form, uploads the resume, then WAITS for you to check and click Submit.
mode=auto   -> clicks Submit (only Greenhouse/Lever, and only if every required field is filled).
mode=pack   -> no browser; just leaves resume + cover letter + link in the output folder.

Deliberately NOT automated: LinkedIn, Naukri, Indeed and similar sites. Their terms forbid bots and accounts get
restricted. For those, the agent prepares the documents and you apply yourself.
"""
from pathlib import Path

GREENHOUSE = {"first_name": "#first_name", "last_name": "#last_name", "email": "#email",
              "phone": "#phone", "resume": ["input[type=file]#resume", "input[type=file]"],
              "cover": "textarea#cover_letter_text", "submit": "button[type=submit], #submit_app"}
LEVER = {"name": "input[name=name]", "email": "input[name=email]", "phone": "input[name=phone]",
         "linkedin": "input[name='urls[LinkedIn]']", "resume": ["input[type=file][name=resume]"],
         "cover": "textarea[name=comments]", "submit": "button[type=submit]"}

# Counts required questions that are still unanswered (text boxes, dropdowns, radio buttons, checkboxes).
UNANSWERED_JS = """() => {
  const required = [...document.querySelectorAll('input, select, textarea')].filter(
    e => e.type !== 'file' && e.type !== 'hidden' && (e.required || e.getAttribute('aria-required') === 'true'));
  return required.filter(e => (e.type === 'radio' || e.type === 'checkbox')
    ? !(e.name ? [...document.getElementsByName(e.name)].some(o => o.checked) : e.checked)
    : !e.value).length;
}"""
CONFIRMATIONS = ("thank you for applying", "application has been submitted", "application submitted",
                 "thanks for applying", "we have received your application", "we've received your application")


def apply(job: dict, cand: dict, resume: Path, cover: str, mode: str, headless: bool, interactive=True) -> str:
    """Return the new status. interactive=False (the web UI) waits for the browser window to be closed."""
    if mode == "pack" or job["apply_type"] not in ("greenhouse", "lever"):
        return "packed"
    from playwright.sync_api import sync_playwright

    first, _, last = cand["name"].partition(" ")
    retry_visible = False
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
        email_ok = _fill(page, s["email"], cand["email"])
        _fill(page, s["phone"], cand["phone"])
        _fill(page, s["cover"], cover)
        resume_ok = _upload(page, s["resume"], resume)

        if mode == "auto":
            page.wait_for_timeout(2000)
            missing = page.evaluate(UNANSWERED_JS)
            if not (email_ok and resume_ok) or missing:  # never guess answers or send a half-filled form
                print(f"    Not submitting automatically ({missing} required answer(s) missing, "
                      f"email filled: {email_ok}, resume attached: {resume_ok}). Switching to review.")
                mode = "review"
                retry_visible = headless
            else:
                page.locator(s["submit"]).first.click()
                page.wait_for_timeout(6000)
                text = page.inner_text("body").lower()
                browser.close()
                if any(c in text for c in CONFIRMATIONS):
                    return "submitted"
                print("    Submit was clicked but no confirmation appeared. Check your email or apply again.")
                return "check-submission"

        if retry_visible:
            browser.close()
        else:
            return _review(browser, page, interactive)
    # Reached only when a hidden browser needs your answers; the first Playwright session is now closed.
    return apply(job, cand, resume, cover, "review", False, interactive)


def _review(browser, page, interactive) -> str:
    print("    Form filled. Check it in the browser, answer any extra questions and click Submit.")
    if interactive:
        done = input("    Did you submit it? (y/n): ").strip().lower().startswith("y")
        browser.close()
        return "submitted-by-user" if done else "ready"
    print("    Close the browser window when you are finished, then click 'Mark applied'.")
    try:
        page.wait_for_event("close", timeout=0)
        browser.close()
    except Exception:  # the whole browser was closed
        pass
    return "ready"


def _fill(page, sel, val) -> bool:
    if not val:
        return False
    try:
        loc = page.locator(sel).first
        if loc.count():
            loc.fill(val)
            return True
    except Exception:
        pass
    return False


def _upload(page, selectors, path) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.set_input_files(str(path))
                return True
        except Exception:
            pass
    return False

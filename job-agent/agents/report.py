"""Excel tracker: applications by date, a daily count, and every job found.

The file is rebuilt from the database each time. Your 'Stage', 'Follow-up date' and 'My notes' entries on
the Applications sheet are read back first, so they are kept.
"""
import os
from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

MINE = ["Stage", "Follow-up date", "My notes"]
STAGES = ["Applied", "Recruiter call", "Interview", "Offer", "Rejected", "No response"]
STATUS = {"submitted": "Applied (automatic)", "submitted-by-user": "Applied", "ready": "Ready to apply",
          "packed": "Ready: apply on the site", "check-submission": "CHECK: submission not confirmed",
          "hidden": "Hidden by you", "skipped-fit": "Skipped: low fit score",
          "skipped-keywords": "Skipped: few matching skills"}
SITES = ("linkedin", "naukri", "indeed")


def _site(row):
    url = (row["url"] or "").lower()
    return next((s.title() if s != "linkedin" else "LinkedIn" for s in SITES if s in url),
                (row["source"] or "").title())


def _date(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return text or None


def _kept(path: Path) -> dict:
    """Your own entries from the existing file, by job ID."""
    if not path.exists():
        return {}
    try:
        ws = load_workbook(path)["Applications"]
        head = [c.value for c in ws[1]]
        out = {}
        for values in ws.iter_rows(min_row=2, values_only=True):
            row = dict(zip(head, values))
            if row.get("Job ID"):
                out[row["Job ID"]] = {k: row.get(k) for k in MINE}
        return out
    except PermissionError:
        raise
    except Exception:  # damaged or restructured by hand: keep a copy rather than lose it
        path.replace(path.with_name(f"{path.stem}_backup_{date.today():%Y%m%d}.xlsx"))
        return {}


def _sheet(ws, headers, widths, rows, links=()):
    ws.append(headers)
    for values in rows:
        ws.append([ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v for v in values])
        for cell, name in zip(ws[ws.max_row], headers):
            if isinstance(cell.value, str):
                cell.data_type = "s"  # text from job sites must never run as a formula
                if name in links and cell.value.startswith(("http://", "https://")):
                    cell.hyperlink, cell.style = cell.value, "Hyperlink"
            if isinstance(cell.value, date):
                cell.number_format = "dd-mmm-yyyy"
            cell.alignment = Alignment(vertical="top", wrap_text=name in ("Job title", "My notes"))
    for i, (cell, width) in enumerate(zip(ws[1], widths), 1):
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")
        ws.column_dimensions[cell.column_letter].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_excel(jobs: list, path: Path) -> bool:
    """Rebuild the workbook. Returns False if it could not be saved (usually because it is open in Excel)."""
    try:
        mine = _kept(path)
        wb = Workbook()
        applied = sorted((j for j in jobs if j["applied_on"]), key=lambda j: j["applied_on"], reverse=True)

        ws = wb.active
        ws.title = "Applications"
        _sheet(ws, ["Applied on", "Company", "Job title", "Location", "Site", "Fit score", "How applied", *MINE,
                    "Link", "Job ID"],
               [13, 24, 42, 22, 12, 10, 20, 16, 15, 40, 45, 14],
               [[_date(j["applied_on"]), j["company"], j["title"], j["location"], _site(j), j["fit_score"],
                 "Automatic" if j["status"] == "submitted" else "Manual",
                 mine.get(j["id"], {}).get("Stage") or "Applied",
                 mine.get(j["id"], {}).get("Follow-up date"), mine.get(j["id"], {}).get("My notes"),
                 j["url"], j["id"]] for j in applied], links=("Link",))
        ws.column_dimensions["L"].hidden = True
        stages = DataValidation(type="list", formula1=f'"{",".join(STAGES)}"', allow_blank=True)
        ws.add_data_validation(stages)
        stages.add(f"H2:H{max(2, ws.max_row)}")

        per_day = Counter(j["applied_on"] for j in applied)
        daily = wb.create_sheet("Daily Summary")
        _sheet(daily, ["Date", "Jobs applied", "Companies"], [13, 14, 90],
               [[_date(d), n, ", ".join(j["company"] for j in applied if j["applied_on"] == d)]
                for d, n in sorted(per_day.items(), reverse=True)])
        if per_day:
            daily.append(["Total", sum(per_day.values())])
            for cell in daily[daily.max_row]:
                cell.font = Font(bold=True)

        _sheet(wb.create_sheet("All Jobs"),
               ["Found on", "Company", "Job title", "Location", "Site", "Fit score", "Status", "Link"],
               [13, 24, 42, 24, 12, 10, 32, 45],
               [[_date(j["found_on"]), j["company"], j["title"], j["location"], _site(j), j["fit_score"],
                 STATUS.get(j["status"], j["status"]), j["url"]] for j in jobs], links=("Link",))

        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.stem + ".tmp.xlsx")
        wb.save(temp)
        os.replace(temp, path)
        return True
    except PermissionError:
        print(f"    ! Close {path.name} in Excel; it will be updated on the next run.")
        path.with_name(path.stem + ".tmp.xlsx").unlink(missing_ok=True)
        return False

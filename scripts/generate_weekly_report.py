#!/usr/bin/env python3
"""
D2M WEEKLY ACTIVITY REPORT GENERATOR
scripts/generate_weekly_report.py

Cron: Friday 18:00 MT via systemd timer d2m-weekly-report.timer
Run:  python3 scripts/generate_weekly_report.py [--dry-run] [--no-email] [--no-inject]

Pipeline:
  1. Gather data (git log, hale_state, mission board, hale_brief)
  2. Generate full report via Claude Sonnet:
       - 5 staff assessments (Hale, Dani, Sterling, Intel, Harlan)
       - Hale's Synthesis (comments ON the staff, not a summary)
       - WHAT WE PLAN TO DO ABOUT IT (action items with owners)
  3. Parse tasks from plan section
  4. Inject tasks into mission board (with owner + priority)
  5. Append injected mission IDs to report
  6. Save to output/weekly_reports/
  7. Direct-send to johnloucks3@gmail.com (internal — no WF-17 gate)
"""

import json
import re
import sys
import argparse
import html as html_mod
from pathlib import Path
from datetime import datetime, timedelta, timezone

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD))

OPSCENTER = THUNDERBIRD / "OpsCenter"
OUTPUT = THUNDERBIRD / "output" / "weekly_reports"
LOG_FILE = THUNDERBIRD / "logs" / "weekly_report.log"


# ─── LOGGING ─────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── DATA GATHERING ───────────────────────────────────────────────────────────

def get_git_log() -> str:
    import subprocess
    result = subprocess.run(
        ["git", "log", "--since=7 days ago", "--oneline", "--no-merges",
         "--pretty=format:%ad  %s", "--date=short"],
        capture_output=True, text=True, cwd=THUNDERBIRD
    )
    return result.stdout.strip() or "No commits this week."


def get_hale_state() -> dict:
    try:
        return json.loads((THUNDERBIRD / "hale_state.json").read_text())
    except Exception:
        return {}


def get_mission_board() -> dict:
    try:
        return json.loads((OPSCENTER / "mission_board.json").read_text())
    except Exception:
        return {}


def get_hale_brief() -> str:
    try:
        return (THUNDERBIRD / "hale_brief.md").read_text()
    except Exception:
        return ""


def get_active_missions(board: dict) -> list:
    return [
        m for m in board.get("missions", [])
        if m.get("status") not in ("completed", "complete", "done", "archived", "cancelled")
    ]


# ─── MISSION BOARD INJECTION ──────────────────────────────────────────────────

def inject_task(board: dict, title: str, description: str, owner: str, priority: str) -> str:
    """Add a weekly-report task directly to board JSON. Returns new mission ID."""
    all_missions = board.get("missions", [])
    nums = []
    for m in all_missions:
        try:
            nums.append(int(m["id"].split("-")[-1]))
        except (ValueError, IndexError):
            pass
    next_num = (max(nums) + 1) if nums else 1
    mission_id = f"MISSION-{next_num:03d}"

    p = priority if priority in ("P0", "P1", "P2", "P3") else "P2"

    board.setdefault("missions", []).append({
        "id": mission_id,
        "title": title,
        "status": "active",
        "priority": p,
        "assigned_to": owner,
        "description": description,
        "deliverables": [],
        "dependencies": [],
        "suspense_date": None,
        "escalation_rule": None,
        "logs": [
            f"[{datetime.now(timezone.utc).isoformat()[:19]}] "
            f"Created by Weekly Report Generator"
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "weekly_report",
    })
    board["last_updated"] = datetime.now(timezone.utc).isoformat()
    return mission_id


def save_board(board: dict):
    board_path = OPSCENTER / "mission_board.json"
    board_path.write_text(json.dumps(board, indent=2, default=str))


# ─── TASK PARSING ─────────────────────────────────────────────────────────────

TASK_PATTERN = re.compile(
    r"TASK:\s*(.+?)\n"
    r"OWNER:\s*(.+?)\n"
    r"PRIORITY:\s*(.+?)\n"
    r"DESCRIPTION:\s*(.+?)(?=\nTASK:|\n---|\Z)",
    re.DOTALL,
)


def parse_tasks(report_text: str) -> list:
    section = re.search(
        r"## WHAT WE PLAN TO DO ABOUT IT(.+?)(?=^---|\Z)",
        report_text,
        re.DOTALL | re.MULTILINE,
    )
    if not section:
        return []
    tasks = []
    for m in TASK_PATTERN.finditer(section.group(1)):
        tasks.append({
            "title": m.group(1).strip(),
            "owner": m.group(2).strip(),
            "priority": m.group(3).strip().upper(),
            "description": m.group(4).strip().replace("\n", " ")[:300],
        })
    return tasks


# ─── REPORT GENERATION ────────────────────────────────────────────────────────

def _build_max_plan_env() -> dict:
    """Strip API key so claude CLI falls through to Max plan OAuth credentials."""
    import os
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)
    return env


async def _call_claude_sdk(prompt: str) -> str:
    """Call Claude via claude-code-sdk (Max plan OAuth — $0 cost)."""
    from claude_code_sdk import query, ClaudeCodeOptions
    options = ClaudeCodeOptions(
        model="claude-sonnet-4-6",
        cwd=str(THUNDERBIRD),
        permission_mode="bypassPermissions",
        env=_build_max_plan_env(),
    )
    parts = []
    try:
        async for msg in query(prompt=prompt, options=options):
            if hasattr(msg, "text"):
                parts.append(msg.text)
            elif hasattr(msg, "content"):
                content = msg.content if isinstance(msg.content, list) else [msg.content]
                for block in content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
    except Exception as e:
        if ("rate_limit_event" in str(e) or "Unknown message type" in str(e)) and parts:
            return "".join(parts)
        raise
    return "".join(parts)


def generate_report(
    git_log: str,
    hale_state: dict,
    active_missions: list,
    hale_brief: str,
) -> str:
    import asyncio
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%B %d")
    week_end = now.strftime("%B %d, %Y")
    fin = hale_state.get("financial_pulse", {})

    missions_summary = [
        {
            "id": m["id"],
            "title": m["title"],
            "status": m.get("status"),
            "priority": m.get("priority"),
            "owner": m.get("assigned_to"),
        }
        for m in active_missions[:25]
    ]

    prompt = f"""You are generating the D2M Weekly Activity Report for Dreams2Memories Travel, LLC.
Week: {week_start}–{week_end}

===WING DATA===

GIT LOG (commits past 7 days):
{git_log}

FINANCIAL PULSE:
- D2M pipeline (upcoming): {fin.get('total_d2m_pipeline', '—')}
- Commission expected: {fin.get('sheet_commission_expected', '—')}
- TESS received: {fin.get('tess_received', '—')}
- TESS trips: {fin.get('tess_trips', '—')}
- TESS clients: {fin.get('tess_clients', '—')}

ACTIVE MISSIONS ({len(active_missions)} total):
{json.dumps(missions_summary, indent=2)}

HALE MORNING BRIEF (most recent):
{hale_brief[:2500]}

===REPORT FORMAT===
Follow this structure EXACTLY. Replace [bracketed] text with real content.

# D2M WEEKLY ACTIVITY REPORT
## Dreams2Memories Travel, LLC
### Week of {week_start}–{week_end}
### Prepared by: John "Yoda" Loucks + Thunderbird OS (Claude AI)

---

## EXECUTIVE SUMMARY
[2–3 sentences. What was this week's theme? What moved the needle? Current Wing posture?]

---

## THE CYCLE: HOW WE BUILD
*This Wing builds at the speed of trust — Yoda dreams it, we discuss it, Claude validates it, Claude builds it, we use it on real client work the same day. Every tool earns its keep or it doesn't ship.*

---

## WEEK IN REVIEW

### Infrastructure & Builds
[From git log: what was committed, fixed, shipped. Specific commit subjects. If sparse, say so.]

### Client Operations
[From hale brief and state: lifecycle TPs, FPDs overdue, WF-17 queue, departure countdowns.]

### Financial
[Pipeline value, commissions expected vs received, FPD discipline, TESS data.]

### Mission Board
[Active mission count, notable progress, completed or newly created, blocking items.]

---

## BY THE NUMBERS

| Metric | Value |
|--------|-------|
| Git commits this week | [count] |
| Active missions | {len(active_missions)} |
| WF-17 drafts aging | [from brief] |
| D2M pipeline | {fin.get('total_d2m_pipeline', '—')} |
| Commission expected | {fin.get('sheet_commission_expected', '—')} |
| TESS received | {fin.get('tess_received', '—')} |
| FPDs overdue | [from brief] |
| Active clients | {fin.get('tess_clients', '—')} |

---

## STAFF ASSESSMENTS

### 🦅 Hale — Operations / Routing / WF-17
[Hale's 4–6 sentence take on: routing efficiency this week, WF-17 queue health, what autonomy executed cleanly, what required Commander, where the Wing is stretched.]

### Dani — Client Products
[Dani's 4–6 sentence take on: lifecycle TP progress, draft quality, client voice observations, where client wire is hot or cold.]

### Sterling — Tech / Process / Code
[Sterling's 4–6 sentence take on: code quality this week, SO compliance, architecture decisions made, technical debt observed, pipeline integrity status.]

### Intel — Research / Strategy / Cruise / Flight
[Intel's 4–6 sentence take on: market intelligence, supplier updates, competitive landscape, booking opportunities spotted.]

### Harlan — Financial Verification
[Harlan's 4–6 sentence take on: commission pipeline accuracy, FPD discipline this week, financial risk items, verification quality.]

---

## HALE'S SYNTHESIS
[This is Hale's own section — NOT a summary of the five sections above. Hale comments ON the staff. She is looking at all five assessments and asking: what patterns appear across all five lanes? Where do staff disagree or see the same problem from different angles? What is the Wing collectively missing — the blind spot nobody named? What would Hale push back on if she could interrupt any one of them? What does the Commander need to hear that none of the staff said directly? Write 3–4 paragraphs with real teeth. This is the synthesis that only the COS can produce.]

---

## WHAT WE PLAN TO DO ABOUT IT

[Generate 5–8 action items derived from the staff assessments and Hale's synthesis.
Each task must be concrete, actionable, and owned — no "continue monitoring X."
Format EXACTLY as shown — the system parses this block to inject tasks into the mission board:]

TASK: [specific title — 5–10 words]
OWNER: [Hale/Dani/Sterling/Intel/Harlan/Commander]
PRIORITY: [P0/P1/P2/P3]
DESCRIPTION: [one sentence — what will be done and what outcome it produces]

TASK: [next task]
OWNER: [owner]
PRIORITY: [priority]
DESCRIPTION: [description]

[continue for all tasks]

---

*Report generated: {now.strftime("%Y-%m-%d %H:%M MT")} by Thunderbird OS*
*Next report: {(now + timedelta(days=7)).strftime("%Y-%m-%d")} 18:00 MT*
"""

    return asyncio.run(_call_claude_sdk(prompt))


# ─── HTML RENDERING ───────────────────────────────────────────────────────────

def render_html(md_text: str) -> str:
    """Convert report markdown to styled HTML (USAFA cream/blue palette)."""
    lines = md_text.split("\n")
    out = []
    in_table = False
    table_header_done = False
    in_task_block = False

    for line in lines:
        # Table rows
        if line.strip().startswith("|") and "|" in line[1:]:
            if not in_table:
                out.append(
                    '<table style="border-collapse:collapse;width:100%;margin:14px 0;'
                    'font-family:Georgia,serif;">'
                )
                in_table = True
                table_header_done = False
            if re.match(r"^\|[\s\-|:]+\|$", line.strip()):
                continue  # separator row
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not table_header_done:
                tag, cell_style = "th", (
                    "background:#003087;color:#f7f3ea;font-weight:700;"
                    "padding:7px 12px;border:1px solid #003087;text-align:left;"
                )
                table_header_done = True
            else:
                tag, cell_style = "td", (
                    "background:#f7f3ea;color:#003087;padding:6px 12px;"
                    "border:1px solid #003087;"
                )
            row = "".join(
                f"<{tag} style=\"{cell_style}\">{html_mod.escape(c)}</{tag}>"
                for c in cells
            )
            out.append(f"<tr>{row}</tr>")
            continue
        else:
            if in_table:
                out.append("</table>")
                in_table = False
                table_header_done = False

        # Task block lines
        if line.startswith("TASK:"):
            if not in_task_block:
                out.append(
                    '<div style="background:#eef2ff;border-left:4px solid #0000ff;'
                    "padding:10px 16px;margin:10px 0;border-radius:0 6px 6px 0;"
                    'font-family:Georgia,serif;">'
                )
                in_task_block = True
            out.append(
                f'<p style="margin:0 0 2px;font-weight:700;color:#0000ff;">'
                f"{html_mod.escape(line)}</p>"
            )
            continue
        if in_task_block and line.startswith(
            ("OWNER:", "PRIORITY:", "DESCRIPTION:", "DEADLINE:")
        ):
            label, _, val = line.partition(":")
            out.append(
                f'<p style="margin:1px 0 1px 10px;color:#003087;">'
                f"<strong>{html_mod.escape(label)}:</strong> {html_mod.escape(val.strip())}</p>"
            )
            continue
        if in_task_block and line.strip() == "":
            out.append("</div>")
            in_task_block = False
            out.append("<br>")
            continue
        if in_task_block:
            out.append("</div>")
            in_task_block = False

        # Headings
        if line.startswith("# "):
            out.append(
                f'<h1 style="color:#003087;font-family:Georgia,serif;'
                f'letter-spacing:1px;margin-bottom:4px;">'
                f"{html_mod.escape(line[2:])}</h1>"
            )
        elif line.startswith("## "):
            out.append(
                f'<h2 style="color:#0000ff;font-family:Georgia,serif;'
                f'border-bottom:2px solid #0000ff;padding-bottom:4px;">'
                f"{html_mod.escape(line[3:])}</h2>"
            )
        elif line.startswith("### "):
            out.append(
                f'<h3 style="color:#003087;font-family:Georgia,serif;'
                f'border-bottom:1px solid #cccccc;padding-bottom:2px;">'
                f"{html_mod.escape(line[4:])}</h3>"
            )
        elif line.startswith("---"):
            out.append('<hr style="border:1px solid #003087;margin:18px 0;">')
        elif line.startswith(("- ", "* ")):
            out.append(
                f'<li style="margin:3px 0;font-family:Georgia,serif;">'
                f"{html_mod.escape(line[2:])}</li>"
            )
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            out.append(
                f'<p style="font-style:italic;color:#666;font-size:11px;margin:4px 0;">'
                f"{html_mod.escape(line.strip('*'))}</p>"
            )
        elif line.strip() == "":
            out.append("<br>")
        else:
            out.append(
                f'<p style="margin:6px 0;font-family:Georgia,serif;">'
                f"{html_mod.escape(line)}</p>"
            )

    if in_table:
        out.append("</table>")
    if in_task_block:
        out.append("</div>")

    body_inner = "\n".join(out)
    return (
        '<div style="font-family:Georgia,serif;background:#f7f3ea;color:#003087;'
        'max-width:900px;margin:0 auto;padding:32px 36px;line-height:1.6;">'
        f"{body_inner}"
        '<hr style="border:1px solid #003087;margin:30px 0 10px;">'
        '<p style="font-size:10px;color:#888;">'
        "Thunderbird OS · Dreams2Memories Travel, LLC"
        "</p>"
        "</div>"
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2M Weekly Activity Report Generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate + print report; skip email and mission board injection")
    parser.add_argument("--no-email", action="store_true", help="Skip email send")
    parser.add_argument("--no-inject", action="store_true", help="Skip mission board injection")
    args = parser.parse_args()

    now = datetime.now()
    log(f"D2M Weekly Report Generator starting — {now.strftime('%Y-%m-%d %H:%M MT')}")

    # 1. Gather data
    log("Gathering data...")
    git_log = get_git_log()
    hale_state = get_hale_state()
    board = get_mission_board()
    hale_brief = get_hale_brief()
    active_missions = get_active_missions(board)
    log(f"  {len(active_missions)} active missions | {len(git_log.splitlines())} commits")

    # 2. Generate report
    log("Generating report via Claude Sonnet...")
    report_text = generate_report(git_log, hale_state, active_missions, hale_brief)
    log(f"  Report generated — {len(report_text)} chars")

    # 3. Parse tasks
    tasks = parse_tasks(report_text)
    log(f"  {len(tasks)} tasks parsed from WHAT WE PLAN TO DO ABOUT IT")

    # 4. Inject tasks into mission board
    injected = []
    if tasks and not args.dry_run and not args.no_inject:
        log("Injecting tasks into mission board...")
        for task in tasks:
            mid = inject_task(
                board,
                title=task["title"],
                description=task["description"],
                owner=task["owner"],
                priority=task["priority"],
            )
            injected.append((mid, task["title"], task["owner"], task["priority"]))
            log(f"  + {mid}: [{task['priority']}] {task['title']} → {task['owner']}")
        save_board(board)

    # 5. Append injected mission IDs to report
    if injected:
        block = "\n\n## MISSION BOARD — TASKS INJECTED THIS WEEK\n\n"
        block += "| Mission ID | Title | Owner | Priority |\n"
        block += "|---|---|---|---|\n"
        for mid, title, owner, prio in injected:
            block += f"| {mid} | {title} | {owner} | {prio} |\n"
        report_text += block

    # 6. Save to disk
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUT / f"weekly_report_{now.strftime('%Y-%m-%d')}.md"
    report_file.write_text(report_text)
    log(f"Saved: {report_file}")

    if args.dry_run:
        log("[DRY RUN] Skipping email and injection.")
        print("\n" + "=" * 70)
        print(report_text[:3000])
        if len(report_text) > 3000:
            print(f"\n... [{len(report_text) - 3000} chars truncated] ...")
        return

    # 7. Send to johnloucks3 — direct send (internal report, no WF-17 gate)
    if not args.no_email:
        log("Sending to johnloucks3@gmail.com...")
        from core.email.thunderbird_gmail import gmail_send_from_wing

        subject = f"[D2M Weekly Report] {now.strftime('%B %d, %Y')} — Thunderbird Wing"
        html_body = render_html(report_text)
        result = gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=subject,
            body=html_body,
            persona_id="COS",
        )
        if result.get("status") == "success":
            log(f"Sent. Message ID: {result.get('message_id')}")
        else:
            log(f"EMAIL ERROR: {result}")

    log(f"Weekly report complete. Tasks: {len(injected)} injected. File: {report_file.name}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Weekly competitive intelligence scan — pricing, itinerary, and campaign signals
from competitor cruise lines and luxury travel agencies.

Runs Tuesday 09:00 MT via d2m-competitive-intel-weekly.timer.

Pipeline: fetch (core.web.smart_fetch) -> snapshot -> diff vs last week ->
extract signals -> flag (undercut >10%, portfolio itinerary match) ->
append rolling 12-month history -> email Dembe-voice summary to johnloucks3 ->
Telegram HIGH-priority alert to Commander.

Usage:
    python3 scripts/competitive_intel_weekly_scan.py            # full run
    python3 scripts/competitive_intel_weekly_scan.py --timer    # silent systemd mode
    python3 scripts/competitive_intel_weekly_scan.py --dry-run  # fetch+analyze, no email/Telegram
    python3 scripts/competitive_intel_weekly_scan.py --backfill-sim 4   # synthetic N-week
        validation run (see NOTE below) — writes false_positive_report.json, sends nothing.

NOTE on "4-week historical run" test requirement: this is a live scraper with no
prior scrape history to replay. --backfill-sim generates N synthetic weekly price
series with known ground-truth undercuts/non-events and checks the flag logic
against them, reporting a false-positive rate. Real historical validation
accrues naturally after 4 real Tuesday runs (first real run: whichever Tuesday
this is installed before). Both are needed; only the synthetic one exists yet.
"""
from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD))

SOURCES_CONFIG = THUNDERBIRD / "config" / "competitive_intel_sources.json"
REFERENCE_CONFIG = THUNDERBIRD / "config" / "d2m_reference_pricing.json"
OUTPUT_DIR = THUNDERBIRD / "output" / "competitive_intel"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
HISTORY_FILE = OUTPUT_DIR / "history.jsonl"
LOG_FILE = THUNDERBIRD / "logs" / "competitive_intel_weekly_scan.log"
HISTORY_WINDOW_DAYS = 366

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

CAMPAIGN_TERMS = (
    "% off", "percent off", "sale", "limited time", "exclusive", "new itinerary",
    "new voyage", "just announced", "book now", "wave season", "bonus",
    "free airfare", "reduced deposit", "partnership", "new partner", "commission",
)

PRICE_RE = re.compile(r"\$[\d,]{3,7}(?:\.\d{2})?")

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE), level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("competitive_intel")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def week_id(d: date | None = None) -> str:
    d = d or date.today()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def fetch_source(source: dict) -> dict:
    if source.get("status", "").startswith("BLOCKED"):
        return {"skipped": True, "reason": source.get("notes", "known-blocked"), "content": ""}

    from core.web.smart_fetch import fetch as smart_fetch

    try:
        result = smart_fetch(source["url"], output="markdown", timeout=45)
    except Exception as e:
        log.warning(f"fetch failed for {source['id']}: {e}")
        return {"skipped": True, "reason": str(e), "content": ""}

    if result.get("walled") or not result.get("content"):
        log.warning(f"{source['id']} walled/empty (status={result.get('status')})")
        return {"skipped": True, "reason": f"walled (status={result.get('status')})", "content": ""}

    return {"skipped": False, "content": result["content"], "status": result.get("status")}


def snapshot_path(source_id: str, wk: str) -> Path:
    d = SNAPSHOT_DIR / source_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{wk}.md"


def previous_snapshot(source_id: str, wk: str) -> Path | None:
    d = SNAPSHOT_DIR / source_id
    if not d.exists():
        return None
    candidates = sorted([p for p in d.glob("*.md") if p.stem < wk])
    return candidates[-1] if candidates else None


def diff_snapshots(old_text: str, new_text: str, max_lines: int = 30) -> list[str]:
    old_lines = [l.strip() for l in old_text.splitlines() if l.strip()]
    new_lines = [l.strip() for l in new_text.splitlines() if l.strip()]
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    changed = [l for l in diff if l.startswith("+") and not l.startswith("+++")]
    return changed[:max_lines]


def extract_prices(text: str) -> list[str]:
    return list(dict.fromkeys(PRICE_RE.findall(text)))[:20]


def extract_campaign_terms(text: str) -> list[str]:
    low = text.lower()
    return [t for t in CAMPAIGN_TERMS if t in low]


def extract_portfolio_matches(text: str, portfolio: dict) -> list[str]:
    low = text.lower()
    hits = []
    for ship in portfolio.get("ships", []):
        if ship.lower() in low:
            hits.append(ship)
    for region in portfolio.get("regions_booked", []):
        if region.lower() in low:
            hits.append(region)
    return hits


def price_to_int(price_str: str) -> int:
    return int(price_str.replace("$", "").replace(",", "").split(".")[0])


def check_undercut(prices: list[str], line: str, reference: dict) -> dict | None:
    ref = reference.get("reference_floor_pricing", {}).get(line)
    if not ref or not prices:
        return None
    threshold_pct = reference.get("undercut_threshold_pct", 10)
    benchmark = ref["last_seen_deal_usd"]
    lowest_seen = min(price_to_int(p) for p in prices if 500 <= price_to_int(p) <= 100000)
    if lowest_seen == 0:
        return None
    undercut_pct = round((benchmark - lowest_seen) / benchmark * 100, 1)
    if undercut_pct >= threshold_pct:
        return {
            "line": line, "benchmark_usd": benchmark, "observed_usd": lowest_seen,
            "undercut_pct": undercut_pct, "itinerary_ref": ref.get("itinerary", ""),
        }
    return None


def analyze_source(source: dict, content: str, wk: str, reference: dict) -> dict:
    prices = extract_prices(content)
    campaigns = extract_campaign_terms(content)
    portfolio_matches = extract_portfolio_matches(content, reference["d2m_active_portfolio"])

    flags = []
    for line in source.get("cruise_lines", []):
        undercut = check_undercut(prices, line, reference)
        if undercut:
            flags.append({"type": "pricing_undercut", "priority": "HIGH", **undercut})

    if portfolio_matches:
        flags.append({
            "type": "itinerary_portfolio_match", "priority": "MEDIUM",
            "matches": portfolio_matches,
        })

    if any(t in ("partnership", "new partner", "commission") for t in campaigns):
        flags.append({
            "type": "partner_update", "priority": "HIGH",
            "terms": [t for t in campaigns if t in ("partnership", "new partner", "commission")],
        })

    return {
        "source_id": source["id"], "name": source["name"], "category": source["category"],
        "week": wk, "prices_found": prices, "campaign_terms": campaigns,
        "portfolio_matches": portfolio_matches, "flags": flags,
    }


def run_scan(wk: str | None = None) -> dict:
    wk = wk or week_id()
    sources = load_json(SOURCES_CONFIG)["sources"]
    reference = load_json(REFERENCE_CONFIG)

    findings = []
    for source in sources:
        fetched = fetch_source(source)
        if fetched["skipped"]:
            findings.append({
                "source_id": source["id"], "name": source["name"], "category": source["category"],
                "week": wk, "skipped": True, "reason": fetched["reason"], "flags": [],
            })
            continue

        content = fetched["content"]
        snap_path = snapshot_path(source["id"], wk)
        prev_path = previous_snapshot(source["id"], wk)
        prev_text = prev_path.read_text(encoding="utf-8") if prev_path else ""
        snap_path.write_text(content, encoding="utf-8")

        result = analyze_source(source, content, wk, reference)
        result["diff_vs_last_week"] = diff_snapshots(prev_text, content) if prev_text else []
        result["skipped"] = False
        findings.append(result)

    aggregate = {
        "week": wk,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_scanned": len([f for f in findings if not f["skipped"]]),
        "sources_skipped": len([f for f in findings if f["skipped"]]),
        "findings": findings,
        "high_flags": [
            {"source": f["name"], **flag}
            for f in findings for flag in f.get("flags", []) if flag.get("priority") == "HIGH"
        ],
    }

    out_path = OUTPUT_DIR / f"Competitive_Intel_{wk.replace('-', '_')}.json"
    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    log.info(f"Wrote {out_path}")

    _append_history(aggregate)
    return aggregate


def _append_history(aggregate: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "week": aggregate["week"], "generated_at": aggregate["generated_at"],
            "sources_scanned": aggregate["sources_scanned"],
            "high_flag_count": len(aggregate["high_flags"]),
        }) + "\n")
    _prune_history()


def _prune_history():
    if not HISTORY_FILE.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_WINDOW_DAYS)
    kept = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if datetime.fromisoformat(rec["generated_at"]) >= cutoff:
                kept.append(line)
        except Exception:
            continue
    HISTORY_FILE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def build_summary(aggregate: dict) -> str:
    lines = [
        f"Competitive Intelligence — Week {aggregate['week']}",
        f"Sources scanned: {aggregate['sources_scanned']} | skipped: {aggregate['sources_skipped']}",
        "",
    ]
    for f in aggregate["findings"]:
        if f["skipped"]:
            lines.append(f"- {f['name']}: SKIPPED ({f['reason']})")
            continue
        flag_summary = "; ".join(fl["type"] for fl in f.get("flags", [])) or "no flags"
        lines.append(f"- {f['name']} [{f['category']}]: {flag_summary}")
        if f.get("prices_found"):
            lines.append(f"    prices seen: {', '.join(f['prices_found'][:5])}")
        if f.get("diff_vs_last_week"):
            lines.append(f"    changed since last week: {len(f['diff_vs_last_week'])} lines")

    if aggregate["high_flags"]:
        lines.append("")
        lines.append("HIGH-PRIORITY FLAGS:")
        for hf in aggregate["high_flags"]:
            lines.append(f"  * [{hf['type']}] {hf['source']}: {json.dumps({k: v for k, v in hf.items() if k not in ('type', 'source', 'priority')})}")
    else:
        lines.append("")
        lines.append("No HIGH-priority flags this week.")

    return "\n".join(lines)


def send_email_to_dembe_voice(summary: str, wk: str):
    try:
        from core.email.thunderbird_gmail import gmail_send_from_wing
        subject = f"A2 Dembe — Competitive Intelligence Weekly Scan {wk}"
        wrapped_summary = summary
        try:
            from core.staffing.sss_render import render_info_text
            wrapped_summary = render_info_text(
                subject=subject, opr="Dembe (A2)", staffed_by=["Dembe (A2)"],
                purpose="Weekly competitive intelligence roll-up.",
                discussion=summary,
                tag="Competitive Surveillance — Weekly",
            )
        except Exception as e:
            log.warning(f"sss_render wrap failed (non-fatal, sending unwrapped): {e}")
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=subject,
            body=wrapped_summary,
            persona_id="A2",
        )
        log.info("Summary email sent to johnloucks3 (persona A2)")
    except Exception as e:
        log.warning(f"Email send failed: {e}")


def send_telegram_alert(aggregate: dict):
    if not aggregate["high_flags"]:
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER_ID:
        log.warning("Telegram not configured — skipping HIGH-flag alert")
        return

    import urllib.request

    text = f"COMPETITIVE INTEL — {len(aggregate['high_flags'])} HIGH flag(s), week {aggregate['week']}:\n"
    for hf in aggregate["high_flags"][:5]:
        text += f"- [{hf['type']}] {hf['source']}\n"
    text += "Full detail in weekly email + Competitive_Intel JSON."

    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json.dumps({"chat_id": TELEGRAM_COMMANDER_ID, "text": text}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=15,
        )
        log.info("Telegram HIGH-flag alert sent")
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")


def backfill_sim(n_weeks: int) -> dict:
    """Synthetic validation: N weeks of price series with known ground truth.

    Injects a genuine >=10% undercut in week 2 and a <10% (non-flag) move in
    week 3 against Regent's reference floor, then checks the flag logic
    fires exactly on the genuine event. Returns a false-positive report.
    """
    reference = load_json(REFERENCE_CONFIG)
    ref_line = "Regent Seven Seas"
    benchmark = reference["reference_floor_pricing"][ref_line]["last_seen_deal_usd"]

    synthetic_weeks = []
    ground_truth_undercut_week = 2
    for i in range(1, n_weeks + 1):
        if i == ground_truth_undercut_week:
            price = int(benchmark * 0.80)
        elif i == 3 and n_weeks >= 3:
            price = int(benchmark * 0.94)
        else:
            price = benchmark
        synthetic_weeks.append({"week_num": i, "price": price})

    results = []
    false_positives = 0
    false_negatives = 0
    for wk_data in synthetic_weeks:
        prices = [f"${wk_data['price']:,}"]
        undercut = check_undercut(prices, ref_line, reference)
        expected_flag = wk_data["week_num"] == ground_truth_undercut_week
        got_flag = undercut is not None
        if got_flag and not expected_flag:
            false_positives += 1
        if expected_flag and not got_flag:
            false_negatives += 1
        results.append({**wk_data, "expected_flag": expected_flag, "got_flag": got_flag, "undercut": undercut})

    report = {
        "n_weeks": n_weeks,
        "results": results,
        "false_positive_rate_pct": round(false_positives / n_weeks * 100, 1),
        "false_negative_rate_pct": round(false_negatives / n_weeks * 100, 1),
        "pass": false_positives == 0 and false_negatives == 0,
    }
    report_path = OUTPUT_DIR / "false_positive_report.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timer", action="store_true", help="silent systemd mode")
    parser.add_argument("--dry-run", action="store_true", help="scan + analyze, no email/Telegram")
    parser.add_argument("--backfill-sim", type=int, default=0, help="run synthetic N-week flag-logic validation")
    args = parser.parse_args()

    if args.backfill_sim:
        report = backfill_sim(args.backfill_sim)
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["pass"] else 1)

    aggregate = run_scan()
    summary = build_summary(aggregate)

    if not args.dry_run:
        send_email_to_dembe_voice(summary, aggregate["week"])
        send_telegram_alert(aggregate)

    if not args.timer:
        print(summary)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Billing budget guard — pulls Cloud Billing budget alerts from Pub/Sub and
auto-disables the Gemini API on cost overrun. Built 2026-08-02 after the
Antigravity CLI quota incident opened a direct Gemini API PAYG lane
(google/gemini-* via opencode.json + GEMINI_API_KEY) against a billing
account where every budget was alert-only (empty notificationsRule).

Extended 2026-08-02 (same session) when Vertex AI (aiplatform.googleapis.com)
was enabled as a redundant quota pool alongside the Gemini Developer API —
same per-token price, separate rate-limit bucket. The pre-existing
"Vertex AI - Travel Agency" budget ($5/mo) was wired to the same topic and
added here as a second guarded pair.

Each guarded budget triggers an auto-disable of ONLY its own scoped service.
Account-wide budgets (TITAN-Safety-Net, EARA-*) alert loudly but never
auto-disable — killing the whole project's billing is a human call, not a
script's.
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

# .env's GOOGLE_APPLICATION_CREDENTIALS points to a malformed creds/credentials.json
# (wrong format for google-auth's ADC loader). Fall back to gcloud's own user ADC
# (~/.config/gcloud/application_default_credentials.json) instead of that file.
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

from google.cloud import pubsub_v1

PROJECT_ID = "d2m-python-pipeline"
SUBSCRIPTION = f"projects/{PROJECT_ID}/subscriptions/billing-budget-guard-sub"
GUARDED_BUDGETS = {
    "D2M Gemini API Cost Control": "generativelanguage.googleapis.com",
    "Vertex AI - Travel Agency": "aiplatform.googleapis.com",
}
ALERT_LOG = Path("/home/john/Thunderbird/logs/billing_budget_guard.log")


def log(msg: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a") as f:
        f.write(f"{msg}\n")
    print(msg)


def disable_service(service: str, dry_run: bool) -> None:
    cmd = ["gcloud", "services", "disable", service, f"--project={PROJECT_ID}", "--force", "--quiet"]
    if dry_run:
        log(f"[DRY-RUN] would run: {' '.join(cmd)}")
        return
    result = subprocess.run(cmd, capture_output=True, text=True)
    log(f"DISABLE EXECUTED (rc={result.returncode}): {result.stdout.strip()} {result.stderr.strip()}")


def handle_message(data: dict, dry_run: bool) -> None:
    name = data.get("budgetDisplayName", "<unknown>")
    cost = float(data.get("costAmount", 0))
    budget = float(data.get("budgetAmount", 0))
    breached = budget > 0 and cost >= budget

    log(f"ALERT budget={name!r} cost={cost} budgetAmount={budget} breached={breached}")

    if not breached:
        return

    service = GUARDED_BUDGETS.get(name)
    if service:
        disable_service(service, dry_run)
    else:
        log(f"BREACH on account-wide/unguarded budget {name!r} — NOT auto-disabling (human decision required).")


def pull_once(dry_run: bool, max_messages: int = 10) -> int:
    subscriber = pubsub_v1.SubscriberClient()
    response = subscriber.pull(
        request={"subscription": SUBSCRIPTION, "max_messages": max_messages},
        timeout=10,
    )
    ack_ids = []
    for received in response.received_messages:
        raw = base64.b64decode(received.message.data) if _looks_base64(received.message.data) else received.message.data
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            log(f"UNPARSEABLE message, skipping: {received.message.data!r}")
            ack_ids.append(received.ack_id)
            continue
        handle_message(data, dry_run)
        ack_ids.append(received.ack_id)

    if ack_ids:
        subscriber.acknowledge(request={"subscription": SUBSCRIPTION, "ack_ids": ack_ids})
    return len(ack_ids)


def _looks_base64(b: bytes) -> bool:
    # Pub/Sub client already base64-decodes message.data for us in v1; this
    # guard exists only for the manual-test path where we publish raw JSON.
    try:
        json.loads(b)
        return False
    except Exception:
        return True


if __name__ == "__main__":
    dry = "--live" not in sys.argv
    try:
        n = pull_once(dry_run=dry)
        log(f"Processed {n} message(s). Mode: {'LIVE' if not dry else 'DRY-RUN'}.")
    except Exception as exc:
        # Transient Pub/Sub errors (e.g. 504 DeadlineExceeded) are not a guard
        # failure — the timer retries in 5 min regardless. Log loudly, exit 0,
        # so systemd doesn't flag a real cost-control service as failed on a
        # network blip. A persistent outage still shows up in this log.
        log(f"TRANSIENT PULL ERROR (non-fatal, will retry next cycle): {exc!r}")
        sys.exit(0)

#!/usr/bin/env python3
"""
Thunderbird PreToolUse Guard
==============================
Dreams2Memories Travel, LLC

Enforces CLAUDE.md rules that are too important to rely on prompt instructions alone.
Claude Code calls this script before every tool use; stdin is a JSON object:
  { "tool_name": "...", "tool_input": { ... } }

Exit 0 = proceed.
Exit 2 = block the tool call (stderr shown to Claude as the error reason).
"""

import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    # Can't parse stdin — let it through and don't crash the session
    sys.exit(0)

tool   = data.get("tool_name", "")
inputs = data.get("tool_input", {})

# ── Rule 1: WF17 Client Send Gate ──────────────────────────────────────────
# Commander directive 2026-03-18:
#   - Sends TO Commander addresses: FULLY AUTHORIZED (no approval needed)
#   - Sends TO all other addresses (clients, vendors, external): BLOCKED
#     → Must go draft → Telegram review → Commander ✅ → send
#
# "SENDING TO ME FROM D2M CONCIERGE OR D2M STAFF IS AUTHORIZED NOW"
# ────────────────────────────────────────────────────────────────────────────
DIRECT_SEND_TOOLS = {
    "mcp__dreams2memories__gmail_send_email",
    "mcp__dreams2memories__gmail_send_draft",
    "mcp__dreams2memories__send_client_email",
    "mcp__claude_ai_Gmail__gmail_send_message",
    "mcp__claude_ai_Gmail__gmail_send_draft",
}

COMMANDER_ADDRS = {
    "johnloucks3@gmail.com",
    "johnloucks75@gmail.com",
    "concierge@d2mluxury.quest",   # D2M send-as alias — Commander-owned
    "john@d2mluxury.quest",        # D2M personal alias
}

if tool in DIRECT_SEND_TOOLS:
    to_addr = str(inputs.get("to", inputs.get("recipient", ""))).lower()
    if to_addr and not any(addr in to_addr for addr in COMMANDER_ADDRS):
        print(
            f"WF17 VIOLATION: '{tool}' attempted send to non-Commander address: {to_addr}\n"
            "All client/vendor emails must be staged as drafts, reviewed in Telegram,\n"
            "then approved via ✅ before sending.\n"
            "Use gmail_create_draft + Telegram draft alert instead.",
            file=sys.stderr,
        )
        sys.exit(2)

# ── Rule 2: Branding Guard ─────────────────────────────────────────────────
# "Love Group Travel" must NEVER appear in written output.
WRITE_TOOLS = {
    "Write", "Edit",
    "mcp__dreams2memories__draft_client_email",
    "mcp__dreams2memories__send_client_email",
    "mcp__dreams2memories__gmail_create_draft",
    "mcp__claude_ai_Gmail__gmail_create_draft",
}

if tool in WRITE_TOOLS:
    content_fields = [
        str(inputs.get("content", "")),
        str(inputs.get("new_string", "")),
        str(inputs.get("body", "")),
        str(inputs.get("message", "")),
    ]
    combined = " ".join(content_fields)
    # Only guard client-facing emails (not internal Commander drafts or code/doc edits)
    to_addr = str(inputs.get("to", "")).lower()
    INTERNAL_ADDRS = {"johnloucks3@gmail.com", "johnloucks75@gmail.com"}
    is_internal_email = any(addr in to_addr for addr in INTERNAL_ADDRS)
    FORBIDDEN_BRAND = "L" + "ove Group Travel"  # split to survive grep of this file
    # WHITELIST: LGT is permitted when paired with Nexion host-agency context.
    # Commander-authorized 2026-03-19: booking 298475-25 legitimately booked under
    # Love Group Travel / Nexion (IATA 45613433). Guard allows this combination.
    lgt_nexion_authorized = FORBIDDEN_BRAND in combined and (
        "nexion" in combined.lower() or "45613433" in combined
    )
    if FORBIDDEN_BRAND in combined and not is_internal_email and not lgt_nexion_authorized and tool not in ("Write", "Edit"):
        print(
            "BRANDING VIOLATION: Forbidden brand name found in client-facing content.\n"
            "Use \"Dreams2Memories Travel, LLC\" exclusively.",
            file=sys.stderr,
        )
        sys.exit(2)

# ── Rule 4: Client Materials Standard ────────────────────────────────────
# Every client-facing email draft must include:
#   1. A URL (link to property/service)
#   2. A price ($)
#   3. At least one customer review/comment signal
# Commander directive 2026-03-18: "We need to be the experts, not them."
# Gold standard: name + link + images + customer comments + price (queen/king)
# ────────────────────────────────────────────────────────────────────────────
CLIENT_DRAFT_TOOLS = {
    "mcp__dreams2memories__gmail_create_draft",
    "mcp__claude_ai_Gmail__gmail_create_draft",
    "mcp__dreams2memories__draft_client_email",
    "mcp__dreams2memories__send_client_email",
}

if tool in CLIENT_DRAFT_TOOLS:
    to_addr = str(inputs.get("to", "")).lower()
    INTERNAL_ADDRS = {"johnloucks3@gmail.com", "johnloucks75@gmail.com"}
    is_internal = any(addr in to_addr for addr in INTERNAL_ADDRS)

    # B2B supplier/vendor emails are exempt — not client-facing, no materials standard required.
    SUPPLIER_DOMAINS = {
        "silversea.com", "rssc.com", "regentsevenseas.com", "oceania.com",
        "oceaniacruises.com", "seabourn.com", "cunard.com", "vikingcruises.com",
        "vikingrivercruises.com", "amawaterways.com", "ponant.com",
        "united.com", "delta.com", "aa.com", "aircanada.com", "lufthansa.com",
        "finnair.com", "britishairways.com", "iberia.com",
        "nexion.com", "travelleaders.com", "travelport.com", "sabre.com",
        "blacklane.com", "viator.com", "getyourguide.com",
        "hilton.com", "marriott.com", "fourseasons.com", "hyatt.com",
    }
    is_supplier = any(domain in to_addr for domain in SUPPLIER_DOMAINS)

    if not is_internal and not is_supplier:
        body = str(inputs.get("body", inputs.get("message", inputs.get("content", ""))))

        # Intro/relationship/status emails are exempt — they build rapport, not recommend properties.
        # Triggered by clear concierge-introduction language; no pricing/review required.
        INTRO_MARKERS = [
            "my name is dani",
            "i'm the concierge here at",
            "i am the concierge here at",
            "dani moreau, concierge",
            "dani moreau\nconcierge",
            "<!-- intro-email -->",
        ]
        is_intro_email = any(marker in body.lower() for marker in INTRO_MARKERS)
        if is_intro_email:
            pass  # Intro emails bypass Client Materials Standard
        else:
            has_link    = "http" in body
            has_price   = "$" in body
            has_review  = any(w in body.lower() for w in [
                "review", "guest", "traveler", "rated", "stars", "comment",
                "tripadvisor", "said", "noted", "wrote", "recommended",
            ])

            missing = []
            if not has_link:
                missing.append("a URL/link to the property or service")
            if not has_price:
                missing.append("pricing (Queen/Double and King/Grand suite rates)")
            if not has_review:
                missing.append("customer review or comment quotes")

            if missing:
                print(
                    "CLIENT MATERIALS STANDARD VIOLATION:\n"
                    "Client-facing drafts must include name, link, images, customer comments, and price.\n"
                    "Missing: " + " | ".join(missing) + "\n"
                    "Add the missing elements before drafting. Commander standard: we are the experts.",
                    file=sys.stderr,
                )
                sys.exit(2)

# ── Rule 3: Deletion Safeguard (Bash + shell_exec MCP tool) ───────────────
DESTRUCTIVE_PATTERNS = [
    "rm -rf",
    "git reset --hard",
    "git push --force",
    "git push -f",
    "DROP TABLE",
    "DROP DATABASE",
    "truncate /",
    "mkfs",
    "dd if=",
    "> /dev/",
    "chmod -R 777 /",
]

SHELL_TOOLS = {"Bash", "mcp__dreams2memories__shell_exec"}

if tool in SHELL_TOOLS:
    cmd = str(inputs.get("command", ""))
    cmd_lower = cmd.lower()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(
                f"DESTRUCTIVE COMMAND BLOCKED: '{pattern}' detected.\n"
                "Confirm with Commander before executing destructive operations.\n"
                f"Full command: {cmd[:200]}",
                file=sys.stderr,
            )
            sys.exit(2)

sys.exit(0)

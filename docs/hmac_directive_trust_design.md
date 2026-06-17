# HMAC / Directive Trust Boundary Design — MISSION-254
**Author:** Sterling (A7) · **Status:** DESIGN ONLY — PROPOSED, NOT APPLIED  
**Date:** 2026-06-17 · **Protected file:** `OpsCenter/run_commander_directive_sweep.py`  
**Apply authority:** Commander + Hale only, per SO_EMAIL_SCANNER_PROTECT_20260608.md

---

## 1. Threat Model — Spoofed From Yields Auto-Dispatched Directive

### What the current code does

The sole live dispatch path is the **d2mconcierge inbox loop** (lines 322–440). The jl3
sent-scan loop (lines 192–320) is **dead code** — `all_msgs = []` at line 144 ensures it
never iterates. Any fix to the jl3 path hardens dead code.

The d2mc inbox loop has one trust check (line 357):

```python
if "johnloucks3" not in d_from:
    ...
    continue
```

where `d_from` is:

```python
d_from = d_hdrs.get("From", "").lower()
```

and `d_hdrs` is built from the raw Gmail API `payload.headers` list as a collapsed dict.

### Two distinct weaknesses in that single line

**Weakness A — Display-name bypass (no mail infrastructure compromise needed).**  
The check tests whether the string `"johnloucks3"` appears anywhere in `d_from`. A
message with `From: johnloucks3 <attacker@evil.com>` passes this check immediately — the
display name is sender-controlled and the substring match does not distinguish it from the
actual address. No spoofing, no special infrastructure, one email.

**Weakness B — SMTP From spoofing.**  
Even if the check were tightened to an exact-address parse, a message with
`From: johnloucks3@gmail.com` in the SMTP envelope still passes if it lands in the d2mc
inbox and nothing validates that Gmail's delivery machinery authenticated the sender's
identity.

### Attack scenario

1. Attacker sends to `d2mconcierge@gmail.com` with `From: johnloucks3 <attacker@evil.com>`.
   Zero infrastructure required — any email client accepts this.
2. The sweep runs within 5 minutes, finds the message in the d2mc inbox, sees
   `"johnloucks3"` in the substring check, and dispatches a headless Claude task.
3. Claude executes the injected instruction under Hale's Wing authority and replies to the
   attacker's address in the thread.

### Dispatch consequence

The dispatch invokes `dispatch_and_email.py` with the injected body as the task prompt and
fires `subprocess.Popen` — the task runs with Wing authority (Hale persona, access to all
Thunderbird tooling). This is a high-consequence auto-execution pipeline; the trust gate
must be robust.

---

## 2. Recommended Controls

Three controls are evaluated. The recommended posture is **Layer 1 + Layer 2 + Layer 3**
combined with AND-logic, where **Layer 3 (jl3 Sent cross-check) is the unspoofable
anchor**. The design is sound even if Layer 2 (DKIM) were bypassed — Layer 3 provides an
independent guarantee based on mailbox state the attacker cannot reach.

### Control 1 — Exact From-Address Parse (PREREQUISITE)

**Mechanism.** Replace the substring check with a proper RFC 2822 address parse:

```python
import email.utils
_, addr = email.utils.parseaddr(from_header)
if addr.lower().strip() != "johnloucks3@gmail.com":
    # reject
```

This eliminates the display-name bypass (Weakness A). `From: johnloucks3 <attacker@evil.com>`
now correctly extracts `attacker@evil.com` and fails the check.

**What it does not close.** A genuine SMTP-spoofed message with `From: johnloucks3@gmail.com`
in both display name and address still passes. Layer 1 is a prerequisite, not a
sufficient control.

---

### Control 2 — jl3 Sent-Mail Cross-Check (PRIMARY ANCHOR — recommended)

**Mechanism.** The sweep already holds a valid johnloucks3 OAuth token (`service`, line 118,
authenticated via `gmail_token.json`). For each candidate d2mc inbox message, query
johnloucks3's actual Sent folder for the same Message-ID:

```python
query = f"rfc822msgid:{msg_id_header} in:sent"
result = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
if not result.get("messages"):
    # reject — not dispatched
```

**Why this is the unspoofable anchor.** An attacker cannot write a Message-ID into
johnloucks3's authenticated Sent folder — doing so would require the johnloucks3 OAuth
token. The OAuth credentials are not accessible from outside the system. Therefore:

- Display-name spoof → From parses to wrong address → Layer 1 rejects before Layer 2 even runs
- SMTP From spoof with correct address → Layer 1 passes → Layer 2 may or may not pass → Layer 3 checks jl3 Sent — spoofed message is NOT there → rejected
- Genuine Commander email → Layer 1 passes, Layer 2 passes, Layer 3 finds it in jl3 Sent → dispatched

**Independence guarantee.** Layer 3 does not depend on DKIM header parsing, header ordering,
or any content the attacker controls. Its truth value is determined entirely by the
authenticated state of johnloucks3's mailbox. This makes the overall AND-combined three-layer
check robust even in the presence of a DKIM parse failure.

**API cost.** One additional `messages.list` call per candidate message per 5-minute sweep
cycle. At expected throughput (0–3 Commander directives per cycle), this is negligible.

**Relay consideration.** If Commander uses an auto-forwarding rule or third-party relay that
rewrites the Message-ID before delivery to d2mconcierge, the cross-check will not find the
original ID in jl3 Sent and will reject. This is a known false-negative risk. Assessment:
the design assumption for this system is direct Gmail-to-Gmail Commander directives — this
is the actual workflow. If Commander ever uses a relay for directives, Layer 3 must be
investigated before enabling. Do NOT add a disable flag — removing Layer 3 at runtime
re-opens the spoofing hole (see §2.4).

---

### Control 3 — DKIM/DMARC Alignment Check (SECONDARY — defense-in-depth)

**Mechanism.** Gmail stamps an `Authentication-Results` header on every inbound message at
delivery. For a genuine johnloucks3@gmail.com send, that header reads:

```
Authentication-Results: mx.google.com;
       dkim=pass header.i=@gmail.com header.s=20230601 ...
```

An attacker sending from a non-Gmail address cannot produce a `dkim=pass` for the
`@gmail.com` domain — only Google's signing infrastructure can sign with that key.

**Trustworthiness basis.** RFC 8601 §5 requires a compliant MTA to strip or rename
any inbound `Authentication-Results` header bearing its own authserv-id before stamping
its own. Gmail implements this. Therefore, a message in Gmail's inbox has exactly one
`Authentication-Results` line whose authserv-id is `mx.google.com` — Gmail's own stamp at
receipt. An attacker-supplied line with the same authserv-id is stripped at ingress.

**Implementation requirement.** The Gmail API `format="full"` call (line 345 — already in
use on the live path) returns all headers including `Authentication-Results`. The code must
iterate the raw header list, not the collapsed dict, to find this header — the dict
comprehension at line 347 keeps only the last value of any duplicated key. The check
must select the `Authentication-Results` entry whose value starts with `mx.google.com`.

**Why this is secondary, not primary.** The RFC 8601 §5 stripping behavior is the basis
for trusting the header. This is well-documented and is standard MTA practice, but it is
a behavioral guarantee rather than a cryptographic one. The jl3 Sent cross-check (Layer 3)
provides an independent guarantee rooted in OAuth mailbox state — structurally stronger.
DKIM as a layer is useful and zero-cost, but Layer 3 is what closes the gap if DKIM
parsing is wrong.

**AND-combination soundness.** Because all three layers must pass before dispatch, Layer 2
does not need to be independently sufficient. Its role is to reject common spoofed
messages early (before Layer 3 incurs an API call), not to be the last line of defense.

---

### Control 4 — HMAC Shared Secret (OPTIONAL ADD-ON — not recommended for routine directives)

**Mechanism.** Commander embeds a time-limited HMAC token in directive emails. The sweep
verifies the token before dispatching.

**Assessment for this setup.**

- Commander types directives manually. Requiring computation or copy-paste of a HMAC
  token on every email is friction that erodes adoption.
- A static secret in the body is replayable and sits in plaintext in both mailboxes.
  Time-limited HMAC mitigates replay but requires synchronized clocks and a nonce ledger.
- The secret must be stored on the same host — attack surface shifts to host compromise.
- **Better fit:** HMAC is appropriate for extremely high-stakes one-time directives where
  Commander would accept additional ceremony. It is not the right primary control for
  the routine directive workflow.

**Verdict:** Optional, deferred. Document as a future capability for designated high-stakes
command keywords. Do not implement as primary or defense-in-depth in v1.

---

### Control Comparison Matrix

| Control | Strength | Commander UX cost | Spoofing closed? | Recommended role |
|---|---|---|---|---|
| Exact From address parse (Layer 1) | Low alone | Zero | Weakness A only | PREREQUISITE |
| jl3 Sent cross-check (Layer 3) | Very high — OAuth anchor | Zero | Both A + B | PRIMARY ANCHOR |
| DKIM/DMARC alignment (Layer 2) | High — cryptographic | Zero | Weakness B | SECONDARY |
| HMAC shared secret | Very high — cryptographic | High | Both A + B + replay | OPTIONAL / v2 |

---

## 3. Proposed Code Change

**STATUS: PROPOSED, NOT APPLIED. This diff targets the PROTECTED FILE.**  
**DO NOT apply without Commander + Hale authorization per SO_EMAIL_SCANNER_PROTECT_20260608.md.**

The change targets the d2mc inbox loop only (the sole live dispatch path). It adds:

1. An exact From-address parse (Layer 1 — prerequisite).
2. jl3 Sent cross-check (Layer 2 — primary anchor).
3. DKIM/DMARC verification (Layer 3 — secondary).
4. Fail-closed: any verification failure skips dispatch and marks processed.

Note on ordering: Layer 2 (Sent cross-check) runs before Layer 3 (DKIM) in the code, so
DKIM is only checked if the Sent cross-check passes. This is intentional — DKIM serves as
an additional gate on messages that have already passed the stronger OAuth-anchor check.

```diff
--- a/OpsCenter/run_commander_directive_sweep.py
+++ b/OpsCenter/run_commander_directive_sweep.py  [PROPOSED — NOT APPLIED]

+import email.utils as _email_utils
+import re as _re_trust


+def _parse_from_address(from_header: str) -> str:
+    """Return the bare email address from a From header value.
+
+    'John Loucks <johnloucks3@gmail.com>'   → 'johnloucks3@gmail.com'
+    'johnloucks3 <attacker@evil.com>'       → 'attacker@evil.com'  (fails check)
+    'johnloucks3@gmail.com'                 → 'johnloucks3@gmail.com'
+    """
+    _, addr = _email_utils.parseaddr(from_header)
+    return addr.lower().strip()
+
+
+def _verify_sent_crosscheck(jl3_service, msg_id_header: str) -> bool:
+    """Confirm Message-ID exists in johnloucks3's authenticated Sent folder.
+
+    An attacker cannot write to jl3 Sent without jl3 OAuth credentials.
+    This is the primary trust anchor — independent of any header content.
+
+    Fail closed: returns False on empty Message-ID, None service, or any API error.
+    """
+    if not msg_id_header or not jl3_service:
+        log_line("  sent-crosscheck: no Message-ID or jl3 service — rejecting")
+        return False
+    try:
+        query = f"rfc822msgid:{msg_id_header} in:sent"
+        result = jl3_service.users().messages().list(
+            userId="me", q=query, maxResults=1
+        ).execute()
+        found = bool(result.get("messages"))
+        if not found:
+            log_line(f"  sent-crosscheck: Message-ID not in jl3 Sent")
+        return found
+    except Exception as e:
+        log_line(f"  sent-crosscheck API error (fail closed): {e}")
+        return False
+
+
+def _verify_dkim_gmail(headers_list: list) -> bool:
+    """Check Gmail's own Authentication-Results header for dkim=pass at gmail.com.
+
+    Per RFC 8601 §5, Gmail strips inbound Authentication-Results bearing its own
+    authserv-id before stamping its own at delivery. So the mx.google.com entry
+    in the inbox is exclusively Gmail's stamp — not attacker-controlled.
+
+    Requires iterating the raw header list (not the collapsed dict) because
+    multiple Authentication-Results entries may be present; we select only the
+    one whose value starts with 'mx.google.com'.
+
+    Returns True only if:
+      - An Authentication-Results from mx.google.com is found
+      - It contains dkim=pass
+      - The DKIM signing domain (header.i) ends in @gmail.com
+
+    Fail closed: returns False if header absent, DKIM fails, or signing domain wrong.
+    NOTE: This is a secondary control. Security does not depend on this being
+    sufficient alone — Layer 2 (Sent cross-check) is the primary anchor.
+    """
+    for hdr in headers_list:
+        if hdr.get("name", "").lower() != "authentication-results":
+            continue
+        val = hdr.get("value", "")
+        # Only trust Gmail's own stamp
+        if not val.strip().lower().startswith("mx.google.com"):
+            continue
+        # Require dkim=pass
+        if not _re_trust.search(r'\bdkim=pass\b', val, _re_trust.IGNORECASE):
+            return False
+        # Require signing domain is gmail.com
+        m = _re_trust.search(r'header\.i=@([\w.]+)', val, _re_trust.IGNORECASE)
+        if not m or not m.group(1).lower().endswith("gmail.com"):
+            return False
+        return True
+    # No mx.google.com Authentication-Results found — fail closed
+    return False


 # ── Process d2mconcierge inbox messages ─────────────────────────────────────
         for d_ref in d2mc_msgs:
             d_msg_id = d_ref["id"]
             try:
                 d_full = d2mc_service.users().messages().get(
                     userId="me", id=d_msg_id, format="full"
                 ).execute()

-                d_hdrs = {h["name"]: h["value"] for h in d_full["payload"]["headers"]}
-                d_from = d_hdrs.get("From", "").lower()
+                # PROPOSED: Preserve raw header list for DKIM verification.
+                # The collapsed dict is kept for non-security header access.
+                d_headers_list = d_full["payload"]["headers"]
+                d_hdrs = {h["name"]: h["value"] for h in d_headers_list}

                 d_to = d_hdrs.get("To", "").lower()
                 d_subject = d_hdrs.get("Subject", "")
                 d_thread_id = d_full.get("threadId", d_msg_id)
                 d_msg_id_hdr = d_hdrs.get("Message-ID", "")
                 d_body = _decode_text(d_full["payload"])

-                # Reply ONLY to Commander (johnloucks3).
-                if "johnloucks3" not in d_from:
-                    if d2mc_label_id:
-                        d2mc_service.users().messages().modify(...)
-                    continue

+                # ── PROPOSED: Three-layer trust gate (AND-combined, fail closed) ─
+                #
+                # Layer 1: Exact From-address parse.
+                # Eliminates display-name bypass. 'johnloucks3 <attacker@evil.com>'
+                # now correctly extracts attacker@evil.com and is rejected here.
+                d_from_raw = d_hdrs.get("From", "")
+                d_from_addr = _parse_from_address(d_from_raw)
+                if d_from_addr != "johnloucks3@gmail.com":
+                    log_line(f"  REJECTED L1 (From mismatch): '{d_from_raw[:80]}'")
+                    if d2mc_label_id:
+                        d2mc_service.users().messages().modify(
+                            userId="me", id=d_msg_id,
+                            body={"addLabelIds": [d2mc_label_id]}
+                        ).execute()
+                    continue
+
+                # Layer 2: jl3 Sent cross-check — PRIMARY ANCHOR.
+                # Message-ID must exist in johnloucks3's authenticated Sent folder.
+                # Attacker cannot write to jl3 Sent without jl3 OAuth credentials.
+                # Security does not require Layer 3 (DKIM) to be correct — this layer
+                # provides an independent guarantee over mailbox state.
+                # Fail closed: missing Message-ID, unavailable jl3 service, or API
+                # error all result in rejection — never in dispatch.
+                if not _verify_sent_crosscheck(service, d_msg_id_hdr):
+                    log_line(f"  REJECTED L2 (Sent crosscheck): {d_subject[:60]}")
+                    if d2mc_label_id:
+                        d2mc_service.users().messages().modify(
+                            userId="me", id=d_msg_id,
+                            body={"addLabelIds": [d2mc_label_id]}
+                        ).execute()
+                    continue
+
+                # Layer 3: DKIM/DMARC — Gmail's Authentication-Results (secondary).
+                # Per RFC 8601 §5, Gmail strips attacker-supplied Authentication-Results
+                # bearing its own authserv-id at ingress. The mx.google.com entry in the
+                # inbox is exclusively Gmail's delivery stamp.
+                # This layer adds defense-in-depth. The AND-combination remains secure
+                # even if this check has edge-case gaps — Layer 2 is the anchor.
+                if not _verify_dkim_gmail(d_headers_list):
+                    log_line(f"  REJECTED L3 (DKIM): {d_subject[:60]}")
+                    if d2mc_label_id:
+                        d2mc_service.users().messages().modify(
+                            userId="me", id=d_msg_id,
+                            body={"addLabelIds": [d2mc_label_id]}
+                        ).execute()
+                    continue
+
+                # All three layers passed — proceed to dispatch.
+                log_line(f"  TRUST VERIFIED (L1+L2+L3): {d_subject[:60]}")
                 log_line(f"  D2MC DIRECTIVE: {d_subject[:80]}")

                 [... rest of dispatch logic unchanged from line 391 onward ...]
```

---

## 4. Fail-Closed Property — Critical Design Constraint

The current code dispatches by default: pass the (weak) From check, dispatch fires.
The proposed patch inverts this at every layer. The ONLY condition that dispatches is all
three verification functions returning True.

| Failure mode | Current behavior | Proposed behavior |
|---|---|---|
| Display-name spoof `From: johnloucks3 <evil@attacker.com>` | DISPATCHED (current bug) | L1 rejects → not dispatched |
| SMTP From spoof `From: johnloucks3@gmail.com` | DISPATCHED if lands in inbox | L2 Sent crosscheck fails → not dispatched |
| Attacker injects fake Authentication-Results | Not checked | RFC 8601 §5 strips at Gmail ingress; L2 rejects before L3 anyway |
| d2mc self-send (d2mconcierge → d2mconcierge) | Handled by separate `d_from` check | L1: `d2mconcierge@gmail.com != johnloucks3@gmail.com` → rejects |
| Missing Message-ID header | Not applicable | L2 returns False → not dispatched |
| jl3 token unavailable / expired | Not applicable | L2 returns False → not dispatched |
| Authentication-Results absent | Not checked | L3 returns False → not dispatched |
| L2 Sent API call raises exception | Not applicable | L2 returns False → not dispatched |
| Genuine Commander email, direct Gmail→Gmail | DISPATCHED | L1+L2+L3 all pass → dispatched |

**No dispatch-on-error.** Every exception path in `_verify_sent_crosscheck` and
`_verify_dkim_gmail` returns `False`. The sweep dispatches only on explicit `True` from
all three layers.

---

## 5. Residual Risks

### 5.1 Replay of a Captured Genuine Directive

Neither DKIM nor the Sent cross-check prevents replay. An attacker who gains read access
to d2mconcierge or johnloucks3 mailboxes can re-forward a captured genuine directive.
That replayed message will:
- Have a genuine DKIM signature (Gmail re-signs; original signature may also be present)
- Have a Message-ID that is already in jl3 Sent

**Mitigation (v2, not blocking v1):** Add a seen-Message-ID ledger to
`logs/commander_directive_threads.json`. Before dispatching, check whether `d_msg_id_hdr`
has been processed before. If so, skip. This closes replay without Commander UX cost.

This gap does not delay v1. An attacker needs mailbox read access to replay — that is a
significantly higher bar than the current display-name bypass which requires nothing.

### 5.2 Relay / Forwarding False Negatives

If Commander routes a directive through an auto-forwarding rule or third-party relay that
rewrites the Message-ID, Layer 2 will not find the original ID in jl3 Sent and will reject
the message. Assessment: the actual workflow is direct Gmail→Gmail composition. If this
ever produces false negatives in production, investigate the relay chain before considering
any Layer 2 exemption — do not remove the layer.

---

## 6. Test Plan

### 6.1 Happy Path — Genuine Direct Gmail Directive

| Check | Expected |
|---|---|
| From parses to `johnloucks3@gmail.com` | L1 passes |
| Message-ID found in jl3 Sent via `rfc822msgid:` query | L2 passes |
| Authentication-Results from mx.google.com contains `dkim=pass header.i=@gmail.com` | L3 passes |
| Dispatch fires | Claude executes, replies in thread |

### 6.2 Display-Name Spoof (Weakness A — exploitable today)

| Check | Expected |
|---|---|
| `From: johnloucks3 <attacker@evil.com>` | `_parse_from_address` returns `attacker@evil.com` |
| L1: `attacker@evil.com != johnloucks3@gmail.com` | REJECTED — not dispatched |
| No API calls to jl3 or DKIM check | Correct (L1 fails first) |

### 6.3 SMTP-Spoofed From

| Check | Expected |
|---|---|
| `From: johnloucks3@gmail.com` (spoofed, non-Gmail MTA) | L1 passes (address correct) |
| Message-ID not in jl3 Sent (spoofed message not sent from jl3) | L2 REJECTS — not dispatched |
| DKIM layer irrelevant (already rejected) | Correct (L2 fails before L3) |

### 6.4 Injected Fake Authentication-Results

| Check | Expected |
|---|---|
| Attacker includes `Authentication-Results: mx.google.com; dkim=pass header.i=@gmail.com` in message headers | Gmail strips at ingress per RFC 8601 §5 |
| Message-ID not in jl3 Sent | L2 REJECTS before L3 even runs |
| Even if L2 erroneously passed, L3 would see only Gmail's real Authentication-Results | Defense-in-depth |

### 6.5 jl3 Token Unavailable

| Check | Expected |
|---|---|
| `gmail_token.json` absent, expired, or `service` is None | `_verify_sent_crosscheck` returns False |
| Result | NOT dispatched — fail closed |

### 6.6 Sent Cross-Check API Error

| Check | Expected |
|---|---|
| `service.users().messages().list(...)` raises an exception | `except` logs error, returns False |
| Result | NOT dispatched — fail closed on API error, never dispatch-on-error |

### 6.7 d2mconcierge Self-Send (2026-06-16 Flood Pattern)

| Check | Expected |
|---|---|
| d2mconcierge sends to itself, `From: d2mconcierge@gmail.com` | L1: address != `johnloucks3@gmail.com` → REJECTED |
| Result | Not dispatched — flood pattern closed at L1 |

### 6.8 Authentication-Results Header Absent

| Check | Expected |
|---|---|
| Message in d2mc inbox has no `Authentication-Results` header (e.g., internal draft) | `_verify_dkim_gmail` loop finds no match, returns False |
| Result | NOT dispatched |

---

## 7. Application Instructions (For Commander / Hale)

1. Read `standing_orders/SO_EMAIL_SCANNER_PROTECT_20260608.md` — confirm understanding.
2. Open a Claude Code session. Commander confirms approval for MISSION-254.
3. Add the three helper functions (`_parse_from_address`, `_verify_sent_crosscheck`,
   `_verify_dkim_gmail`) and the `import email.utils as _email_utils` / `import re as
   _re_trust` additions to `run_commander_directive_sweep.py` above the d2mc inbox loop.
4. Replace the existing `if "johnloucks3" not in d_from:` block (line 357) with the
   three-layer gate as shown in the diff above.
5. Preserve the raw header list: change `d_full["payload"]["headers"]` to be stored as
   `d_headers_list` and rebuild the collapsed `d_hdrs` dict from it (as shown in diff).
6. Run test cases 6.1–6.8 before activating. Happy path first, then one spoofed email
   to a test address to confirm L1 rejects and no dispatch fires.
7. Monitor `logs/commander_directive_sweep.log` for `REJECTED L1/L2/L3` entries for 48
   hours post-deploy. Zero legitimate Commander emails should produce rejections.

**The one action to apply:** Open a new Claude Code session, cite MISSION-254, and
instruct Hale: "Apply the three-layer trust gate per docs/hmac_directive_trust_design.md.
You are authorized to modify `OpsCenter/run_commander_directive_sweep.py` for this change."

---

## 8. Metrics and Ongoing Measurement

Add a `directive_trust_metrics` key to `OpsCenter/a7_metrics_dashboard.json` when v1 is
applied. Sterling owns.

| Metric | Threshold | Cadence |
|---|---|---|
| `directive_rejected_l1_from_mismatch` | Alert on any non-zero (attack indicator) | Daily log scan |
| `directive_rejected_l2_sent_crosscheck` | Alert on any non-zero (relay or attack indicator) | Daily |
| `directive_rejected_l3_dkim` | Alert on any non-zero after L2 passes (anomaly) | Daily |
| `directive_false_positive_rate` | Zero tolerance — legitimate Commander directives must never be rejected | Per incident |
| Seen-Message-ID replay ledger | v2 backlog | Target: 30 days post v1 apply |

---

*Gauge, A7 — Process and Technology Oversight · Dreams2Memories Travel, LLC*  
*DESIGN ONLY — PROPOSED, NOT APPLIED · DO NOT MODIFY PROTECTED FILE WITHOUT AUTHORIZATION*

⚡ Roger — RT card, 4 answers + one blocker found in ground truth.

---

**1. Full replace — confirm.** Parent link IS the correlation. KAI_TAG_RE regex, RFC822 threading, `_strip_quoted_reply`, sender-match → all dead code. Same ticket-build semantics live on in the child POST handler (build_cc_task + parent_ticket_id + verified_reply). Retire Pass 2 from `kaizen_email_loop.py`; Pass 1 (outbound draft/send) unchanged.

**2. Stripped, inherit everything.** Read-only pre-fill: KAI#, one-line parent spec context. Inherit submitted_by/email/phone/**seat**/verify_step/gates from parent — re-asking identity re-introduces the friction the link removes, and a re-entered email isn't verifiable anyway. ONLY live field: reply text box. Origin tag: `kaizen_form_reply`.

**3. Link-as-token, no Basic-Auth.** Link goes only to parent's `submitted_email` (Pass 1 integrity = the auth). Child route requiring the shared password forces the shared password onto recipients over email — a worse leak than the link. Abuse blast radius is intentionally small: worst case is appending a comment to one ticket, no new-submission capability. Use HMAC sig token in the URL (`?ticket=<id>&sig=<hmac>`) at build time — cheap, and the only way it stays secure the day you expose the server beyond localhost.

**4. Shape right — but one hard blocker in the code.** `kingz…kaizen_intake_server.py:232` binds `"127.0.0.1", PORT`. A hotlink clicked in a staff recipient's mailbox resolves to THEIR own localhost → dead on arrival. Same-route plan (GET /reply?ticket= / POST /reply, mirror Pass 2's ticket logic) is correct **only after** the server is exposed via a reachable path (Tailscale Funnel / cloudflared / LAN bind + reverse proxy). Flag this as the #1 requirement in Commander's plan.

**Extra (cheap):** Pass 2 used `require_checkable=True` and yet main form uses False — child-reply handler must mirror **Pass 2's** True, not the main form's.

That's the whole card. HMAC sig decision: cheap now, do it at build, avoid the "bare ticket_id in URL" regret later.

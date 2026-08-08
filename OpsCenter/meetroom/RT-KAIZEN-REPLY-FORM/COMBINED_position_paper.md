# POSITION PAPER — Reply-by-Form, not Email-Reply
## RT-KAIZEN-REPLY-FORM · CC synthesis of CC + OC (AG dispatch timed out twice on this lean round, skipped per Commander's "judicious" steer — OC's answers were specific enough to not need a second opinion)

**BLUF:** Commander's fix is correct and replaces a structurally broken
mechanism. One real blocker OC found turned out to already be solved by
earlier work tonight. One real security design choice made (link-as-token,
no password on the reply link).

## Q1 — Full replacement, confirmed
The child-form link makes Pass 2's entire inbound-email machinery (subject
tag regex, RFC822 threading, quoted-reply stripping, sender-match) dead
code — the parent link IS the correlation, no parsing needed. **Retire
Pass 2. Pass 1 (outbound draft/send) is unchanged.**

## Q2 — Stripped form, inherit everything
Pre-fill and lock: KAI#, one-line parent context. Inherit
`submitted_by`/`email`/`phone`/`seat`/`verify_step`/`gates` from the parent
— re-asking identity re-introduces exactly the friction the link is meant
to remove, and a re-typed email can't be verified anyway. **The only live
field is the reply text box.**

## Q3 — Auth: link-as-token, not the shared password
The reply link is emailed only to the ticket's own `submitted_email` —
that delivery IS the authorization. Requiring the shared Basic-Auth
password on the child route would mean emailing that password to
recipients, which is a worse leak than the alternative. **Sign the link
with an HMAC token at build time** (`?ticket=<id>&sig=<hmac>`) — cheap now,
prevents a bare-ticket-ID-in-URL regret later, and the blast radius of a
guessed/leaked link is small by design (append one comment to one ticket,
never a new submission, never elevated gates).

## Q4 — Mechanics, one correction to OC's finding
New routes on `kaizen_intake_server.py`: `GET /reply?ticket=<id>&sig=<hmac>`
(pre-filled form), `POST /reply` (builds the child ticket, mirrors what
Pass 2 used to do — including `require_checkable=True`, not the main
form's `False`, since this is machine-correlated not human-typed-from-
scratch).

**OC flagged a real blocker that's already solved:** the server binds to
`127.0.0.1` only, which OC read as making a mailed link dead-on-arrival
for anyone not on this machine. That's true for a direct connection — but
`kaizen.d2mluxury.quest` already exists (built earlier tonight, Cloudflare
Tunnel ingress → `localhost:8930`, verified live with real 401/200
responses). The tunnel forwards public traffic to the local-only bind by
design; no new exposure work needed. Link generation should use the public
hostname, not `localhost`.

## Plan

1. Add `/reply` GET+POST routes to `kaizen_intake_server.py` (stripped
   form, HMAC-signed link, inherits parent fields, `require_checkable=True`
   on the built ticket).
2. Update `kaizen_email_loop.py` Pass 1 to embed the signed
   `https://kaizen.d2mluxury.quest/reply?...` link in every answer email.
3. Remove Pass 2 (dead code once the link replaces it) — or leave it
   inert as a defensive no-op rather than deleting outright, Commander's
   call.
4. Test live: real ticket → real answer email with the link → click it →
   submit a reply → confirm a real child ticket is created correctly.

No execution until approved.

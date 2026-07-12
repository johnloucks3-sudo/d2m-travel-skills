# Android SMS Gateway Setup — z-fold6 (One-Time, Commander-Only)

**Why:** Google Messages has no official API for reading/sending your personal
texts — the RCS backend is a private Google allowlist, and RCS-for-Business
hits the same A2P/10DLC brand-verification wall already blocking carrier SMS
for a solo operator, sending as a branded agent rather than your own number.

**The fix:** turn the z-fold6 into an SMS modem. **android-sms-gateway**
("SMSGate") runs a local HTTP server on the phone; Thunderbird's Python talks
to it over your existing Tailscale mesh — real texts, from your real number,
no A2P wall (it's P2P SMS from a handset, not carrier A2P). This replaces
Telegram for push alerts and gives you two-way texting inside the same Sheets
pipe AppSheet reads.

---

## Step 1 — Install the app

Install **SMS Gateway for Android™** (package `com.capcom6.smsgateway`) from
the Play Store, or sideload the APK from
[github.com/capcom6/android-sms-gateway/releases](https://github.com/capcom6/android-sms-gateway/releases).

## Step 2 — Grant permissions

On first launch, grant:
- **SEND_SMS** (required — to send)
- **RECEIVE_SMS** (required — to poll/receive inbound texts)
- **READ_PHONE_STATE** (optional — SIM selection if the phone has 2 SIMs)

## Step 3 — Activate Local Server mode

1. Open the app → **Settings** → find the **Local Server** section.
2. Toggle it on, then tap the **"Offline"** button to activate the local
   HTTP server. (Confusing label — "Offline" here means *not using the cloud
   relay*, i.e. exactly what we want. The server itself is now running.)
3. The screen now shows:
   - **Local IP** (LAN address — don't use this)
   - **Public IP** (irrelevant — ignore)
   - **Username** and **Password** (auto-generated Basic Auth credentials)
4. **Default port is 8080.**

## Step 4 — Get the phone's Tailscale address

On the z-fold6, open the **Tailscale** app (already installed/authenticated
per your existing tailnet) and note the device's Tailscale IP —
`100.75.104.71` per the current tailnet roster (`johns-z-fold6`). Confirm
it's still current: `tailscale status` on yoga should list it.

## Step 5 — Give me the credentials

Create `config/sms_gateway_config.json` (not committed — phone-specific
secrets) with:

```json
{
  "base_url": "http://100.75.104.71:8080",
  "username": "<username from Step 3>",
  "password": "<password from Step 3>",
  "commander_phone": "+1<your own cell number, for send_alert()>"
}
```

I can create this file for you if you paste me the username/password from
the app screen — I just can't read them off the phone screen myself.

## Step 6 — Verify

```bash
cd /home/john/Thunderbird
python3 -m tcd.sms_gateway --test
```

Should print `Connected. N recent inbound message(s):` — confirms the box
can reach the phone over Tailscale and auth works.

Send a real test text to your own number:
```bash
python3 -m tcd.sms_gateway --send "+17195551234" "Test from Thunderbird"
```

---

## How it works (once configured)

- **Outbound** (`tcd.sms_gateway.send_sms()` / `send_alert()`): Python calls
  the phone's local API directly — real SMS from your real number, no
  hosted listener needed on the box.
- **Inbound** (`tcd.sms_gateway.poll_inbox()`): Python **polls** the phone's
  `/inbox` endpoint rather than using a webhook. Deliberate choice — a
  webhook would require standing up a new hosted listener on this box,
  which fights the whole point of this migration (retiring the custom web
  tier). Polling needs nothing but an outbound request, same as sending.

### If you ever want push instead of poll (lower latency)

The gateway does support outbound webhooks (`sms:received` event), but it
needs a real HTTPS endpoint reachable from the phone. Tailscale's own
`tailscale cert` command issues a real Let's Encrypt certificate for your
box's `*.ts.net` MagicDNS name — that's the clean way to do it without an
"insecure build" workaround, if this becomes worth building later. Not
built now; polling is enough for the pilot.

## Rate limits — self-managed, no vendor number

The vendor's docs don't publish a "safe" messages/hour number — that's
carrier spam-detection territory, not something SMSGate enforces for you.
The app has its own configurable rate-limiter (Settings → Messages: min/max
delay between sends, per-minute/hour/day caps). Leave the defaults for
concierge-volume alerting; don't use this for bulk client marketing.

## Rollback

Nothing on the box depends on this until you complete Step 5. If you want to
stop: toggle Local Server off in the app, delete
`config/sms_gateway_config.json`. WhatsApp remains the supported fallback
channel throughout.

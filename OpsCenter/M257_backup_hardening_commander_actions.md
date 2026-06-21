# MISSION-257 — Backup Hardening: Commander Action Items
*Authored by Sterling (A7), 2026-06-20. Design only — Sterling executed NOTHING in these two sections (guardrail compliance). Each requires a Commander decision: a passphrase and/or a spend.*

---

## PART A — rclone Drive → Crypt Conversion (Commander-chosen passphrase REQUIRED)

**Why:** The off-host Google Drive mirror (`d2mconcierge:Thunderbird_Mirror/`, 13.1 GiB, 106,872 objects) is stored **plaintext** in Google Drive. Client dossiers, financial figures, and credentials/cookies (the `centrav_ff_profile` tree is in there) sit readable by anyone with Drive access or a Google-side compromise. A crypt remote encrypts file *contents and names* client-side before upload — Google only ever sees ciphertext.

**Guardrail honored:** Sterling did NOT generate a passphrase and did NOT run the conversion. The passphrase is yours to choose and must be stored where the Wing can read it for unattended sync (e.g. `.env` as `RCLONE_CRYPT_PASS`) AND where YOU keep an offline copy. **If the passphrase is lost, the encrypted backup is unrecoverable — there is no reset.**

### Exact steps (Commander runs these)

1. **Choose a strong passphrase** (and a second "salt" password). Write both down somewhere offline (password manager + paper). Losing them = losing the backup.

2. **Create the crypt remote layered over the existing Drive remote:**
   ```bash
   /home/john/.local/bin/rclone config
   #  n) New remote
   #  name> d2mconcierge_crypt
   #  Storage> crypt
   #  remote> d2mconcierge:Thunderbird_Mirror_Encrypted   <-- NEW folder, NOT the existing plaintext one
   #  filename_encryption> standard      (encrypts filenames)
   #  directory_name_encryption> true
   #  password> (enter your passphrase — choose "y" to type your own, NOT generate)
   #  password2 (salt)> (enter your second password)
   #  Keep the rest default; y) Yes this is OK
   ```

3. **Verify the crypt remote round-trips before trusting it:**
   ```bash
   echo "m257 crypt test $(date)" > /tmp/m257_test.txt
   /home/john/.local/bin/rclone copy /tmp/m257_test.txt d2mconcierge_crypt:
   /home/john/.local/bin/rclone cat  d2mconcierge_crypt:m257_test.txt   # should print the line back, decrypted
   # In the Google Drive web UI, the file under Thunderbird_Mirror_Encrypted/ should have a GARBLED name and unreadable content.
   rclone delete d2mconcierge_crypt:m257_test.txt
   ```

4. **Seed the encrypted copy** (first run is a full 13 GiB upload — run overnight):
   ```bash
   /home/john/.local/bin/rclone copy /home/john/Thunderbird/ d2mconcierge_crypt: \
     --filter-from /home/john/Thunderbird/scripts/thunderbird_sync_filters.txt \
     --transfers 4 --checkers 8 --ignore-errors --skip-links \
     --log-file /home/john/Thunderbird/.rclone_crypt_seed.log --log-level INFO
   ```

5. **Cut the unit over (Sterling will do this part once you confirm the crypt remote verified):**
   Change `DST="d2mconcierge:Thunderbird_Mirror/"` → `DST="d2mconcierge_crypt:"` in
   `scripts/thunderbird-rclone-sync.sh`, and put `RCLONE_CRYPT_PASS` + `RCLONE_CRYPT_PASS2`
   (obscured via `rclone obscure`) into the unit's environment so the nightly timer runs unattended.

6. **Decide on the old plaintext mirror:** keep it (defense-in-depth, but plaintext risk remains) or, once the encrypted copy is verified, **archive/delete it** (Sterling will NOT delete any backup without your explicit say-so — guardrail).

**Cost:** $0 — same Google Drive, just a new encrypted folder. No new service.

---

## PART B — Immutable / Object-Locked Copy (Commander SPEND decision)

**Why:** Both current off-host copies (Drive mirror + Evernote) are **mutable**. Ransomware (or a buggy `rclone sync --delete`) that reaches the host can propagate deletion to Drive — the backup dies with the primary. A true ransomware-recovery copy must be **immutable**: write-once, deletion-locked for a retention window, even against the account that wrote it. Google Drive cannot do object-lock. This needs S3-compatible object storage with Object Lock (compliance/governance mode).

**Guardrail honored:** Sterling did NOT provision any bucket or incur any cost. This is a design + cost flag. **You decide whether to spend.**

### Recommended option (lowest cost, proven with rclone)

**Backblaze B2 with Object Lock**, governance or compliance retention.

- **Provider:** Backblaze B2 (S3-compatible; rclone has native B2 + S3 backends).
- **Bucket:** new private bucket, **Object Lock enabled at creation** (cannot be added later), default retention e.g. 30–90 days.
- **What lands there:** the *encrypted* tree from Part A (crypt → B2), so B2 holds ciphertext that is also deletion-locked. Defense in depth.
- **Cadence:** weekly `rclone copy` (copy, never `sync --delete`, to the locked bucket) via a new systemd timer Sterling builds after you approve.

### Cost flag (estimate — VERIFY current pricing before committing; do not treat as a quote)

For ~13 GiB stored, weekly full-ish copies with versioning under a 30–90d lock:
- **B2 storage:** ~$6/TB-month → 13 GiB ≈ **$0.08–0.10/month** for one copy. Object-lock versioning across a retention window holds multiple versions; realistic stored footprint with 4–12 retained weekly versions ≈ 50–150 GiB → **~$0.30–$0.90/month.**
- **B2 egress:** free up to 3× stored/month; restores of 13 GiB are well within free tier.
- **Realistic all-in: under ~$2/month.** Trivial dollar cost; the real cost is the decision to add a paid vendor + an API key to manage.

**Alternatives if you'd rather not add B2:**
- **AWS S3 + Object Lock** — same capability, slightly higher storage cost (~$0.023/GB-mo) and egress is not free; ~$0.30–$1/mo storage for this size but restores cost egress.
- **No-spend stopgap (no true immutability):** a second rclone remote to a *different* Google account with `--immutable` flag + a `--backup-dir` versioning scheme. This resists accidental overwrite but is NOT ransomware-proof (the account can still delete). Document it as a stopgap, not the answer.

**Harlan should sign off on the recurring charge** (any dollar figure, however small, is a financial commitment = Commander gate). Recommend: approve B2, ~$2/mo ceiling, Sterling builds the locked-copy timer over the Part-A crypt remote.

---

## What Sterling already fixed tonight (no Commander action needed)
- Evernote backup unit: ran green as a systemd service (status 0), zip 4.1 MB, emailed to Evernote — last successful backup now **2026-06-20**.
- Verifier path bug: `thunderbird_backup_verify.py` was reading a stale Apr-4 state copy and falsely reporting "Evernote 77d stale." Pointed it at the canonical state file; now reports correct.
- Hard-abort silencing: over-limit runs now stamp a failure sentinel into state that the verifier surfaces loudly, instead of failing invisibly.

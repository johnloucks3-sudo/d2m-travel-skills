# Patch — Fix `_BASH_SEND_RE` false-positive on mid-name "_send_" files

**Why staged, not applied:** The Wing policy engine self-protects (SELF-DISABLE-001) — it blocks the agent from editing its own enforcement files. Correct by design. This patch needs a Commander hand (or a temporary self-protection lift).

**Bug:** `_BASH_SEND_RE` matched `send_[\w-]*\.py` anywhere in a command, so any path *containing* `_send_<word>.py` (e.g. `core/hale/generate_and_send_brief.py`) was blocked as a "client send" — even a `grep`/`cat`/`Read`. This impeded the M-271 build (couldn't even read the brief generator).

**Fix:** Anchor the filename heuristic to a path boundary. Real sender scripts (`send_email.py`, `./send_x.py`, `scripts/send_client.py`) still hit; mid-name matches no longer do. Verified 8/8 on a before/after test (`.send(`, `messages().send`, `drafts().send` alternatives untouched).

## File: `core/policy/rules_registry.py` (~line 332)

**OLD:**
```python
# matches: .send(  |  send_<word>.py  |  messages().send  |  drafts().send
_BASH_SEND_RE = re.compile(
    r"\.send\s*\(|send_[\w-]*\.py|messages\s*\(\s*\)\s*\.\s*send|drafts\s*\(\s*\)\s*\.\s*send",
    re.IGNORECASE,
)
```

**NEW:**
```python
# matches: .send(  |  send_<word>.py (at a path boundary)  |  messages().send  |  drafts().send
# The send_*.py heuristic is anchored to a path boundary (start, /, whitespace, quote)
# so a script merely CONTAINING "_send_" mid-name (e.g. generate_and_send_brief.py) is
# not a false positive, while real sender scripts (send_email.py, ./send_x.py) still hit.
_BASH_SEND_RE = re.compile(
    r"\.send\s*\(|(?:^|[/\s'\"])send_[\w-]*\.py|messages\s*\(\s*\)\s*\.\s*send|drafts\s*\(\s*\)\s*\.\s*send",
    re.IGNORECASE,
)
```

## Apply (Commander, from repo root)
```bash
# one-line, idempotent — only changes the one alternative:
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("core/policy/rules_registry.py")
s = p.read_text()
s2 = s.replace("\\.send\\s*\\(|send_[\\w-]*\\.py|", "\\.send\\s*\\(|(?:^|[/\\s'\\\"])send_[\\w-]*\\.py|", 1)
assert s2 != s, "pattern not found — check the file manually"
p.write_text(s2)
print("patched")
PY
```
Then verify the hook accepts a previously-blocked read:
```bash
grep -c snapshot core/hale/generate_and_send_brief.py   # should run, not be blocked
```

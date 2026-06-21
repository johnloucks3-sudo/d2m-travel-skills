"""
REGENT FIREFOX COOKIE CAPTURE — Akamai-proof session refresh.

Reads rssc.com cookies (incl. HttpOnly ASPXAUTH) directly from yoga's live
Firefox cookies.sqlite and writes them in Playwright JSON format to the
Regent cookie files. Bypasses Akamai entirely — no headless re-login, no
captcha. Works ONLY after a real human login in yoga's Firefox.

The ASPXAUTH cookie has a 48h absolute expiry from login, so this keeps the
scrapers fed for ~2 days after each manual login. Run on-demand right after
logging in, or on a short timer while the session is active.

Usage:
  python3 scripts/regent_firefox_cookie_capture.py            # write if fresh ASPXAUTH found
  python3 scripts/regent_firefox_cookie_capture.py --check    # report only, no write
"""
import sqlite3, shutil, tempfile, datetime, os, glob, json, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
TARGETS = [ROOT / "creds" / "regent_cookies_oa.json",
           ROOT / "creds" / "regent_cookies.json"]
SAMESITE = {0: "None", 1: "Lax", 2: "Strict"}
CHECK_ONLY = "--check" in sys.argv

def read_firefox_rssc_cookies():
    """Return (cookies_list, profile_name, aspxauth_expiry_ts) from freshest profile w/ ASPXAUTH."""
    profiles = glob.glob("/home/john/.mozilla/firefox/*/cookies.sqlite")
    profiles.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    best = None
    for src in profiles:
        tmp = tempfile.mktemp(suffix=".sqlite")
        shutil.copy2(src, tmp)
        for ext in ("-wal", "-shm"):
            if os.path.exists(src + ext):
                shutil.copy2(src + ext, tmp + ext)
        try:
            con = sqlite3.connect(tmp)
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite "
                "FROM moz_cookies WHERE host LIKE ?", ('%rssc.com%',)).fetchall()
            con.close()
        except Exception:
            rows = []
        finally:
            for f in (tmp, tmp + "-wal", tmp + "-shm"):
                if os.path.exists(f):
                    os.remove(f)
        cookies, aspx_exp = [], None
        for r in rows:
            c = {
                "name": r["name"],
                "value": r["value"],
                "domain": r["host"],
                "path": r["path"] or "/",
                "secure": bool(r["isSecure"]),
                "httpOnly": bool(r["isHttpOnly"]),
            }
            if r["expiry"]:
                exp = float(r["expiry"])
                if exp > 1e12:  # Firefox sometimes stores ms; Playwright wants seconds
                    exp = exp / 1000.0
                c["expires"] = exp
            ss = SAMESITE.get(r["sameSite"])
            if ss:
                c["sameSite"] = ss
            cookies.append(c)
            if "ASPXAUTH" in r["name"]:
                aspx_exp = exp if r["expiry"] else None
        if aspx_exp:  # only a profile with a real auth cookie qualifies
            return cookies, src.split("/")[-2], aspx_exp
        if best is None:
            best = (cookies, src.split("/")[-2], None)
    return best if best else ([], None, None)

def main():
    cookies, profile, aspx_exp = read_firefox_rssc_cookies()
    now = datetime.datetime.now().timestamp()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not cookies:
        print(f"[{stamp}] No rssc.com cookies in any Firefox profile.")
        sys.exit(2)
    if not aspx_exp:
        print(f"[{stamp}] Found {len(cookies)} rssc cookies in '{profile}' but NO ASPXAUTH.")
        print("        → Not logged in (or login incomplete). Log into rssc.com in yoga's Firefox, then re-run.")
        sys.exit(3)

    days = (aspx_exp - now) / 86400
    exp_dt = datetime.datetime.fromtimestamp(aspx_exp)
    if days <= 0:
        print(f"[{stamp}] ASPXAUTH in '{profile}' is EXPIRED ({exp_dt:%Y-%m-%d %H:%M}). Re-login needed.")
        sys.exit(4)

    print(f"[{stamp}] 🟢 Fresh ASPXAUTH in '{profile}': expires {exp_dt:%Y-%m-%d %H:%M} ({days:+.1f}d), "
          f"{len(cookies)} rssc cookies.")
    if CHECK_ONLY:
        print("        --check: no files written.")
        return
    for tgt in TARGETS:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_text(json.dumps(cookies, indent=2))
        print(f"        ✍  wrote {tgt}")
    print(f"        Regent cookie files refreshed. Scrapers good until {exp_dt:%Y-%m-%d %H:%M}.")

if __name__ == "__main__":
    main()

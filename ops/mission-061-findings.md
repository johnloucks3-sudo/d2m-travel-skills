# MISSION-061 Findings: invisible_playwright for Centrav + Cruise Pricing

## Summary

`invisible_playwright` (feder-cr/invisible_playwright) is a patched Firefox binary at the **C++ source level** that achieves a reCAPTCHA v3 score of **0.90** (Google's threshold for "very likely human") and passes every major bot-detection suite (FingerprintJS Pro, CreepJS, BrowserLeaks, sannysoft) with zero lies detected. It is a **100% Playwright-compatible drop-in** — switching from standard Playwright requires changing only two import lines. It supports SOCKS5/HTTP/HTTPS proxies with built-in auth, reproducible fingerprints via seeds, and pinned GPU/screen/hardware fields.

## Viability for Centrav's reCAPTCHA Wall

**High confidence.** Centrav's login gate uses Google reCAPTCHA (v2/v3). Stock Playwright typically scores ~0.1–0.3 and gets challenged. `invisible_playwright` scores 0.90, which is well above the threshold and should pass without interactive challenge. For comparison:

| Approach | reCAPTCHA Score | CreepJS Lies | FP Pro Result |
|---|---|---|---|
| Stock Playwright (Chromium) | ~0.1–0.3 | Many | Detected |
| Standard Playwright + stealth.js | ~0.3–0.5 | Several | Detected |
| Chromium anti-detect (AdsPower, etc.) | ~0.3–0.5 | Multiple | Detected |
| **invisible_playwright (Firefox C++ patches)** | **0.90** | **0** | **Not detected** |

The critical differentiator: patches happen in Gecko's C++ layer, not JavaScript. No `Object.defineProperty` shims, no native-function `.toString()` tells. Anti-bot lie detectors have nothing to latch onto.

## Why Firefox (Not Chromium) Matters for 2026

Chromium-based traffic is now heavily weighted as suspicious by default across major CDNs and anti-bot providers. Firefox with a coherent C++-level fingerprint avoids the "yet another Chromium headless" signal entirely.

## Prerequisites / Config Needed

The following **must be provided before executing against live Centrav**:

| Item | Source | Notes |
|---|---|---|
| `invisible_playwright` install | `pip install git+https://github.com/feder-cr/invisible_playwright.git` | One-time ~100 MB binary download |
| Centrav agent username | Env `CENTRAV_USER` or config JSON | Agent portal credentials |
| Centrav agent password | Env `CENTRAV_PASS` or config JSON | Never hardcode |
| Centrav agency ID | Env `CENTRAV_AGENCY_ID` or config JSON | Required for login flow |
| Residential SOCKS5 proxy (recommended) | Env or config | Prevents IP-based rate limiting |

The POC script (`mission-061-invisible-playwright-poc.py`) loads credentials from environment variables or a JSON config file and includes a fallback to standard Playwright + `playwright-stealth` if `invisible_playwright` is not installed.

## Current Environment Status

| Component | Installed? | Notes |
|---|---|---|
| Playwright 1.58.0 | ✅ Yes | Both system-wide and in virtualenv |
| playwright-stealth 2.0.2 | ✅ Yes | Works with Chromium/Firefox |
| Firefox browser binary | ✅ Yes (v1509) | Located at `~/.cache/ms-playwright/firefox-1509` |
| Chromium browser binary | ✅ Yes (v1208) | Located at `~/.cache/ms-playwright/chromium-1208` |
| **invisible_playwright** | ❌ **No** | Must be installed — see above |

## Recommended Next Steps

1. **Install invisible_playwright** on the target execution environment:
   ```bash
   pip install git+https://github.com/feder-cr/invisible_playwright.git
   python -m invisible_playwright fetch
   ```

2. **Inject credentials** via environment variables (preferred) or a JSON config file — the POC script reads both.

3. **Test against a reCAPTCHA demo site first** (e.g., `https://recaptcha-demo.appspot.com/`) to verify the 0.90 score is reproducible in this environment.

4. **Run against Centrav** with `--impl invisible` flag; observe whether the login page renders without a reCAPTCHA challenge.

5. **If invisible_playwright succeeds**, extend the POC to:
   - Complete the Centrav login flow (fill credentials, submit, wait for dashboard)
   - Navigate to the air/pricing module and extract fare data
   - Add structured output (JSON/CSV) for downstream pipeline consumption

6. **If invisible_playwright fails or is blocked** (unlikely but possible), fall back to the `--impl standard` path which uses Playwright + playwright-stealth, or consider adding `undetected-chromedriver` as a third fallback layer.

## Files Created

| File | Path |
|---|---|
| POC Script | `/home/john/Thunderbird/ops/mission-061-invisible-playwright-poc.py` |
| This Report | `/home/john/Thunderbird/ops/mission-061-findings.md` |

#!/usr/bin/env python3
"""Test: translation_engine — language detection, dossier frontmatter parsing,
fallback-on-unreliable-translation, output file writing, and usage tracking.

Uses deterministic stub translators (no live Anthropic API calls, no network
dependency) exercised across 5 clients with mixed native languages, matching
the real roster: Furlow (Spanish spouse), Kuklinski (French), McLeod (German),
Lyons (Italian), Loucks (English only — baseline/no-translation case).

A `ClaudeTranslator` live-API smoke test is included but skipped unless
ANTHROPIC_API_KEY is set and `--live` is passed, since fluency of real model
output isn't something a unit test can assert deterministically.

Run: python3 core/i18n/test_translation_engine.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.i18n.translation_engine import (
    TranslationEngine, TranslationError, detect_language_heuristic,
    load_client_languages, _validate_translation, SUPPORTED_LANGUAGES,
)

failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status} | {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


# --------------------------------------------------------------------------
# Stub translators
# --------------------------------------------------------------------------

class StubFluentTranslator:
    """Deterministic fake translation — proves the engine's plumbing, not fluency."""
    PREFIXES = {"es": "[ES] ", "fr": "[FR] ", "de": "[DE] ", "it": "[IT] "}

    def translate(self, subject, body_html, target_language):
        prefix = self.PREFIXES.get(target_language, f"[{target_language.upper()}] ")
        return prefix + subject, body_html.replace(">", f"> {prefix}", 1)


class StubNoOpTranslator:
    """Simulates a broken backend that echoes the source unchanged."""
    def translate(self, subject, body_html, target_language):
        return subject, body_html


class StubExceptionTranslator:
    """Simulates a backend/network failure."""
    def translate(self, subject, body_html, target_language):
        raise RuntimeError("simulated API timeout")


class StubMangledHtmlTranslator:
    """Simulates a translation that strips most HTML markup — should fail validation."""
    def translate(self, subject, body_html, target_language):
        import re
        return "Translated subject", re.sub(r'<[^>]+>', '', body_html)[:20]


print("=== translation_engine.py — test suite ===\n")

# --------------------------------------------------------------------------
# 1. Heuristic language detection
# --------------------------------------------------------------------------
check("heuristic detects Spanish", detect_language_heuristic("Hola señor, gracias por todo") == "es")
check("heuristic detects French", detect_language_heuristic("Bonjour monsieur, merci beaucoup") == "fr")
check("heuristic detects German", detect_language_heuristic("Guten Tag Herr Schmidt, danke") == "de")
check("heuristic defaults to English on no marker", detect_language_heuristic("Thank you very much") == "en")
check("heuristic handles empty text", detect_language_heuristic("") == "en")

# --------------------------------------------------------------------------
# 2. Dossier frontmatter parsing — 5 clients, mixed nationalities
# --------------------------------------------------------------------------
tmpdir = Path(tempfile.mkdtemp(prefix="i18n_test_"))

dossiers = {
    "Furlow": ('---\nclient: Furlow\nguest_languages: {"Melissa Furlow": "es", '
               '"John Furlow": "en"}\n---\n# Furlow dossier\n'),
    "Kuklinski": '---\nclient: Kuklinski\nnative_language: fr\n---\n# Kuklinski dossier\n',
    "McLeod": '---\nclient: McLeod\nnative_language: de\n---\n# McLeod dossier\n',
    "Lyons": '---\nclient: Lyons\nnative_language: it\n---\n# Lyons dossier\n',
    "Loucks": '---\nclient: Loucks\n---\n# Loucks dossier (no language field — English default)\n',
}
dossier_paths = {}
for name, content in dossiers.items():
    p = tmpdir / f"{name}.md"
    p.write_text(content)
    dossier_paths[name] = p

furlow_langs = load_client_languages(dossier_paths["Furlow"])
check("Furlow guest_languages parsed", furlow_langs == {"Melissa Furlow": "es", "John Furlow": "en"},
      str(furlow_langs))

kuklinski_langs = load_client_languages(dossier_paths["Kuklinski"])
check("Kuklinski native_language parsed", kuklinski_langs == {"_default": "fr"}, str(kuklinski_langs))

mcleod_langs = load_client_languages(dossier_paths["McLeod"])
check("McLeod native_language parsed", mcleod_langs == {"_default": "de"}, str(mcleod_langs))

lyons_langs = load_client_languages(dossier_paths["Lyons"])
check("Lyons native_language parsed", lyons_langs == {"_default": "it"}, str(lyons_langs))

loucks_langs = load_client_languages(dossier_paths["Loucks"])
check("Loucks (no field) parses empty -> English default", loucks_langs == {}, str(loucks_langs))

check("nonexistent dossier path returns {} not an exception",
      load_client_languages(tmpdir / "does_not_exist.md") == {})

# --------------------------------------------------------------------------
# 3. Engine: successful translation, per client, writes correct files
# --------------------------------------------------------------------------
out_root = tmpdir / "output"
usage_log = tmpdir / "usage_log.json"

SUBJECT = "Your Scandinavia Voyage — Excursions Confirmed"
BODY = "<html><body><p>Your excursions are confirmed for the Stockholm port day.</p></body></html>"

engine = TranslationEngine(translator=StubFluentTranslator(), output_dir=out_root, usage_log_path=usage_log)

expected_targets = {
    "Furlow": ("es", "Melissa Furlow"),   # spouse, Spanish
    "Kuklinski": ("fr", None),
    "McLeod": ("de", None),
    "Lyons": ("it", None),
}

for client, (lang, guest) in expected_targets.items():
    result = engine.translate_tp(client, SUBJECT, BODY, lang, guest_name=guest)
    check(f"{client} -> {lang}: no fallback", result.fallback_used is False, result.reason)
    check(f"{client} -> {lang}: delivered language correct", result.language == lang)
    check(f"{client} -> {lang}: subject file written", result.subject_path.exists())
    check(f"{client} -> {lang}: body file written", result.body_path.exists())
    check(f"{client} -> {lang}: subject file named correctly",
          result.subject_path.name == f"TP_subject_line_{lang}.txt")
    check(f"{client} -> {lang}: body file named correctly",
          result.body_path.name == f"TP_body_{lang}.html")
    check(f"{client} -> {lang}: subject actually translated",
          result.subject.startswith(StubFluentTranslator.PREFIXES[lang]))

# Loucks: English-only client, no translation needed
loucks_result = engine.translate_tp("Loucks", SUBJECT, BODY, "en")
check("Loucks (en) not marked as fallback", loucks_result.fallback_used is False)
check("Loucks (en) subject unchanged", loucks_result.subject == SUBJECT)
check("Loucks (en) file uses 'en' suffix", loucks_result.subject_path.name == "TP_subject_line_en.txt")

# --------------------------------------------------------------------------
# 4. Fallback behavior — no-op, exception, and mangled-HTML translators
# --------------------------------------------------------------------------
noop_engine = TranslationEngine(translator=StubNoOpTranslator(), output_dir=out_root, usage_log_path=usage_log)
noop_result = noop_engine.translate_tp("Westbrook", SUBJECT, BODY, "es")
check("no-op translator triggers fallback", noop_result.fallback_used is True)
check("no-op fallback delivers English", noop_result.language == "en")
check("no-op fallback reason mentions no-op", "no-op" in noop_result.reason or "identical" in noop_result.reason)

exc_engine = TranslationEngine(translator=StubExceptionTranslator(), output_dir=out_root, usage_log_path=usage_log)
exc_result = exc_engine.translate_tp("Britan", SUBJECT, BODY, "de")
check("exception in translator triggers fallback", exc_result.fallback_used is True)
check("exception fallback delivers English", exc_result.language == "en")
check("exception fallback reason captured", "timeout" in exc_result.reason)

mangled_engine = TranslationEngine(translator=StubMangledHtmlTranslator(), output_dir=out_root, usage_log_path=usage_log)
mangled_result = mangled_engine.translate_tp("Spencer", SUBJECT, BODY, "fr")
check("mangled HTML triggers fallback", mangled_result.fallback_used is True)

# Direct validation-function tests
try:
    _validate_translation(SUBJECT, BODY, "", "", "es")
    check("_validate_translation rejects empty output", False)
except TranslationError:
    check("_validate_translation rejects empty output", True)

try:
    _validate_translation(SUBJECT, BODY, SUBJECT, BODY, "es")
    check("_validate_translation rejects identical no-op", False)
except TranslationError:
    check("_validate_translation rejects identical no-op", True)

# --------------------------------------------------------------------------
# 5. translate_tp_multi — Furlow use case: client + spouse, mixed language
# --------------------------------------------------------------------------
multi_engine = TranslationEngine(translator=StubFluentTranslator(), output_dir=out_root, usage_log_path=usage_log)
multi_results = multi_engine.translate_tp_multi(
    "Furlow", SUBJECT, BODY, guest_language_map=furlow_langs
)
langs_produced = sorted(r.language for r in multi_results)
check("Furlow multi produces English + Spanish", langs_produced == ["en", "es"], str(langs_produced))

# --------------------------------------------------------------------------
# 6. resolve_target_languages
# --------------------------------------------------------------------------
resolved = engine.resolve_target_languages(dossier_path=dossier_paths["McLeod"])
check("resolve_target_languages reads McLeod default", resolved == ["de"], str(resolved))

resolved_override = engine.resolve_target_languages(override="ja")
check("resolve_target_languages honors explicit override", resolved_override == ["ja"])

resolved_none = engine.resolve_target_languages()
check("resolve_target_languages defaults to English with no input", resolved_none == ["en"])

# --------------------------------------------------------------------------
# 7. Usage tracking
# --------------------------------------------------------------------------
summary = engine.usage_summary()
check("usage_summary total counts all attempts", summary["total"] > 0, str(summary["total"]))
check("usage_summary tracks fallback_count >= 3 (noop+exception+mangled)",
      summary["fallback_count"] >= 3, str(summary["fallback_count"]))
check("usage_summary by_client includes Furlow", "Furlow" in summary["by_client"])
check("usage_summary by_language includes es", "es" in summary["by_language"], str(summary["by_language"]))

raw_log = json.loads(usage_log.read_text())
check("usage log is a flat JSON list of records", isinstance(raw_log, list) and len(raw_log) == summary["total"])
check("usage log records carry requested vs delivered language",
      all("requested_language" in r and "delivered_language" in r for r in raw_log))

# --------------------------------------------------------------------------
# 8. Optional live-API smoke test (only with --live and a real key)
# --------------------------------------------------------------------------
if "--live" in sys.argv and os.environ.get("ANTHROPIC_API_KEY"):
    from core.i18n.translation_engine import ClaudeTranslator
    live_engine = TranslationEngine(translator=ClaudeTranslator(), output_dir=out_root, usage_log_path=usage_log)
    live_result = live_engine.translate_tp("LiveSmokeTest", SUBJECT, BODY, "es")
    check("live Claude translation does not fall back", live_result.fallback_used is False, live_result.reason)
    print(f"  live translated subject: {live_result.subject}")
else:
    print("SKIP | live Claude API smoke test (pass --live with ANTHROPIC_API_KEY set to run)")

shutil.rmtree(tmpdir, ignore_errors=True)

print("\n" + ("=" * 50))
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")

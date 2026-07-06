#!/usr/bin/env python3
"""Multi-language client communications — auto-translate TP (touchpoint) emails
into a guest's native language.

Language source priority, per client:
  1. Explicit caller override (`target_language=` / `guest_language_map=`)
  2. Dossier YAML frontmatter (`native_language:` or `guest_languages:`)
  3. Heuristic detection over supplied text (last resort, conservative — see
     `detect_language_heuristic`)
  4. English default

Translation backend is pluggable (`Translator` protocol). Default is
`ClaudeTranslator`, calling the Anthropic API. Any translation that fails the
reliability check (`_validate_translation`) falls back to English rather than
shipping a broken or no-op "translation" to a client — this mirrors the wing's
Negative-Space rule (CLAUDE.md Rule 1): unverifiable output does not go out.

Output per client/language: `TP_subject_line_{language}.txt` + `TP_body_{language}.html`,
written under `output/i18n/{client_slug}/`. Every attempt (success or fallback) is
appended to `output/i18n/translation_usage_log.json` for usage tracking.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "i18n"
DEFAULT_USAGE_LOG = DEFAULT_OUTPUT_DIR / "translation_usage_log.json"

# ISO 639-1 code -> display name, for supported target languages.
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "ru": "Russian",
    "ar": "Arabic",
}


class TranslationError(Exception):
    """A translation attempt could not be trusted — caller falls back to English."""


# --------------------------------------------------------------------------
# Language detection
# --------------------------------------------------------------------------

# Cheap word-boundary heuristic used only when no dossier field and no explicit
# language is given. Deliberately conservative: unmatched text stays English —
# a wrong guess in a client email is worse than no guess.
_HEURISTIC_MARKERS = {
    "es": {" el ", " la ", " de ", " gracias", " hola", " señor", " señora", "¿", "¡"},
    "fr": {" le ", " la ", " de ", " merci", " bonjour", " monsieur", " madame"},
    "de": {" der ", " die ", " das ", " danke", " guten tag", " herr ", " frau "},
    "it": {" il ", " la ", " grazie", " buongiorno", " signore", " signora"},
    "pt": {" o ", " a ", " obrigado", " obrigada", " bom dia", " senhor"},
}


def detect_language_heuristic(text: str) -> str:
    """Best-effort language guess from raw text. Returns 'en' when no marker matches."""
    if not text:
        return "en"
    padded = f" {text.lower()} "
    scores = {
        lang: sum(1 for marker in markers if marker in padded)
        for lang, markers in _HEURISTIC_MARKERS.items()
    }
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_lang if best_score > 0 else "en"


_FRONTMATTER_FIELD_RE = re.compile(
    r'^\s*(native_language|preferred_language|guest_languages)\s*:\s*(.+)$',
    re.IGNORECASE | re.MULTILINE,
)


def _frontmatter_block(dossier_text: str) -> str:
    if not dossier_text.startswith("---"):
        return ""
    end = dossier_text.find("\n---", 3)
    return dossier_text[:end] if end != -1 else dossier_text[:2000]


def load_client_languages(dossier_path: Path) -> dict:
    """Read per-guest native language from a dossier's YAML frontmatter.

    Supports two optional frontmatter fields:
      native_language: es
      guest_languages: {"Melissa Furlow": "es", "John Furlow": "en"}

    Returns {"_default": code} and/or {guest_name: code}. A missing or
    unparsable field yields {} — caller defaults to English rather than
    guessing (Negative-Space rule).
    """
    dossier_path = Path(dossier_path)
    if not dossier_path.exists():
        return {}
    text = dossier_path.read_text(encoding="utf-8", errors="ignore")
    block = _frontmatter_block(text)
    result: dict[str, str] = {}
    for match in _FRONTMATTER_FIELD_RE.finditer(block):
        field_name, raw_value = match.group(1).lower(), match.group(2).strip()
        if field_name in ("native_language", "preferred_language"):
            code = raw_value.strip('"\' ').lower()
            if code in SUPPORTED_LANGUAGES:
                result["_default"] = code
        elif field_name == "guest_languages":
            try:
                parsed = json.loads(raw_value)
                for guest, code in parsed.items():
                    code = str(code).strip().lower()
                    if code in SUPPORTED_LANGUAGES:
                        result[guest] = code
            except (json.JSONDecodeError, AttributeError):
                pass
    return result


# --------------------------------------------------------------------------
# Translator backends
# --------------------------------------------------------------------------

class Translator(Protocol):
    def translate(self, subject: str, body_html: str, target_language: str) -> tuple[str, str]:
        """Return (translated_subject, translated_body_html)."""


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


class ClaudeTranslator:
    """Translates via the Anthropic API. Haiku by default — translation is a
    mechanical task, not a reasoning one (SO-TOKEN-DISCIPLINE model routing)."""

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, model: str = DEFAULT_MODEL, client=None):
        self.model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def translate(self, subject: str, body_html: str, target_language: str) -> tuple[str, str]:
        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
        prompt = (
            f"Translate the following client email into fluent, natural {lang_name}. "
            "Preserve all HTML tags, hyperlinks, dollar amounts, dates, and proper "
            "nouns (ship names, hotel names, place names) exactly. Keep the warm, "
            "professional luxury-travel-concierge tone. "
            'Return ONLY valid JSON of the shape {"subject": "...", "body_html": "..."} '
            "with no other text.\n\n"
            f"SUBJECT: {subject}\n\nBODY (HTML):\n{body_html}"
        )
        resp = self._get_client().messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in resp.content if hasattr(block, "text"))
        data = _parse_json_response(raw)
        return data["subject"], data["body_html"]


# --------------------------------------------------------------------------
# Reliability check — a bad translation falls back to English, it never ships
# --------------------------------------------------------------------------

def _validate_translation(orig_subject: str, orig_body: str, t_subject: str,
                           t_body: str, target_language: str) -> None:
    if not t_subject or not t_subject.strip():
        raise TranslationError("empty translated subject")
    if not t_body or not t_body.strip():
        raise TranslationError("empty translated body")
    if t_subject.strip() == orig_subject.strip() and t_body.strip() == orig_body.strip():
        raise TranslationError(
            f"translation identical to source for target '{target_language}' — likely no-op"
        )
    orig_tags, t_tags = orig_body.count("<"), t_body.count("<")
    if orig_tags > 0:
        drift = abs(orig_tags - t_tags) / orig_tags
        if drift > 0.35:
            raise TranslationError(
                f"HTML tag count drifted {drift:.0%} (orig={orig_tags}, translated={t_tags}) "
                "— translation may have mangled markup"
            )
    ratio = len(t_body) / max(len(orig_body), 1)
    if ratio < 0.4 or ratio > 2.5:
        raise TranslationError(f"translated body length ratio {ratio:.2f} outside plausible range")


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_') or "client"


@dataclass
class TranslationResult:
    client: str
    language: str
    subject: str
    body_html: str
    subject_path: Optional[Path]
    body_path: Optional[Path]
    fallback_used: bool
    requested_language: str
    reason: str = ""


class TranslationEngine:
    def __init__(self, translator: Optional[Translator] = None,
                 output_dir: Path = DEFAULT_OUTPUT_DIR,
                 usage_log_path: Path = DEFAULT_USAGE_LOG):
        self.translator = translator or ClaudeTranslator()
        self.output_dir = Path(output_dir)
        self.usage_log_path = Path(usage_log_path)

    def resolve_target_languages(self, dossier_path: Optional[Path] = None,
                                  guest_name: Optional[str] = None,
                                  override: Optional[str] = None) -> list[str]:
        """Which language(s) a TP should be produced in for this client/guest."""
        if override:
            return [override]
        if dossier_path:
            langs = load_client_languages(Path(dossier_path))
            if guest_name and guest_name in langs:
                return [langs[guest_name]]
            if guest_name is None:
                distinct = {v for k, v in langs.items() if k != "_default"}
                if langs.get("_default"):
                    distinct.add(langs["_default"])
                return sorted(distinct) if distinct else ["en"]
            if "_default" in langs:
                return [langs["_default"]]
        return ["en"]

    def translate_tp(self, client_name: str, subject: str, body_html: str,
                      target_language: str, guest_name: Optional[str] = None) -> TranslationResult:
        """Translate one TP email into `target_language`. Writes both output files
        and logs the attempt regardless of outcome. Falls back to English on any
        reliability failure — see `_validate_translation`."""
        client_dir = self.output_dir / _slugify(client_name)
        client_dir.mkdir(parents=True, exist_ok=True)

        delivered_language = target_language
        fallback_used = False
        reason = ""
        out_subject, out_body = subject, body_html

        if target_language != "en":
            try:
                t_subject, t_body = self.translator.translate(subject, body_html, target_language)
                _validate_translation(subject, body_html, t_subject, t_body, target_language)
                out_subject, out_body = t_subject, t_body
            except Exception as exc:  # noqa: BLE001 — any backend/validation failure -> fallback
                delivered_language = "en"
                fallback_used = True
                reason = str(exc)

        subject_path = client_dir / f"TP_subject_line_{delivered_language}.txt"
        body_path = client_dir / f"TP_body_{delivered_language}.html"
        subject_path.write_text(out_subject, encoding="utf-8")
        body_path.write_text(out_body, encoding="utf-8")

        self._log_usage({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "client": client_name,
            "guest": guest_name,
            "requested_language": target_language,
            "delivered_language": delivered_language,
            "fallback_used": fallback_used,
            "reason": reason,
            "subject_path": str(subject_path),
            "body_path": str(body_path),
        })

        return TranslationResult(
            client=client_name, language=delivered_language, subject=out_subject,
            body_html=out_body, subject_path=subject_path, body_path=body_path,
            fallback_used=fallback_used, requested_language=target_language, reason=reason,
        )

    def translate_tp_multi(self, client_name: str, subject: str, body_html: str,
                            dossier_path: Optional[Path] = None,
                            guest_language_map: Optional[dict] = None,
                            always_include_english: bool = True) -> list[TranslationResult]:
        """Produce one output per distinct guest language on the booking, e.g. an
        English-speaking client with a Spanish-speaking spouse gets both an
        English and a Spanish TP."""
        if guest_language_map is None and dossier_path:
            guest_language_map = load_client_languages(Path(dossier_path))
        guest_language_map = guest_language_map or {}

        languages = {v for k, v in guest_language_map.items() if k != "_default"}
        if guest_language_map.get("_default"):
            languages.add(guest_language_map["_default"])
        if always_include_english:
            languages.add("en")
        if not languages:
            languages = {"en"}

        return [
            self.translate_tp(client_name, subject, body_html, lang)
            for lang in sorted(languages)
        ]

    def _log_usage(self, record: dict) -> None:
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if self.usage_log_path.exists():
            try:
                entries = json.loads(self.usage_log_path.read_text())
            except json.JSONDecodeError:
                entries = []
        entries.append(record)
        self.usage_log_path.write_text(json.dumps(entries, indent=2))

    def usage_summary(self) -> dict:
        """Which clients/languages have been translated, and how often fallback fired."""
        if not self.usage_log_path.exists():
            return {"total": 0, "by_client": {}, "by_language": {}, "fallback_count": 0}
        entries = json.loads(self.usage_log_path.read_text())
        by_client: dict[str, int] = {}
        by_language: dict[str, int] = {}
        fallback_count = 0
        for e in entries:
            by_client[e["client"]] = by_client.get(e["client"], 0) + 1
            by_language[e["delivered_language"]] = by_language.get(e["delivered_language"], 0) + 1
            if e.get("fallback_used"):
                fallback_count += 1
        return {"total": len(entries), "by_client": by_client, "by_language": by_language,
                "fallback_count": fallback_count}

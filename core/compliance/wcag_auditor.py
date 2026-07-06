"""
WCAG 2.1 AA accessibility auditor for D2M client-facing HTML
(itineraries, proposals, lifecycle emails).

Scans for:
  - contrast-ratio  : text/background contrast below AA threshold (4.5:1 normal, 3:1 large)
  - missing-alt      : <img> with no alt attribute (or alt="")
  - missing-label    : form control with no accessible name (label/aria-label/aria-labelledby)
  - color-only       : a bare colored glyph/dot used as the only status signal
  - keyboard-trap    : onclick handler on a non-interactive element with no
                       tabindex/role/onkeydown, so it is unreachable by keyboard

Usage:
    python3 core/compliance/wcag_auditor.py audit <file_or_dir> [--out DIR]
    python3 core/compliance/wcag_auditor.py fix <file> [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

AA_NORMAL_RATIO = 4.5
AA_LARGE_RATIO = 3.0
LARGE_BOLD_PX = 18.66  # ~14pt
LARGE_REGULAR_PX = 24.0  # ~18pt

FORM_CONTROL_TAGS = {"input", "select", "textarea"}
NON_INTERACTIVE_TAGS = {"div", "span", "li", "td", "tr", "p", "img"}
COLOR_ONLY_CANDIDATE_TAGS = {"span", "div", "i", "b", "strong", "em"}
# HTML void elements: never have a closing tag, so they must never be pushed
# onto the parser's element stack even when authored without a self-closing
# "/>" (html.parser does not know HTML void-element semantics — a bare
# "<img ...>" with no slash would otherwise sit open for the rest of the
# document and corrupt every subsequent element's inherited style context).
VOID_ELEMENTS = {"img", "br", "hr", "input", "meta", "link", "area", "base",
                  "col", "embed", "source", "track", "wbr"}
_GLYPH_ONLY_RE = re.compile(r"^[\s\W_]{0,3}$")
# Purely decorative uses of color that convey no information (WCAG 1.4.1
# only cares about color used to signal meaning) — excluded from color-only
# even though they otherwise match the "empty/glyph leaf with explicit
# color" shape: a divider line, or a typographic separator between fields.
_DECORATIVE_CLASS_HINT_RE = re.compile(r"divider|separator|\bsep\b|spacer|\brule\b|hr-?line", re.IGNORECASE)
_SEPARATOR_GLYPHS = {"·", "•", "|", "-", "–", "—", "/", "\\", "∙", "●", "○"}

_COLOR_NAMES = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000", "green": "#008000",
    "blue": "#0000ff", "gray": "#808080", "grey": "#808080", "yellow": "#ffff00",
    "orange": "#ffa500",
}


# --------------------------------------------------------------------------
# Color math (WCAG relative luminance / contrast ratio)
# --------------------------------------------------------------------------

def _normalize_hex(value: str) -> Optional[str]:
    v = value.strip().lower()
    if v in _COLOR_NAMES:
        return _COLOR_NAMES[v]
    if not v.startswith("#"):
        return None
    h = v[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9a-f]{6}", h):
        return None
    return "#" + h


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _linearize(c: int) -> float:
    c_ = c / 255.0
    return c_ / 12.92 if c_ <= 0.03928 else ((c_ + 0.055) / 1.055) ** 2.4


def relative_luminance(hexcolor: str) -> float:
    r, g, b = _rgb(hexcolor)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1, l2 = relative_luminance(fg_hex), relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_large_text(font_size_px: Optional[float], bold: bool) -> bool:
    if font_size_px is None:
        return False
    if bold and font_size_px >= LARGE_BOLD_PX:
        return True
    return font_size_px >= LARGE_REGULAR_PX


def required_ratio(font_size_px: Optional[float], bold: bool) -> float:
    return AA_LARGE_RATIO if is_large_text(font_size_px, bold) else AA_NORMAL_RATIO


def _step_toward(hexcolor: str, other_hex: str, direction: int, role: str,
                  target_ratio: float, max_steps: int = 42) -> Optional[tuple]:
    """Step `hexcolor` (the `role` side, 'fg' or 'bg') toward black
    (direction=-1) or white (direction=+1) in fixed increments until the
    contrast against `other_hex` clears target_ratio. Returns
    (new_hex, steps, achieved_ratio) or None if it can't get there
    (already at the 0/255 boundary)."""
    r, g, b = _rgb(hexcolor)
    for i in range(1, max_steps + 1):
        delta = direction * i * 6
        nr, ng, nb = (max(0, min(255, c + delta)) for c in (r, g, b))
        candidate = "#%02x%02x%02x" % (nr, ng, nb)
        ratio = contrast_ratio(candidate, other_hex) if role == "fg" else contrast_ratio(other_hex, candidate)
        if ratio >= target_ratio:
            return candidate, i, ratio
        if (nr, ng, nb) in ((0, 0, 0), (255, 255, 255)):
            break  # hit the rail, no point taking more steps
    return None


def suggest_contrast_fix(fg_hex: str, bg_hex: str, target_ratio: float) -> Optional[dict]:
    """Find the smallest color change — to EITHER the foreground or the
    background — that clears target_ratio. Tries whichever side is not
    already at its luminance extreme; picks the solution needing fewer
    steps when both sides are adjustable."""
    fg, bg = _normalize_hex(fg_hex), _normalize_hex(bg_hex)
    if not fg or not bg:
        return None
    fg_lum, bg_lum = relative_luminance(fg), relative_luminance(bg)

    if fg_lum >= bg_lum:
        # text is the lighter element: lighten text further, or darken bg further
        fg_try = _step_toward(fg, bg, +1, "fg", target_ratio)
        bg_try = _step_toward(bg, fg, -1, "bg", target_ratio)
    else:
        # text is the darker element: darken text further, or lighten bg further
        fg_try = _step_toward(fg, bg, -1, "fg", target_ratio)
        bg_try = _step_toward(bg, fg, +1, "bg", target_ratio)

    candidates = []
    if fg_try:
        candidates.append(("color", fg, fg_try[0], bg, fg_try[1], fg_try[2]))
    if bg_try:
        candidates.append(("background", bg, bg_try[0], fg, bg_try[1], bg_try[2]))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[4])
    target, original, suggested, counterpart, steps, achieved = candidates[0]
    return {
        "target": target,  # "color" or "background" — which property to change
        "original": original,
        "suggested": suggested,
        "counterpart": counterpart,
        "steps": steps,
        "achieved_ratio": round(achieved, 2),
    }


# --------------------------------------------------------------------------
# Violation model
# --------------------------------------------------------------------------

@dataclass
class Violation:
    rule: str
    wcag_criterion: str
    severity: str  # "error" | "warning"
    line: int
    element: str
    detail: str
    fix: Optional[dict] = None


@dataclass
class FileAudit:
    file: str
    violations: list = field(default_factory=list)
    element_count: int = 0
    passed: bool = True

    def to_dict(self):
        return asdict(self)


# --------------------------------------------------------------------------
# Minimal style resolution: inline style + <style> block class/tag rules,
# with per-property provenance so fixes can be written back to the right
# place (a shared CSS rule vs. one element's inline style). Good enough for
# D2M's hand-authored client HTML (no external stylesheets, no cascade
# specificity wars) rather than a full CSS engine.
# --------------------------------------------------------------------------

def _parse_declarations(style: str) -> dict:
    out = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        k, _, v = part.partition(":")
        out[k.strip().lower()] = v.strip()
    return out


def _font_size_px(decl: dict) -> Optional[float]:
    v = decl.get("font-size")
    if not v:
        return None
    m = re.match(r"([\d.]+)\s*(px|pt|em)?", v)
    if not m:
        return None
    num, unit = float(m.group(1)), (m.group(2) or "px")
    if unit == "pt":
        return num * (96 / 72)
    if unit == "em":
        return num * 16
    return num


def _is_bold(decl: dict) -> bool:
    fw = decl.get("font-weight", "").lower()
    return fw in ("bold", "bolder") or (fw.isdigit() and int(fw) >= 600)


def _simple_part(part: str) -> Optional[tuple]:
    """('class', name) or ('tag', name) for a single, non-combinator
    selector fragment; None if it's anything more complex."""
    part = part.strip()
    if not part or any(ch in part for ch in ">+~:["):
        return None
    if part.startswith("."):
        return ("class", part[1:])
    if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", part):
        return ("tag", part.lower())
    return None


class StyleSheet:
    """Extract simple `.class { decl }`, `tag { decl }`, and one-level
    descendant rules (`.parent tag { decl }` / `.parent .child { decl }`)
    from <style> blocks. This covers D2M's hand-authored client templates
    (badge-in-a-box patterns like `.financial-box h3`) without needing a
    real CSS engine — deeper combinators/pseudo-classes are out of scope."""

    _RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")

    def __init__(self):
        self.by_class: dict[str, dict] = {}
        self.by_tag: dict[str, dict] = {}
        # (ancestor_kind, ancestor_name, target_kind, target_name) -> decl
        self.descendant_rules: list[tuple] = []

    def ingest(self, css_text: str):
        for m in self._RULE_RE.finditer(css_text):
            selector, body = m.group(1).strip(), m.group(2).strip()
            decl = _parse_declarations(body)
            if not decl:
                continue
            for sel in selector.split(","):
                sel = sel.strip()
                if not sel:
                    continue
                parts = sel.split()
                if len(parts) == 1:
                    simple = _simple_part(parts[0])
                    if not simple:
                        continue
                    kind, name = simple
                    (self.by_class if kind == "class" else self.by_tag).setdefault(name, {}).update(decl)
                elif len(parts) == 2:
                    ancestor, target = _simple_part(parts[0]), _simple_part(parts[1])
                    if not ancestor or not target:
                        continue
                    self.descendant_rules.append((ancestor, target, decl, sel))
                # 3+ part selectors and any combinator/pseudo-class: out of scope

    def resolve_with_origin(self, tag: str, classes: list[str],
                             ancestors: Optional[list[tuple[str, list[str]]]] = None) -> tuple[dict, dict]:
        """Returns (merged_declarations, origin_map) where origin_map[prop]
        = ("tag"|"class"|"descendant", selector_name). Cascade order (low
        to high specificity): tag rule -> class rule(s) -> descendant rule(s)
        matching an ancestor in `ancestors` (root-to-parent, in order)."""
        merged: dict = {}
        origin: dict = {}
        if tag in self.by_tag:
            for k, v in self.by_tag[tag].items():
                merged[k] = v
                origin[k] = ("tag", tag)
        for c in classes:
            if c in self.by_class:
                for k, v in self.by_class[c].items():
                    merged[k] = v
                    origin[k] = ("class", c)
        if ancestors:
            for (a_kind, a_name), (t_kind, t_name), decl, sel in self.descendant_rules:
                target_matches = (t_kind == "tag" and t_name == tag) or (t_kind == "class" and t_name in classes)
                if not target_matches:
                    continue
                ancestor_matches = any(
                    (a_kind == "tag" and a_name == anc_tag) or (a_kind == "class" and a_name in anc_classes)
                    for anc_tag, anc_classes in ancestors
                )
                if ancestor_matches:
                    for k, v in decl.items():
                        merged[k] = v
                        origin[k] = ("descendant", sel)
        return merged, origin


@dataclass
class _StyleCtx:
    color: Optional[str] = None
    background: Optional[str] = None
    font_size_px: Optional[float] = None
    bold: bool = False
    color_origin: Optional[tuple] = None       # ("tag"|"class"|"inline", selector_or_None, raw_value)
    background_origin: Optional[tuple] = None


def _resolve_ctx(merged: dict, origin: dict, attrs: dict, parent_ctx: _StyleCtx, line: int) -> _StyleCtx:
    def _prop_and_origin(prop_names: list[str], parent_val, parent_origin):
        for p in prop_names:
            if p in merged:
                raw = merged[p]
                normalized = _normalize_hex(raw)
                if normalized:
                    kind, sel = origin[p]
                    return normalized, (kind, sel, raw, p, line)
        bg_attr = attrs.get("bgcolor")
        if bg_attr and "background-color" in prop_names:
            normalized = _normalize_hex(bg_attr)
            if normalized:
                return normalized, ("inline_attr", None, bg_attr, "bgcolor", line)
        return parent_val, parent_origin

    color, color_origin = _prop_and_origin(["color"], parent_ctx.color, parent_ctx.color_origin)
    bg, bg_origin = _prop_and_origin(["background-color", "background"], parent_ctx.background, parent_ctx.background_origin)

    font_px = _font_size_px(merged) or parent_ctx.font_size_px
    bold = _is_bold(merged) or (parent_ctx.bold and "font-weight" not in merged)

    return _StyleCtx(color=color, background=bg, font_size_px=font_px, bold=bold,
                      color_origin=color_origin, background_origin=bg_origin)


class WCAGAuditParser(HTMLParser):
    """Single-pass walk building violations as it goes, carrying a cascade
    stack of resolved color/background/font styles down through nested tags
    (inline style wins over stylesheet class/tag rules, which win over the
    inherited parent context)."""

    def __init__(self, stylesheet: StyleSheet):
        super().__init__(convert_charrefs=True)
        self.stylesheet = stylesheet
        self.violations: list[Violation] = []
        self.element_count = 0
        root_ctx = _StyleCtx(color="#000000", background="#ffffff")
        root_frame = {"tag": "root", "ctx": root_ctx, "explicit_color": False,
                      "explicit_bg": False, "attrs": {}, "line": 0, "text": [], "has_children": False}
        self._stack: list[dict] = [root_frame]
        self._label_for_ids: set[str] = set()
        self._form_controls: list[dict] = []
        self._seen_contrast_keys: set = set()
        self._in_raw_text_el = 0  # depth inside <style>/<script>, whose data isn't visible text

    def _attrs_dict(self, attrs):
        return {k.lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        self._handle_open(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._handle_open(tag, attrs, self_closing=True)

    def _handle_open(self, tag, attrs_list, self_closing: bool):
        self.element_count += 1
        line = self.getpos()[0]
        if tag in VOID_ELEMENTS:
            self_closing = True
        attrs = self._attrs_dict(attrs_list)
        parent_ctx = self._stack[-1]["ctx"]
        self._stack[-1]["has_children"] = True

        classes = attrs.get("class", "").split()
        ancestors = [(f["tag"], f["attrs"].get("class", "").split()) for f in self._stack[1:]]
        sheet_decl, sheet_origin = self.stylesheet.resolve_with_origin(tag, classes, ancestors)
        inline_decl = _parse_declarations(attrs.get("style", ""))
        merged = {**sheet_decl, **inline_decl}
        origin = dict(sheet_origin)
        for k in inline_decl:
            origin[k] = ("inline", None)
        # Only count as "explicit" when the value actually resolves to a solid
        # color — a decorative `background: linear-gradient(...)` divider sets
        # the property but conveys no color-coded meaning at all.
        explicit_color = bool(_normalize_hex(merged.get("color", "")))
        explicit_bg = bool(
            _normalize_hex(merged.get("background-color", ""))
            or _normalize_hex(merged.get("background", ""))
            or _normalize_hex(attrs.get("bgcolor", ""))
        )

        ctx = _resolve_ctx(merged, origin, attrs, parent_ctx, line)

        if tag == "img":
            self._check_img(attrs, line)
        elif tag in FORM_CONTROL_TAGS:
            self._check_form_control(tag, attrs, line)
        elif tag == "label":
            for_id = attrs.get("for")
            if for_id:
                self._label_for_ids.add(for_id)
        elif tag in NON_INTERACTIVE_TAGS:
            self._check_keyboard_trap(tag, attrs, line)

        if tag in ("style", "script"):
            self._in_raw_text_el += 1

        if not self_closing:
            self._stack.append({
                "tag": tag, "ctx": ctx, "explicit_color": explicit_color,
                "explicit_bg": explicit_bg, "attrs": attrs, "line": line, "text": [],
                "has_children": False,
            })

    def handle_endtag(self, tag):
        idx = None
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i]["tag"] == tag:
                idx = i
                break
        if idx is None:
            return
        if tag in ("style", "script"):
            self._in_raw_text_el = max(0, self._in_raw_text_el - 1)
        frame = self._stack[idx]
        del self._stack[idx:]
        # Evaluated on close, using ONLY this element's own directly-authored
        # text (not bubbled from children) — a container that merely wraps
        # differently-styled children (e.g. a <td bgcolor> holding a <div>
        # with its own overriding color) must not be flagged using its own
        # (irrelevant, un-rendered) default text color.
        self._check_color_only(frame)
        if frame["tag"] not in FORM_CONTROL_TAGS and frame["tag"] not in ("style", "script"):
            self._maybe_flag_text_contrast(
                frame["tag"], frame["attrs"], frame["ctx"],
                frame["explicit_color"], frame["explicit_bg"], frame["line"], frame["text"],
            )

    def handle_data(self, data):
        if self._in_raw_text_el:
            return
        if self._stack:
            self._stack[-1]["text"].append(data)

    # -- individual rule checks ---------------------------------------------
    def _check_img(self, attrs, line):
        alt = attrs.get("alt")
        if alt is None or alt.strip() == "":
            self.violations.append(Violation(
                rule="missing-alt",
                wcag_criterion="1.1.1 Non-text Content (A)",
                severity="error",
                line=line,
                element=f'<img src="{attrs.get("src", "")[:80]}">',
                detail="Image has no alt attribute (or alt is empty) — screen readers cannot announce it.",
                fix={"action": "add_alt_text", "src": attrs.get("src", ""), "method": "vision_model"},
            ))

    def _check_form_control(self, tag, attrs, line):
        el_id = attrs.get("id")
        has_aria = bool(attrs.get("aria-label") or attrs.get("aria-labelledby"))
        input_type = attrs.get("type", "text").lower()
        if tag == "input" and input_type in ("hidden", "submit", "button", "image"):
            return
        has_label = bool(el_id) and el_id in self._label_for_ids
        self._form_controls.append({
            "tag": tag, "id": el_id, "has_aria": has_aria, "has_label": has_label,
            "line": line, "attrs": attrs,
        })

    def _finalize_form_controls(self):
        for fc in self._form_controls:
            if fc["has_aria"] or fc["has_label"]:
                continue
            placeholder = fc["attrs"].get("placeholder")
            self.violations.append(Violation(
                rule="missing-label",
                wcag_criterion="3.3.2 Labels or Instructions (A) / 4.1.2 Name, Role, Value (A)",
                severity="error",
                line=fc["line"],
                element=f'<{fc["tag"]} id="{fc["id"] or ""}">',
                detail="Form control has no <label for>, aria-label, or aria-labelledby"
                       + (f' (placeholder "{placeholder}" is not a substitute for a label).' if placeholder else "."),
                fix={
                    "action": "add_aria_label",
                    "target_id": fc["id"],
                    "suggested_label": placeholder or fc["attrs"].get("name") or "Input field",
                },
            ))

    def _check_keyboard_trap(self, tag, attrs, line):
        if "onclick" not in attrs:
            return
        has_tabindex = "tabindex" in attrs
        has_role = attrs.get("role") in ("button", "link", "checkbox", "menuitem")
        has_key_handler = "onkeydown" in attrs or "onkeyup" in attrs or "onkeypress" in attrs
        if has_tabindex and (has_role or has_key_handler):
            return
        self.violations.append(Violation(
            rule="keyboard-trap",
            wcag_criterion="2.1.1 Keyboard (A)",
            severity="error",
            line=line,
            element=f"<{tag} onclick=...>",
            detail=f"<{tag}> has an onclick handler but no tabindex/role/onkeydown — "
                   "keyboard-only users cannot reach or activate it.",
            fix={"action": "add_keyboard_support", "tag": tag, "attrs_to_add": {"tabindex": "0", "role": "button"}},
        ))

    def _check_color_only(self, frame: dict):
        tag = frame["tag"]
        if tag not in COLOR_ONLY_CANDIDATE_TAGS:
            return
        if frame["has_children"]:
            return  # a real structural container, not a bare glyph leaf
        if not (frame["explicit_color"] or frame["explicit_bg"]):
            return
        attrs = frame["attrs"]
        if attrs.get("aria-label") or attrs.get("title") or attrs.get("alt"):
            return
        class_str = attrs.get("class", "")
        if _DECORATIVE_CLASS_HINT_RE.search(class_str):
            return
        text = "".join(frame["text"])
        stripped = text.strip()
        if stripped in _SEPARATOR_GLYPHS:
            return
        if not _GLYPH_ONLY_RE.match(stripped):
            return
        classattr = f' class="{class_str}"' if class_str else ""
        self.violations.append(Violation(
            rule="color-only",
            wcag_criterion="1.4.1 Use of Color (A)",
            severity="warning",
            line=frame["line"],
            element=f"<{tag}{classattr}>{text.strip()}</{tag}>",
            detail="Element's only content is empty or a bare symbol, and it carries an explicit "
                   "color/background — this looks like a status signaled by color alone. "
                   "Screen-reader and colorblind users get no equivalent signal. "
                   "Add visible text, an icon with alt text, or an aria-label naming the status.",
            fix={
                "action": None,
                "manual_review_required": True,
                "reason": "The correct label text depends on business meaning (e.g. which status "
                          "the color represents) that can't be inferred mechanically.",
            },
        ))

    def _maybe_flag_text_contrast(self, tag, attrs, ctx: _StyleCtx, explicit_color: bool,
                                   explicit_bg: bool, line, text_chunks: list[str]):
        if not (explicit_color or explicit_bg):
            return
        if not ctx.color or not ctx.background:
            return
        if not "".join(text_chunks).strip():
            return  # no text is actually rendered directly by this element
        ratio = contrast_ratio(ctx.color, ctx.background)
        needed = required_ratio(ctx.font_size_px, ctx.bold)
        if ratio >= needed:
            return

        # Dedupe: a shared CSS class (e.g. tag-yellow) triggers this on every
        # element that uses it — report it once, keyed by the offending
        # origin with the per-occurrence line number stripped out.
        def _origin_key(origin):
            return origin[:4] if origin else None

        dedupe_key = (_origin_key(ctx.color_origin), _origin_key(ctx.background_origin))
        if dedupe_key in self._seen_contrast_keys:
            return
        self._seen_contrast_keys.add(dedupe_key)

        fix = suggest_contrast_fix(ctx.color, ctx.background, needed)
        if fix:
            fix = {**fix, "origin": _pick_origin(fix["target"], ctx)}
        classattr = f' class="{attrs.get("class")}"' if attrs.get("class") else ""
        self.violations.append(Violation(
            rule="contrast-ratio",
            wcag_criterion="1.4.3 Contrast (Minimum) (AA)",
            severity="error",
            line=line,
            element=f"<{tag}{classattr}>",
            detail=f"Contrast {ratio:.2f}:1 between {ctx.color} text and {ctx.background} "
                   f"background — needs {needed}:1 for "
                   f"{'large' if is_large_text(ctx.font_size_px, ctx.bold) else 'normal'} text.",
            fix=fix,
        ))

    def finalize(self):
        self._finalize_form_controls()
        return self.violations


def _pick_origin(target: str, ctx: _StyleCtx):
    return ctx.color_origin if target == "color" else ctx.background_origin


def _extract_style_blocks(html_text: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html_text, re.IGNORECASE | re.DOTALL))


def audit_html(html_text: str, filename: str = "<inline>") -> FileAudit:
    sheet = StyleSheet()
    sheet.ingest(_extract_style_blocks(html_text))
    parser = WCAGAuditParser(sheet)
    parser.feed(html_text)
    violations = parser.finalize()
    audit = FileAudit(file=filename, violations=violations, element_count=parser.element_count)
    audit.passed = len(violations) == 0
    return audit


def audit_file(path: Path) -> FileAudit:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return audit_html(text, filename=str(path))


# --------------------------------------------------------------------------
# Fix engine — applies violation["fix"] dicts back onto HTML text.
# Vision-based alt text generation is pluggable; falls back to a filename-
# derived placeholder (flagged NEEDS_REVIEW) when no vision backend is wired.
# --------------------------------------------------------------------------

def generate_alt_text(src: str, vision_fn=None) -> str:
    """vision_fn(src) -> str is an injectable hook (e.g. Claude vision).
    Defaults to a conservative placeholder so automated fixing never
    ships an invented factual claim into client copy unreviewed."""
    if vision_fn is not None:
        try:
            text = vision_fn(src)
            if text and text.strip():
                return text.strip()
        except Exception:
            pass
    name = src.rsplit("/", 1)[-1].split("?")[0]
    if name.startswith("data:") or not name:
        return "NEEDS_REVIEW: decorative or embedded image — describe manually"
    stem = re.sub(r"\.[a-zA-Z0-9]+$", "", name)
    stem = re.sub(r"[_\-]+", " ", stem).strip() or "image"
    return f"NEEDS_REVIEW: {stem}"


def default_vision_fn(src: str) -> str:
    """Real vision backend using the Anthropic SDK, mirroring the pattern in
    core/intel/thunderbird_price_monitor.py. Requires ANTHROPIC_API_KEY.
    Raises on any failure so callers fall back to the placeholder."""
    import base64
    import urllib.request
    import anthropic

    if src.startswith("data:"):
        header, b64data = src.split(",", 1)
        media_type = header.split(";")[0].replace("data:", "") or "image/png"
    elif src.startswith("http"):
        with urllib.request.urlopen(src, timeout=10) as resp:  # noqa: S310
            raw = resp.read()
        b64data = base64.b64encode(raw).decode()
        media_type = "image/png" if src.lower().endswith(".png") else "image/jpeg"
    else:
        raise ValueError("unsupported image source for vision alt-text")

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=60,
        system="Write a concise, factual WCAG alt-text description (under 125 characters) "
               "for this image. No preamble, no quotes, just the description.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64data}},
                {"type": "text", "text": "Alt text:"},
            ],
        }],
    )
    return resp.content[0].text.strip()


def _patch_css_rule(html_text: str, selector_kind: str, selector: str, prop: str,
                     raw_value: str, new_value: str) -> tuple[str, bool]:
    """Rewrite `prop: raw_value` to `prop: new_value` inside the specific
    `.selector { ... }`, `tag { ... }`, or compound descendant
    (`.parent tag { ... }`) rule block in the <style> section."""
    if selector_kind == "class":
        pattern_selector = "." + selector
    else:
        # "tag" -> bare selector; "descendant" -> already the full compound text
        pattern_selector = selector
    rule_re = re.compile(
        r"(" + re.escape(pattern_selector) + r"\s*\{[^{}]*?" + re.escape(prop) + r"\s*:\s*)"
        + re.escape(raw_value) + r"(\s*[;}])",
        re.IGNORECASE,
    )
    new_text, n = rule_re.subn(lambda m: m.group(1) + new_value + m.group(2), html_text, count=1)
    return new_text, bool(n)


def _patch_inline_style(html_text: str, line: int, prop: str, raw_value: str, new_value: str) -> tuple[str, bool]:
    """Best-effort: replace `prop: raw_value` inside the style="" attribute
    of the tag opening on/after the given line number."""
    lines = html_text.split("\n")
    if line < 1 or line > len(lines):
        return html_text, False
    offset = sum(len(l) + 1 for l in lines[: line - 1])
    tail = html_text[offset:]
    pattern = re.compile(re.escape(prop) + r"\s*:\s*" + re.escape(raw_value) + r"\b", re.IGNORECASE)
    new_tail, n = pattern.subn(f"{prop}: {new_value}", tail, count=1)
    if not n:
        return html_text, False
    return html_text[:offset] + new_tail, True


def apply_fixes(html_text: str, audit: FileAudit, vision_fn=None) -> tuple[str, list[dict]]:
    """Apply every violation with an available fix in-place on html_text.
    Returns (fixed_html, applied_log)."""
    applied = []
    fixed = html_text
    patched_origins: set = set()

    for v in audit.violations:
        if not v.fix:
            continue
        action = v.fix.get("action")

        if action == "add_alt_text":
            src = v.fix["src"]
            alt_text = generate_alt_text(src, vision_fn=vision_fn)
            pattern = re.compile(
                r'(<img\b[^>]*?src=["\']' + re.escape(src) + r'["\'][^>]*?)(/?>)',
                re.IGNORECASE | re.DOTALL,
            )

            def _inject_alt(m, _alt=alt_text):
                tag_open = m.group(1)
                if re.search(r"\balt\s*=", tag_open, re.IGNORECASE):
                    return m.group(0)
                return f'{tag_open} alt="{_alt}"{m.group(2)}'

            new_fixed, n = pattern.subn(_inject_alt, fixed, count=1)
            if n:
                fixed = new_fixed
                applied.append({"rule": v.rule, "line": v.line, "alt_text": alt_text})

        elif action == "add_aria_label":
            target_id = v.fix.get("target_id")
            label = v.fix.get("suggested_label", "Input field")
            if target_id:
                pattern = re.compile(
                    r'(<(?:input|select|textarea)\b[^>]*?id=["\']' + re.escape(target_id) + r'["\'][^>]*?)(/?>)',
                    re.IGNORECASE | re.DOTALL,
                )

                def _inject_aria(m, _label=label):
                    tag_open = m.group(1)
                    if re.search(r"\baria-label\s*=", tag_open, re.IGNORECASE):
                        return m.group(0)
                    return f'{tag_open} aria-label="{_label}"{m.group(2)}'

                new_fixed, n = pattern.subn(_inject_aria, fixed, count=1)
                if n:
                    fixed = new_fixed
                    applied.append({"rule": v.rule, "line": v.line, "aria_label": label})

        elif action == "add_keyboard_support":
            attrs_to_add = v.fix.get("attrs_to_add", {})
            tag_name = v.fix.get("tag") or v.element.split()[0].lstrip("<")
            line = v.line
            lines = fixed.split("\n")
            if 1 <= line <= len(lines):
                target_line = lines[line - 1]
                tag_pattern = re.compile(r"<" + re.escape(tag_name) + r"\b([^>]*?onclick=[^>]*?)(/?>)", re.IGNORECASE)

                def _inject_attrs(m, _attrs=attrs_to_add, _tag=tag_name):
                    body = m.group(1)
                    for k, val in _attrs.items():
                        if not re.search(rf"\b{k}\s*=", body, re.IGNORECASE):
                            body += f' {k}="{val}"'
                    return f"<{_tag}{body}{m.group(2)}"

                new_line, n = tag_pattern.subn(_inject_attrs, target_line, count=1)
                if n:
                    lines[line - 1] = new_line
                    fixed = "\n".join(lines)
                    applied.append({"rule": v.rule, "line": v.line, "attrs_added": attrs_to_add})

        elif v.rule == "contrast-ratio" and v.fix and "origin" in v.fix:
            origin = v.fix["origin"]
            if not origin:
                continue
            kind, selector, raw_value, prop, line = origin
            prop_css = "color" if v.fix["target"] == "color" else "background-color" if prop == "background-color" else prop
            dedupe_key = (kind, selector, prop_css, raw_value)
            if dedupe_key in patched_origins:
                continue
            new_value = v.fix["suggested"]
            if kind in ("class", "tag", "descendant"):
                new_fixed, ok = _patch_css_rule(fixed, kind, selector, prop_css, raw_value, new_value)
            elif kind == "inline":
                new_fixed, ok = _patch_inline_style(fixed, line, prop_css, raw_value, new_value)
            elif kind == "inline_attr":
                # bgcolor="..." HTML attribute rather than a style property
                pat = re.compile(r'bgcolor\s*=\s*["\']' + re.escape(raw_value) + r'["\']', re.IGNORECASE)
                new_fixed, n = pat.subn(f'bgcolor="{new_value}"', fixed, count=1)
                ok = bool(n)
            else:
                ok = False
                new_fixed = fixed
            if ok:
                fixed = new_fixed
                patched_origins.add(dedupe_key)
                applied.append({
                    "rule": v.rule, "line": v.line, "target": v.fix["target"],
                    "from": raw_value, "to": new_value, "achieved_ratio": v.fix.get("achieved_ratio"),
                })

    return fixed, applied


# --------------------------------------------------------------------------
# Report generation
# --------------------------------------------------------------------------

def build_report(audits: list[FileAudit]) -> dict:
    total_violations = sum(len(a.violations) for a in audits)
    by_rule: dict[str, int] = {}
    for a in audits:
        for v in a.violations:
            by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
    return {
        "generated": date.today().isoformat(),
        "standard": "WCAG 2.1 AA",
        "files_scanned": len(audits),
        "total_violations": total_violations,
        "violations_by_rule": by_rule,
        "files_with_violations": sum(1 for a in audits if not a.passed),
        "files": [a.to_dict() for a in audits],
    }


def write_report(audits: list[FileAudit], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"audit_report_{date.today().isoformat()}.json"
    out_path.write_text(json.dumps(build_report(audits), indent=2), encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _collect_html_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.html"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="WCAG 2.1 AA auditor for D2M client HTML")
    sub = ap.add_subparsers(dest="cmd", required=True)

    audit_p = sub.add_parser("audit", help="Scan file(s) and write a JSON report")
    audit_p.add_argument("target", type=Path)
    audit_p.add_argument("--out", type=Path, default=Path("."))

    fix_p = sub.add_parser("fix", help="Scan a single file and write an auto-fixed copy")
    fix_p.add_argument("target", type=Path)
    fix_p.add_argument("--out", type=Path, default=None)

    args = ap.parse_args(argv)

    if args.cmd == "audit":
        files = _collect_html_files(args.target)
        audits = [audit_file(f) for f in files]
        report_path = write_report(audits, args.out)
        report = build_report(audits)
        print(f"Scanned {report['files_scanned']} file(s), "
              f"{report['total_violations']} violation(s) across "
              f"{report['files_with_violations']} file(s).")
        print(f"Report: {report_path}")
        return 0 if report["total_violations"] == 0 else 1

    if args.cmd == "fix":
        html_text = args.target.read_text(encoding="utf-8", errors="ignore")
        audit = audit_html(html_text, filename=str(args.target))
        fixed_html, applied = apply_fixes(html_text, audit)
        out_path = args.out or args.target.with_suffix(".fixed.html")
        out_path.write_text(fixed_html, encoding="utf-8")
        print(f"Applied {len(applied)} fix(es) (of {len(audit.violations)} violations). Written to {out_path}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

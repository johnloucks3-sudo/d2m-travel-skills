"""
Tests for core/compliance/wcag_auditor.py

Includes:
  - unit tests for the color-math and rule-detection primitives
  - synthetic fixtures covering each of the 5 rules plus known false-positive
    traps (decorative dividers, void elements without a self-closing slash,
    structural containers with only nested-child text)
  - integration tests against 3 REAL D2M client-facing HTML files already
    shipped in this repo, asserting the exact violations found — these were
    hand-verified against the WCAG contrast formula before being encoded
    here, and two of them are genuine, previously-undetected bugs in the
    shipped itinerary template (see docstrings on each test).
"""
from pathlib import Path

import pytest

from core.compliance.wcag_auditor import (
    apply_fixes,
    audit_file,
    audit_html,
    build_report,
    contrast_ratio,
    generate_alt_text,
    is_large_text,
    relative_luminance,
    required_ratio,
    suggest_contrast_fix,
    write_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# Color math
# --------------------------------------------------------------------------

def test_relative_luminance_black_and_white():
    assert relative_luminance("#000000") == pytest.approx(0.0, abs=1e-9)
    assert relative_luminance("#ffffff") == pytest.approx(1.0, abs=1e-9)


def test_contrast_ratio_black_on_white_is_21():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_known_d2m_pen_on_cream():
    # D2M brand pen color (#0000ff) on cream paper (#f7f3ea) — CLAUDE.md
    # brand spec. Verified independently: 7.76:1, comfortably passes AA.
    assert contrast_ratio("#0000ff", "#f7f3ea") == pytest.approx(7.76, abs=0.05)


def test_contrast_ratio_symmetric():
    assert contrast_ratio("#123456", "#abcdef") == pytest.approx(
        contrast_ratio("#abcdef", "#123456"), abs=1e-9
    )


def test_is_large_text_thresholds():
    assert not is_large_text(16, bold=False)
    assert is_large_text(24, bold=False)
    assert is_large_text(19, bold=True)
    assert not is_large_text(16, bold=True)
    assert not is_large_text(None, bold=True)


def test_required_ratio_large_vs_normal():
    assert required_ratio(24, False) == 3.0
    assert required_ratio(16, False) == 4.5


# --------------------------------------------------------------------------
# suggest_contrast_fix — must handle BOTH directions (light-on-dark and
# dark-on-light), including the case where the lighter color is already
# at the luminance rail (pure white) and only the background can move.
# --------------------------------------------------------------------------

def test_suggest_fix_dark_text_on_light_bg():
    fix = suggest_contrast_fix("#4cff4c", "#f7f3ea", 4.5)
    assert fix is not None
    assert fix["target"] == "color"
    assert contrast_ratio(fix["suggested"], "#f7f3ea") >= 4.5


def test_suggest_fix_white_text_on_medium_bg_adjusts_background():
    # White text can't get any lighter (already at the 255 rail), so the
    # fix MUST come from darkening the background instead.
    fix = suggest_contrast_fix("#ffffff", "#b8860b", 4.5)
    assert fix is not None
    assert fix["target"] == "background"
    assert contrast_ratio("#ffffff", fix["suggested"]) >= 4.5


def test_suggest_fix_returns_none_for_invalid_colors():
    assert suggest_contrast_fix("not-a-color", "#ffffff", 4.5) is None


# --------------------------------------------------------------------------
# Rule: missing-alt
# --------------------------------------------------------------------------

def test_missing_alt_detected():
    html = '<html><body><img src="https://example.com/logo.png"></body></html>'
    audit = audit_html(html)
    assert any(v.rule == "missing-alt" for v in audit.violations)


def test_empty_alt_detected():
    html = '<html><body><img src="x.png" alt=""></body></html>'
    audit = audit_html(html)
    assert any(v.rule == "missing-alt" for v in audit.violations)


def test_present_alt_not_flagged():
    html = '<html><body><img src="x.png" alt="Dreams2Memories Travel logo"></body></html>'
    audit = audit_html(html)
    assert not any(v.rule == "missing-alt" for v in audit.violations)


def test_img_without_self_closing_slash_does_not_corrupt_parser_context():
    """Regression test: a bare `<img ...>` with no trailing '/' must not be
    pushed onto the element stack (html.parser doesn't know HTML void-element
    semantics). If it were, every element for the REST of the document would
    inherit img's context and the whole file would misreport."""
    html = (
        '<html><body>'
        '<img src="logo.png" alt="logo">'
        '<div style="color:#000000;background-color:#ffffff">Fine, high contrast</div>'
        '</body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "contrast-ratio" for v in audit.violations)


# --------------------------------------------------------------------------
# Rule: missing-label
# --------------------------------------------------------------------------

def test_input_without_label_detected():
    html = '<html><body><form><input type="text" id="email"></form></body></html>'
    audit = audit_html(html)
    assert any(v.rule == "missing-label" for v in audit.violations)


def test_input_with_label_for_not_flagged():
    html = (
        '<html><body><form>'
        '<label for="email">Email</label><input type="text" id="email">'
        '</form></body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "missing-label" for v in audit.violations)


def test_input_with_aria_label_not_flagged():
    html = '<html><body><input type="text" id="email" aria-label="Email address"></body></html>'
    audit = audit_html(html)
    assert not any(v.rule == "missing-label" for v in audit.violations)


def test_hidden_and_submit_inputs_not_flagged():
    html = (
        '<html><body>'
        '<input type="hidden" id="csrf" value="abc">'
        '<input type="submit" id="go" value="Send">'
        '</body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "missing-label" for v in audit.violations)


def test_apply_fixes_adds_aria_label_to_orphan_input():
    html = '<html><body><input type="text" id="phone" placeholder="Phone number"></body></html>'
    audit = audit_html(html)
    fixed, applied = apply_fixes(html, audit)
    assert 'aria-label="Phone number"' in fixed
    assert any(a["rule"] == "missing-label" for a in applied)


# --------------------------------------------------------------------------
# Rule: keyboard-trap
# --------------------------------------------------------------------------

def test_div_onclick_without_tabindex_detected():
    html = '<html><body><div onclick="doThing()">Click me</div></body></html>'
    audit = audit_html(html)
    assert any(v.rule == "keyboard-trap" for v in audit.violations)


def test_div_onclick_with_tabindex_and_role_not_flagged():
    html = (
        '<html><body>'
        '<div onclick="doThing()" tabindex="0" role="button">Click me</div>'
        '</body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "keyboard-trap" for v in audit.violations)


def test_apply_fixes_adds_keyboard_support():
    html = '<html><body><div onclick="doThing()">Click me</div></body></html>'
    audit = audit_html(html)
    fixed, applied = apply_fixes(html, audit)
    assert 'tabindex="0"' in fixed and 'role="button"' in fixed
    assert any(a["rule"] == "keyboard-trap" for a in applied)


# --------------------------------------------------------------------------
# Rule: color-only
# --------------------------------------------------------------------------

def test_bare_colored_dot_flagged_as_color_only():
    html = '<html><body><span class="status" style="background-color:#008000"></span> Confirmed</body></html>'
    audit = audit_html(html)
    assert any(v.rule == "color-only" for v in audit.violations)


def test_span_with_real_text_not_flagged_color_only():
    html = '<html><body><span style="color:#008000">Confirmed</span></body></html>'
    audit = audit_html(html)
    assert not any(v.rule == "color-only" for v in audit.violations)


def test_span_with_aria_label_not_flagged_color_only():
    html = '<html><body><span class="status" style="background-color:#008000" aria-label="Confirmed"></span></body></html>'
    audit = audit_html(html)
    assert not any(v.rule == "color-only" for v in audit.violations)


def test_structural_container_wrapping_headers_not_flagged_color_only():
    """A <div class="header"> whose only DIRECT text is whitespace (the
    real text lives in nested <h1>/<h3> children) must not be treated as a
    bare color-only glyph — that was a real false-positive class caught
    during development against Loucks_SilverNova_May2027_Excursions."""
    html = (
        '<html><head><style>.header{background:#07076b;color:#f7f3ea}</style></head>'
        '<body><div class="header"><h1>Title</h1><h3>Subtitle</h3></div></body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "color-only" for v in audit.violations)


def test_decorative_gradient_divider_not_flagged():
    """A 1px decorative divider using `background: linear-gradient(...)`
    conveys no color-coded meaning and must not trip color-only or
    contrast — the property is present but not a solid color."""
    html = (
        '<html><body>'
        '<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,0.5))"></div>'
        '</body></html>'
    )
    audit = audit_html(html)
    assert len(audit.violations) == 0


# --------------------------------------------------------------------------
# Rule: contrast-ratio (synthetic)
# --------------------------------------------------------------------------

def test_low_contrast_class_rule_detected_and_deduped():
    html = (
        '<html><head><style>.tag-yellow{background:#b8860b;color:#fff;font-size:11px;font-weight:bold}</style></head>'
        '<body>'
        '<span class="tag-yellow">A</span>'
        '<span class="tag-yellow">B</span>'
        '<span class="tag-yellow">C</span>'
        '</body></html>'
    )
    audit = audit_html(html)
    contrast_violations = [v for v in audit.violations if v.rule == "contrast-ratio"]
    # Same shared class → one finding, not three.
    assert len(contrast_violations) == 1


def test_large_bold_text_gets_relaxed_threshold():
    # 3.25:1 fails the 4.5 normal-text threshold but clears the 3.0 large-text one.
    html = (
        '<html><body>'
        '<div style="color:#ffffff;background-color:#b8860b;font-size:24px;font-weight:bold">Big</div>'
        '</body></html>'
    )
    audit = audit_html(html)
    assert not any(v.rule == "contrast-ratio" for v in audit.violations)


def test_apply_fixes_patches_shared_css_class_once():
    html = (
        '<html><head><style>.tag-yellow{background:#b8860b;color:#fff;font-size:11px;font-weight:bold}</style></head>'
        '<body><span class="tag-yellow">A</span><span class="tag-yellow">B</span></body></html>'
    )
    audit = audit_html(html)
    fixed, applied = apply_fixes(html, audit)
    assert fixed.count("#b8860b") == 0  # both instances read from the one patched rule
    assert len(applied) == 1
    refixed_audit = audit_html(fixed)
    assert not any(v.rule == "contrast-ratio" for v in refixed_audit.violations)


# --------------------------------------------------------------------------
# generate_alt_text — placeholder behavior without a vision backend
# --------------------------------------------------------------------------

def test_generate_alt_text_placeholder_from_filename():
    text = generate_alt_text("https://example.com/images/silver_nova_ship.jpg")
    assert "NEEDS_REVIEW" in text
    assert "silver nova ship" in text.lower()


def test_generate_alt_text_uses_injected_vision_fn():
    text = generate_alt_text("https://example.com/x.png", vision_fn=lambda src: "A cruise ship at sunset")
    assert text == "A cruise ship at sunset"


def test_generate_alt_text_falls_back_when_vision_fn_raises():
    def _boom(src):
        raise RuntimeError("no network")
    text = generate_alt_text("https://example.com/x.png", vision_fn=_boom)
    assert "NEEDS_REVIEW" in text


# --------------------------------------------------------------------------
# Report generation
# --------------------------------------------------------------------------

def test_build_report_shape():
    audits = [audit_html('<html><body><img src="x.png"></body></html>', filename="a.html")]
    report = build_report(audits)
    assert report["standard"] == "WCAG 2.1 AA"
    assert report["files_scanned"] == 1
    assert report["total_violations"] == 1
    assert report["violations_by_rule"]["missing-alt"] == 1
    assert report["files_with_violations"] == 1


def test_write_report_creates_json_file(tmp_path):
    audits = [audit_html('<html><body><img src="x.png" alt="ok"></body></html>', filename="clean.html")]
    out_path = write_report(audits, tmp_path)
    assert out_path.exists()
    assert out_path.name.startswith("audit_report_")
    import json
    data = json.loads(out_path.read_text())
    assert data["total_violations"] == 0


# --------------------------------------------------------------------------
# Integration: 3 REAL D2M client itinerary HTMLs shipped in this repo.
#
# These numbers were hand-verified against the WCAG relative-luminance
# formula in a standalone script before being encoded as assertions (see
# session notes) — they are not just "whatever the tool currently outputs."
# Two are genuine, previously-unknown accessibility bugs in the shared
# itinerary CSS template (tag-yellow badges + the .savings callout).
# --------------------------------------------------------------------------

LOUCKS_SILVER_NOVA = REPO_ROOT / "dossiers" / "Loucks_SilverNova_May2027_Excursions_v2_SUPPLEMENT.html"
KUKLINSKI_VIKING = REPO_ROOT / "dossiers" / "Kuklinski_VikingMars_Dec2026_Excursions_SUPPLEMENT.html"
FURLOW_VOYAGE_PREVIEW = REPO_ROOT / "drafts" / "Grandeur_Furlow_TP11_Voyage_Preview_20260621.html"

pytestmark_real_files = pytest.mark.skipif(
    not (LOUCKS_SILVER_NOVA.exists() and KUKLINSKI_VIKING.exists() and FURLOW_VOYAGE_PREVIEW.exists()),
    reason="real repo fixture files not present in this checkout",
)


@pytestmark_real_files
def test_real_file_loucks_silver_nova_excursions():
    """Shared `.tag-yellow` badge class (white text on #b8860b) is 3.25:1,
    fails AA's 4.5:1 for normal-weight body-size text. The `.savings`
    class (#4cff4c bright green on #f7f3ea cream) is 1.21:1 — essentially
    invisible. Both are genuine bugs in a template used across every
    excursion supplement (Loucks AND Kuklinski share this CSS)."""
    audit = audit_file(LOUCKS_SILVER_NOVA)
    rules = sorted(v.rule for v in audit.violations)
    assert rules == ["contrast-ratio", "contrast-ratio"]
    classes_flagged = {v.element for v in audit.violations}
    assert any("tag-yellow" in c for c in classes_flagged)
    assert any("savings" in c for c in classes_flagged)


@pytestmark_real_files
def test_real_file_kuklinski_viking_mars_shares_the_same_template_bug():
    audit = audit_file(KUKLINSKI_VIKING)
    assert len(audit.violations) == 2
    assert all(v.rule == "contrast-ratio" for v in audit.violations)


@pytestmark_real_files
def test_real_file_furlow_voyage_preview_is_clean():
    """The canonical dark-navy lifecycle email template has no detectable
    WCAG violations — a true-negative check so the auditor isn't just
    finding violations everywhere."""
    audit = audit_file(FURLOW_VOYAGE_PREVIEW)
    assert audit.violations == []


@pytestmark_real_files
def test_real_file_fix_engine_clears_loucks_violations():
    html_text = LOUCKS_SILVER_NOVA.read_text(encoding="utf-8")
    audit = audit_html(html_text, filename=str(LOUCKS_SILVER_NOVA))
    fixed_html, applied = apply_fixes(html_text, audit)
    assert len(applied) == 2
    refixed_audit = audit_html(fixed_html, filename="fixed")
    assert refixed_audit.violations == []

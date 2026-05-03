#!/usr/bin/env python3
"""
Comprehensive Test Suite for Gmail Template Solution
Tests both the preprocessor and the draft creator end-to-end.

Run: python3 test_gmail_template_solution.py
"""

import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

# Import modules
try:
    from gmail_template_stripper import GmailSafePreprocessor, TransformationLog
except ImportError:
    print("ERROR: Could not import gmail_template_stripper")
    sys.exit(1)

# ============================================================================
# TEST FIXTURES
# ============================================================================

# Test case 1: Basic HTML with inline styles
TEST_BASIC_HTML = """
<html>
<head>
    <title>Test Email</title>
    <style>
        body { background-color: #f7f3ea; color: #0000ff; font-family: Georgia, serif; }
        .header { padding: 20px; margin: 0; }
        .content { padding: 10px; }
        .unsafe { animation: spin 2s; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome</h1>
    </div>
    <div class="content">
        <p>This is a test email.</p>
    </div>
</body>
</html>
"""

# Test case 2: HTML with unsafe tags
TEST_UNSAFE_TAGS = """
<html>
<body>
    <script>alert('XSS');</script>
    <style>
        p { color: red; }
    </style>
    <p>Safe paragraph</p>
    <svg onload="alert('SVG XSS')">
        <circle cx="50" cy="50" r="40" />
    </svg>
    <iframe src="https://evil.com"></iframe>
</body>
</html>
"""

# Test case 3: HTML with unsafe CSS
TEST_UNSAFE_CSS = """
<html>
<body>
    <style>
        div {
            position: fixed;
            animation: slide 1s;
            pointer-events: none;
            transform: rotate(45deg);
            color: blue;
            padding: 10px;
        }
    </style>
    <div>This has unsafe CSS properties</div>
</body>
</html>
"""

# Test case 4: HTML with layout divs (for div→table conversion)
TEST_LAYOUT_DIVS = """
<html>
<body>
    <div style="width: 600px; padding: 20px; margin: 0;">
        <div style="background-color: #f0f0f0; padding: 10px;">
            <h2>Section 1</h2>
            <p>Content here</p>
        </div>
        <div style="width: 100%; height: 100px;">
            <img src="image.png" />
        </div>
    </div>
</body>
</html>
"""

# Test case 5: Malformed HTML
TEST_MALFORMED_HTML = """
<html>
    <body>
        <p>Unclosed paragraph
        <p>Another unclosed</p>
        <div>Div not closed
    </body>
</html>
"""

# Test case 6: D2M Brand Stationery
TEST_D2M_STATIONERY = """
<html>
<head>
    <style>
        body {
            background-color: #f7f3ea;
            color: #0000ff;
            font-family: Georgia, serif;
            margin: 0;
            padding: 20px;
        }
        .logo-banner {
            background-color: #0000ff;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 20px;
            line-height: 1.6;
        }
        .signature {
            border-top: 1px solid #0000ff;
            padding-top: 10px;
            margin-top: 20px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="logo-banner">
        <h1>Dreams2Memories Travel</h1>
    </div>
    <div class="content">
        <p>Dear Client,</p>
        <p>Your itinerary is ready.</p>
        <p>Best regards,<br>The D2M Team</p>
    </div>
    <div class="signature">
        <p>© 2026 Dreams2Memories Travel, LLC</p>
    </div>
</body>
</html>
"""

# Test case 7: Complex email with table
TEST_TABLE_EMAIL = """
<html>
<body>
    <style>
        table { width: 100%; border-collapse: collapse; }
        td { padding: 10px; border: 1px solid #ddd; }
    </style>
    <table>
        <tr>
            <td>Destination</td>
            <td>Price</td>
        </tr>
        <tr>
            <td>Bora Bora</td>
            <td>$5,000</td>
        </tr>
    </table>
</body>
</html>
"""

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_case(
    name: str,
    html: str,
    checks: List[Tuple[str, callable]]
) -> bool:
    """
    Run a single test case.

    Args:
        name: Test name
        html: Input HTML
        checks: List of (description, check_function) tuples
                check_function takes processed_html and returns bool

    Returns: True if all checks pass
    """
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")

    # Process HTML
    preprocessor = GmailSafePreprocessor()
    try:
        result, log = preprocessor.process(html)
    except Exception as e:
        print(f"✗ FAIL — Preprocessing failed: {e}")
        return False

    # Print summary
    print(f"Input:  {log.input_size:,} bytes")
    print(f"Output: {log.output_size:,} bytes")
    print(f"Changes: {log.summary()}")

    # Run checks
    all_passed = True
    for check_desc, check_fn in checks:
        try:
            passed = check_fn(result)
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}: {check_desc}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"  ✗ FAIL: {check_desc} — {e}")
            all_passed = False

    return all_passed

# ============================================================================
# INDIVIDUAL TESTS
# ============================================================================

def test_1_basic_html():
    """Test basic HTML processing with style inlining."""
    checks = [
        ("Contains <h1>", lambda html: "<h1>" in html),
        ("Contains <p>", lambda html: "<p>" in html),
        ("Inline styles applied", lambda html: "style=" in html),
        ("No <style> block remains", lambda html: "<style>" not in html.lower()),
        ("Background color inlined", lambda html: "#f7f3ea" in html or "#f7f3ea" in html.lower()),
    ]
    return test_case("1. Basic HTML Processing", TEST_BASIC_HTML, checks)

def test_2_unsafe_tags():
    """Test removal of unsafe tags."""
    checks = [
        ("No <script> tags", lambda html: "<script>" not in html.lower()),
        ("No <iframe> tags", lambda html: "<iframe>" not in html.lower()),
        ("No <svg> tags", lambda html: "<svg>" not in html.lower()),
        ("Safe <p> tag remains", lambda html: "<p>" in html),
        ("Safe paragraph text present", lambda html: "Safe paragraph" in html),
    ]
    return test_case("2. Unsafe Tag Removal", TEST_UNSAFE_TAGS, checks)

def test_3_unsafe_css():
    """Test removal of unsafe CSS properties."""
    checks = [
        ("Animation removed", lambda html: "animation" not in html.lower()),
        ("Position fixed removed", lambda html: "position: fixed" not in html.lower()),
        ("Pointer-events removed", lambda html: "pointer-events" not in html.lower()),
        ("Transform removed", lambda html: "transform" not in html.lower()),
        ("Safe color property kept", lambda html: "color" in html.lower()),
        ("Safe padding property kept", lambda html: "padding" in html.lower()),
    ]
    return test_case("3. Unsafe CSS Removal", TEST_UNSAFE_CSS, checks)

def test_4_layout_divs():
    """Test div to table conversion."""
    checks = [
        ("Contains <table>", lambda html: "<table>" in html or "<table " in html),
        ("Contains <tr>", lambda html: "<tr>" in html or "<tr " in html),
        ("Contains <td>", lambda html: "<td>" in html or "<td " in html),
        ("Content preserved", lambda html: "Section 1" in html),
        ("Styles inlined", lambda html: "style=" in html),
    ]
    return test_case("4. Div to Table Conversion", TEST_LAYOUT_DIVS, checks)

def test_5_malformed_html():
    """Test handling of malformed HTML."""
    checks = [
        ("Does not crash", lambda html: len(html) > 0),
        ("Content preserved", lambda html: "Unclosed paragraph" in html),
        ("Basic structure", lambda html: "<" in html and ">" in html),
    ]
    return test_case("5. Malformed HTML Handling", TEST_MALFORMED_HTML, checks)

def test_6_d2m_branding():
    """Test D2M brand stationery preservation."""
    checks = [
        ("D2M cream background (#f7f3ea)", lambda html: "#f7f3ea" in html.lower()),
        ("D2M blue ink (#0000ff)", lambda html: "#0000ff" in html.lower()),
        ("Georgia font family", lambda html: "georgia" in html.lower()),
        ("Logo banner present", lambda html: "Dreams2Memories" in html),
        ("Signature preserved", lambda html: "© 2026" in html),
        ("No <style> blocks remain", lambda html: "<style>" not in html.lower()),
    ]
    return test_case("6. D2M Brand Stationery", TEST_D2M_STATIONERY, checks)

def test_7_table_structure():
    """Test preservation of table structures."""
    checks = [
        ("Table structure preserved", lambda html: "<table>" in html or "<table " in html),
        ("Table data preserved", lambda html: "Bora Bora" in html and "$5,000" in html),
        ("Style inlined", lambda html: "style=" in html),
        ("No <style> blocks", lambda html: "<style>" not in html.lower()),
    ]
    return test_case("7. Table Email Preservation", TEST_TABLE_EMAIL, checks)

# ============================================================================
# CHARSET AND ENCODING TESTS
# ============================================================================

def test_8_charset():
    """Test charset meta tag."""
    html = "<html><body><p>Test</p></body></html>"
    preprocessor = GmailSafePreprocessor(charset="utf-8")
    result, _ = preprocessor.process(html)

    checks = [
        ("Contains charset meta", lambda html: 'charset="utf-8"' in html.lower() or "charset=utf-8" in html.lower()),
        ("Valid HTML structure", lambda html: "<html>" in html and "<body>" in html),
    ]

    return test_case("8. Charset Handling", html, checks)

# ============================================================================
# FILE I/O TESTS
# ============================================================================

def test_9_file_io():
    """Test file loading and saving."""
    print(f"\n{'='*70}")
    print(f"TEST: 9. File I/O Operations")
    print(f"{'='*70}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write test HTML to file
        input_file = tmpdir / "input.html"
        input_file.write_text(TEST_BASIC_HTML, encoding="utf-8")

        # Process
        from create_gmail_draft_direct_v2 import preprocess_html
        try:
            result, log = preprocess_html(TEST_BASIC_HTML)
            print(f"✓ PASS: Preprocessing completed")
        except Exception as e:
            print(f"✗ FAIL: Preprocessing failed: {e}")
            return False

        # Write output
        output_file = tmpdir / "output.html"
        output_file.write_text(result, encoding="utf-8")

        # Verify file was created
        if output_file.exists():
            size = output_file.stat().st_size
            print(f"✓ PASS: Output file created ({size} bytes)")
            return True
        else:
            print(f"✗ FAIL: Output file not created")
            return False

# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_10_empty_html():
    """Test handling of empty/minimal HTML."""
    html = "<html></html>"
    preprocessor = GmailSafePreprocessor()

    try:
        result, log = preprocessor.process(html)
        print(f"\n{'='*70}")
        print(f"TEST: 10. Empty HTML Handling")
        print(f"{'='*70}")
        print(f"✓ PASS: Empty HTML processed without error")
        return True
    except Exception as e:
        print(f"✗ FAIL: Empty HTML caused error: {e}")
        return False

def test_11_large_html():
    """Test handling of large HTML documents."""
    # Create large HTML
    large_html = "<html><body>"
    for i in range(1000):
        large_html += f"<p>Paragraph {i}</p>"
    large_html += "</body></html>"

    preprocessor = GmailSafePreprocessor()

    print(f"\n{'='*70}")
    print(f"TEST: 11. Large HTML Handling ({len(large_html):,} bytes)")
    print(f"{'='*70}")

    try:
        result, log = preprocessor.process(large_html)
        print(f"Input:  {log.input_size:,} bytes")
        print(f"Output: {log.output_size:,} bytes")
        print(f"✓ PASS: Large HTML processed successfully")
        return True
    except Exception as e:
        print(f"✗ FAIL: Large HTML caused error: {e}")
        return False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "GMAIL TEMPLATE SOLUTION TEST SUITE" + " "*19 + "║")
    print("╚" + "="*68 + "╝")

    tests = [
        test_1_basic_html,
        test_2_unsafe_tags,
        test_3_unsafe_css,
        test_4_layout_divs,
        test_5_malformed_html,
        test_6_d2m_branding,
        test_7_table_structure,
        test_8_charset,
        test_9_file_io,
        test_10_empty_html,
        test_11_large_html,
    ]

    results = []
    for test_fn in tests:
        try:
            result = test_fn()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test {test_fn.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    passed = sum(results)
    total = len(results)
    pct = 100 * passed / total if total > 0 else 0

    print(f"Passed: {passed}/{total} ({pct:.1f}%)")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Gmail-Safe HTML Template Preprocessor
Hardens HTML for Gmail's rendering engine by:
  1. Inlining all CSS
  2. Removing disallowed tags/attributes
  3. Converting div layouts to table layouts (Gmail-safe)
  4. Validating HTML structure
  5. Logging transformations for debugging
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from html.parser import HTMLParser

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    raise ImportError("Install BeautifulSoup4: pip install beautifulsoup4")

# ============================================================================
# LOGGING SETUP
# ============================================================================

logger = logging.getLogger("gmail_template_stripper")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ============================================================================
# GMAIL-SAFE CONSTANTS
# ============================================================================

# Tags Gmail keeps (allow list)
GMAIL_SAFE_TAGS = {
    "html", "head", "body", "meta", "title", "style",
    "p", "div", "span", "a", "strong", "b", "em", "i", "u", "s",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "tbody", "thead", "tfoot", "tr", "td", "th",
    "img", "br", "hr",
    "blockquote", "pre", "code",
    "font", "center", "line-height"  # Legacy but safe
}

# Attributes Gmail strips
GMAIL_UNSAFE_ATTRS = {
    "onclick", "onerror", "onload", "onmouseover", "onmouseout",
    "onchange", "onsubmit", "onkeydown", "onkeyup",
    "class", "id", "style",  # Will re-inline
    "data-*", "aria-*",  # ARIA attributes stripped
    "xmlns", "xmlns:xlink", "xlink:href"  # SVG-related
}

# CSS properties Gmail strips or deprecates
GMAIL_UNSAFE_CSS = {
    "animation", "transition", "transform", "filter",
    "box-shadow", "text-shadow", "backdrop-filter",
    "display: grid", "display: flex", "display: inline-flex",
    "position: fixed", "position: sticky",
    "pointer-events", "cursor",
    "clip-path", "mask", "mask-image"
}

# CSS properties that MUST be inlined (removed from <style> block)
GMAIL_INLINE_ONLY_CSS = {
    "color", "background-color", "font-size", "font-weight", "font-family",
    "text-align", "padding", "margin", "border", "width", "height",
    "line-height", "letter-spacing", "text-decoration", "font-style"
}

# D2M Brand Defaults (cream + blue)
D2M_DEFAULTS = {
    "background_color": "#f7f3ea",
    "ink_color": "#0000ff",
    "font_family": "Georgia, serif"
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TransformationLog:
    """Track what was changed during preprocessing"""
    input_size: int
    output_size: int
    tags_removed: List[str]
    attrs_inlined: Dict[str, int]  # attr_name -> count
    css_unsafe_removed: List[str]
    div_to_table_conversions: int
    errors: List[str]

    def summary(self) -> str:
        return (
            f"Size: {self.input_size} → {self.output_size} bytes | "
            f"Tags removed: {', '.join(set(self.tags_removed)) or 'none'} | "
            f"Divs→Tables: {self.div_to_table_conversions} | "
            f"Errors: {len(self.errors)}"
        )

# ============================================================================
# CORE STRIPPER CLASS
# ============================================================================

class GmailSafePreprocessor:
    """
    Transforms HTML to survive Gmail's sanitization engine.

    Process:
      1. Parse HTML with BeautifulSoup
      2. Extract all <style> blocks and inline CSS into element styles
      3. Remove unsafe tags and attributes
      4. Convert div layouts to nested tables (Gmail-safe)
      5. Validate and re-serialize
    """

    def __init__(self, charset: str = "utf-8"):
        self.charset = charset
        self.log = TransformationLog(
            input_size=0,
            output_size=0,
            tags_removed=[],
            attrs_inlined={},
            css_unsafe_removed=[],
            div_to_table_conversions=0,
            errors=[]
        )

    def process(self, html: str) -> Tuple[str, TransformationLog]:
        """
        Main entry point: transform HTML to Gmail-safe format.

        Returns: (transformed_html, transformation_log)
        """
        self.log = TransformationLog(
            input_size=len(html),
            output_size=0,
            tags_removed=[],
            attrs_inlined={},
            css_unsafe_removed=[],
            div_to_table_conversions=0,
            errors=[]
        )

        try:
            # Step 1: Parse
            soup = self._parse_html(html)
            if not soup:
                raise ValueError("HTML parsing failed")

            logger.debug(f"✓ Parsed HTML ({self.log.input_size} bytes)")

            # Step 2: Extract and inline CSS
            self._extract_and_inline_styles(soup)
            logger.debug(f"✓ Extracted <style> blocks and inlined CSS")

            # Step 3: Remove unsafe tags/attributes
            self._remove_unsafe_elements(soup)
            logger.debug(f"✓ Removed unsafe tags/attributes")

            # Step 4: Remove unsafe CSS properties
            self._sanitize_inline_styles(soup)
            logger.debug(f"✓ Sanitized inline CSS")

            # Step 5: Convert div layouts to tables (Gmail-safe)
            self._convert_divs_to_tables(soup)
            logger.debug(f"✓ Converted divs to tables")

            # Step 6: Ensure proper encoding
            self._ensure_charset(soup)
            logger.debug(f"✓ Set charset to {self.charset}")

            # Step 7: Re-serialize
            output = self._serialize_html(soup)
            self.log.output_size = len(output)

            logger.info(f"✓ Transform complete: {self.log.summary()}")
            return output, self.log

        except Exception as e:
            self.log.errors.append(str(e))
            logger.error(f"✗ Transform failed: {e}")
            raise

    # ========================================================================
    # STEP IMPLEMENTATIONS
    # ========================================================================

    def _parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """Parse HTML, handle malformed input gracefully."""
        try:
            # Try HTML parser first (more lenient)
            soup = BeautifulSoup(html, "html.parser")

            # Validate we got content
            if not soup.body and not soup.find():
                raise ValueError("HTML parsed but no content found")

            return soup
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            self.log.errors.append(f"Parse error: {e}")
            return None

    def _extract_and_inline_styles(self, soup: BeautifulSoup) -> None:
        """
        Extract all <style> blocks and parse CSS rules.
        Apply matching selectors' styles as inline style attributes.
        """
        styles_to_extract = {}

        # Find all <style> blocks
        for style_tag in soup.find_all("style"):
            css_text = style_tag.string or ""

            # Parse CSS rules (simple parser, handles most cases)
            rules = self._parse_css_rules(css_text)
            styles_to_extract.update(rules)

            # Remove the <style> tag (can't keep it in Gmail draft)
            style_tag.decompose()
            logger.debug(f"  Extracted <style> block ({len(rules)} rules)")

        # Apply extracted styles to matching elements
        for selector, properties in styles_to_extract.items():
            try:
                elements = soup.select(selector)
                for element in elements:
                    self._apply_inline_style(element, properties)
                    self.log.attrs_inlined[selector] = self.log.attrs_inlined.get(selector, 0) + 1
            except Exception as e:
                logger.warning(f"  Could not apply selector '{selector}': {e}")
                self.log.errors.append(f"CSS selector '{selector}': {e}")

    def _parse_css_rules(self, css_text: str) -> Dict[str, Dict[str, str]]:
        """
        Simple CSS rule parser.
        Handles: selector { property: value; property: value; }

        Limitations:
          - No support for @media, @keyframes, etc. (those are removed anyway)
          - Assumes well-formed CSS
        """
        rules = {}

        # Remove comments
        css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

        # Split into rule blocks
        rule_blocks = re.findall(r"([^{]+)\{([^}]+)\}", css_text)

        for selector, properties in rule_blocks:
            selector = selector.strip()

            # Skip at-rules (media queries, keyframes, etc.)
            if selector.startswith("@"):
                continue

            # Parse properties
            props_dict = {}
            for prop in properties.split(";"):
                if ":" not in prop:
                    continue
                key, value = prop.split(":", 1)
                key = key.strip().lower()
                value = re.sub(r"\s*!important\s*$", "", value.strip())

                if key and value:
                    props_dict[key] = value

            if props_dict:
                rules[selector] = props_dict

        return rules

    def _apply_inline_style(self, element: Tag, properties: Dict[str, str]) -> None:
        """Apply CSS properties to an element's inline style attribute."""
        current_style = element.get("style", "")

        # Parse existing inline styles
        existing_props = {}
        for item in current_style.split(";"):
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            existing_props[key.strip().lower()] = value.strip()

        # Merge new properties (new ones override existing)
        existing_props.update(properties)

        # Re-serialize
        style_str = "; ".join(f"{k}: {v}" for k, v in existing_props.items())
        element["style"] = style_str

    def _remove_unsafe_elements(self, soup: BeautifulSoup) -> None:
        """Remove tags that Gmail doesn't support."""
        for tag in soup.find_all(True):  # True = all tags
            # Check if tag is safe
            if tag.name not in GMAIL_SAFE_TAGS:
                self.log.tags_removed.append(tag.name)

                # Keep children, remove tag wrapper
                for child in list(tag.children):
                    tag.insert_before(child)
                tag.decompose()
                logger.debug(f"  Removed unsafe tag: <{tag.name}>")

    def _sanitize_inline_styles(self, soup: BeautifulSoup) -> None:
        """Remove unsafe CSS properties from inline styles."""
        for tag in soup.find_all(True):
            style = tag.get("style", "")
            if not style:
                continue

            # Parse inline style
            props = {}
            for item in style.split(";"):
                if ":" not in item:
                    continue
                key, value = item.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                props[key] = value

            # Filter out unsafe properties
            safe_props = {}
            for key, value in props.items():
                # Check if property is unsafe
                is_unsafe = any(
                    unsafe in f"{key}: {value}".lower()
                    for unsafe in GMAIL_UNSAFE_CSS
                )

                if not is_unsafe:
                    safe_props[key] = value
                else:
                    self.log.css_unsafe_removed.append(f"{key}")
                    logger.debug(f"  Removed unsafe CSS: {key}")

            # Re-apply safe properties
            if safe_props:
                style_str = "; ".join(f"{k}: {v}" for k, v in safe_props.items())
                tag["style"] = style_str
            else:
                # Remove style attribute if no safe properties
                if "style" in tag.attrs:
                    del tag["style"]

    def _convert_divs_to_tables(self, soup: BeautifulSoup) -> None:
        """
        Convert block-level divs to nested tables.

        Rationale: Gmail's rendering engine is table-optimized (legacy HTML emails).
        Divs can render unpredictably. Tables are guaranteed.

        This is a conservative conversion: only convert divs with clear layout semantics.
        """
        layout_divs = self._find_layout_divs(soup)

        for div in layout_divs:
            try:
                table = self._div_to_table(div)
                div.replace_with(table)
                self.log.div_to_table_conversions += 1
                logger.debug(f"  Converted div to table (id={div.get('id')} class={div.get('class')})")
            except Exception as e:
                logger.warning(f"  Could not convert div to table: {e}")
                self.log.errors.append(f"Div→table conversion: {e}")

    def _find_layout_divs(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Identify divs that are used for layout (not semantic content).

        Heuristics:
          - Has width/height/padding/margin in style
          - Has flex/grid/position in style
          - Has data-layout or similar attribute
          - No text content (only children)
        """
        layout_divs = []

        for div in soup.find_all("div"):
            style = div.get("style", "").lower()

            # Check for layout indicators
            has_layout_css = any(
                prop in style
                for prop in ["width:", "height:", "padding:", "margin:", "flex", "grid", "position:"]
            )

            # Check for data attributes
            has_layout_attr = any(
                attr.startswith("data-layout") or attr.startswith("data-grid")
                for attr in div.attrs
            )

            # Only convert if it looks like a layout div
            if has_layout_css or has_layout_attr:
                layout_divs.append(div)

        return layout_divs

    def _div_to_table(self, div: Tag) -> Tag:
        """Convert a single div to a table."""
        table = BeautifulSoup("<table></table>", "html.parser").table
        tbody = BeautifulSoup("<tbody></tbody>", "html.parser").tbody
        tr = BeautifulSoup("<tr></tr>", "html.parser").tr
        td = BeautifulSoup("<td></td>", "html.parser").td

        # Copy style from div to td
        if div.get("style"):
            td["style"] = div.get("style")

        # Copy content from div to td
        for child in list(div.children):
            td.append(child)

        tr.append(td)
        tbody.append(tr)
        table.append(tbody)

        return table

    def _ensure_charset(self, soup: BeautifulSoup) -> None:
        """Ensure <meta charset> is set in <head>."""
        head = soup.find("head")
        if not head:
            head = BeautifulSoup(f"<head></head>", "html.parser").head
            soup.insert(0, head)

        # Check if charset meta already exists
        charset_meta = head.find("meta", attrs={"charset": True})
        if not charset_meta:
            charset_meta = BeautifulSoup(
                f'<meta charset="{self.charset}">',
                "html.parser"
            ).find("meta")
            head.insert(0, charset_meta)

    def _serialize_html(self, soup: BeautifulSoup) -> str:
        """Re-serialize soup to HTML string."""
        html = soup.prettify()

        # Ensure proper encoding declaration
        if f'charset="{self.charset}"' not in html.lower():
            # Add charset if missing
            meta_charset = f'<meta charset="{self.charset}">\n'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n{meta_charset}", 1)

        return html

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def process_html_for_gmail(html_path: str, output_path: Optional[str] = None) -> Tuple[str, TransformationLog]:
    """
    Load HTML, process for Gmail, optionally write output.

    Args:
        html_path: Path to input HTML file
        output_path: Optional path to write processed HTML

    Returns:
        (processed_html, transformation_log)
    """
    # Load input
    input_file = Path(html_path)
    if not input_file.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    html = input_file.read_text(encoding="utf-8")
    logger.info(f"Loaded HTML from {html_path} ({len(html)} bytes)")

    # Process
    preprocessor = GmailSafePreprocessor(charset="utf-8")
    processed_html, log = preprocessor.process(html)

    # Optionally write output
    if output_path:
        output_file = Path(output_path)
        output_file.write_text(processed_html, encoding="utf-8")
        logger.info(f"Wrote processed HTML to {output_path}")

    return processed_html, log

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 gmail_template_stripper.py <input_html> [output_html]")
        sys.exit(1)

    input_html = sys.argv[1]
    output_html = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result, log = process_html_for_gmail(input_html, output_html)
        print(f"\n✅ Success: {log.summary()}")
        if log.errors:
            print(f"⚠️  Warnings: {'; '.join(log.errors)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

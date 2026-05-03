#!/usr/bin/env python3
"""
Ironclad Gmail Draft Creator
Enhanced version with:
  - HTML preprocessing (inline styles, remove unsafe tags)
  - Comprehensive error handling
  - Input validation
  - Logging and audit trail
  - Pre-send verification
"""

import json
import base64
import sys
import logging
import argparse
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple
from datetime import datetime

# Email validation
import re

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    print("Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Import the stripper
try:
    from gmail_template_stripper import GmailSafePreprocessor, TransformationLog
except ImportError:
    print("ERROR: Could not import gmail_template_stripper")
    print("Ensure gmail_template_stripper.py is in the same directory")
    sys.exit(1)

# ============================================================================
# LOGGING SETUP
# ============================================================================

logger = logging.getLogger("create_gmail_draft")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_html(html: str, min_length: int = 50) -> Tuple[bool, Optional[str]]:
    """
    Validate HTML structure.

    Returns: (is_valid, error_message)
    """
    if not html:
        return False, "HTML is empty"

    if len(html) < min_length:
        return False, f"HTML is too short ({len(html)} bytes, min {min_length})"

    # Check for basic HTML structure
    if not re.search(r"<html|<body|<div|<p|<table", html, re.IGNORECASE):
        return False, "HTML has no recognized tags"

    # Check for balanced tags (basic check)
    open_tags = len(re.findall(r"<[^/][^>]*>", html))
    close_tags = len(re.findall(r"</[^>]*>", html))
    if open_tags > close_tags + 10:  # Allow some unmatched (self-closing)
        logger.warning(f"⚠️  HTML may have unbalanced tags ({open_tags} open, {close_tags} close)")

    return True, None

def validate_token_file(token_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate token file existence and structure.

    Returns: (is_valid, error_message)
    """
    if not token_path.exists():
        return False, f"Token file not found at {token_path}"

    try:
        with open(token_path) as f:
            data = json.load(f)

        required_fields = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            return False, f"Token missing fields: {', '.join(missing)}"

        # Validate token is not empty
        if not data.get("token") or len(data["token"]) < 10:
            return False, "Token appears invalid or corrupted"

        return True, None

    except json.JSONDecodeError as e:
        return False, f"Token file is not valid JSON: {e}"
    except Exception as e:
        return False, f"Error reading token file: {e}"

# ============================================================================
# GMAIL SERVICE INITIALIZATION
# ============================================================================

def initialize_gmail_service(token_path: Path) -> Tuple[Optional[object], Optional[str]]:
    """
    Initialize Gmail API service with token refresh.

    Returns: (service, error_message)
    """
    try:
        # Validate token file first
        is_valid, error = validate_token_file(token_path)
        if not is_valid:
            return None, error

        logger.info(f"Loading token from {token_path}")

        with open(token_path) as f:
            token_data = json.load(f)

        # Create credentials object
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
        )

        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing...")
            try:
                creds.refresh(Request())
                logger.info("✓ Token refreshed successfully")
            except Exception as e:
                logger.warning(f"⚠️  Token refresh failed: {e}")
                logger.warning("Attempting to proceed with expired token (may fail)...")

        # Build Gmail service
        logger.info("Initializing Gmail API service...")
        service = build("gmail", "v1", credentials=creds)
        logger.info("✓ Gmail service initialized")

        return service, None

    except Exception as e:
        return None, f"Failed to initialize Gmail service: {e}"

# ============================================================================
# HTML PREPROCESSING
# ============================================================================

def preprocess_html(html: str) -> Tuple[str, TransformationLog]:
    """
    Preprocess HTML to survive Gmail's rendering engine.

    Returns: (processed_html, log)
    """
    logger.info(f"Preprocessing HTML ({len(html)} bytes)...")

    preprocessor = GmailSafePreprocessor(charset="utf-8")
    processed_html, log = preprocessor.process(html)

    logger.info(f"✓ Preprocessing complete: {log.summary()}")

    if log.errors:
        logger.warning(f"⚠️  Preprocessing warnings: {'; '.join(log.errors)}")

    return processed_html, log

# ============================================================================
# MIME MESSAGE BUILDING
# ============================================================================

def build_mime_message(
    html_body: str,
    to_email: str,
    subject: str,
    from_email: str = "d2mconcierge@gmail.com"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Build MIME message with HTML body.

    Returns: (raw_message_base64, error_message)
    """
    try:
        logger.info("Building MIME message...")

        # Create multipart message (alternative = prefer HTML over plain text)
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["from"] = from_email
        message["subject"] = subject

        # Add plain text fallback
        plain_text = re.sub(r"<[^>]+>", "", html_body)[:200] + "..."
        msg_plain = MIMEText(plain_text, "plain", "utf-8")
        message.attach(msg_plain)

        # Add HTML part
        msg_html = MIMEText(html_body, "html", "utf-8")
        message.attach(msg_html)

        # Encode message to base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        logger.info(f"✓ MIME message built ({len(raw_message)} bytes base64)")
        return raw_message, None

    except Exception as e:
        return None, f"Failed to build MIME message: {e}"

# ============================================================================
# GMAIL API DRAFT CREATION
# ============================================================================

def create_draft(
    service: object,
    raw_message: str,
    to_email: str,
    subject: str
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Create draft in Gmail.

    Returns: (draft_response, error_message)
    """
    try:
        logger.info("Creating Gmail draft...")

        draft_body = {"message": {"raw": raw_message}}
        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        logger.info(f"✓ Draft created successfully")
        logger.info(f"  Draft ID: {draft_id}")
        logger.info(f"  Message ID: {message_id}")

        return draft, None

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8") if isinstance(error.content, bytes)
            else str(error.content)
        )
        return None, f"Gmail API Error ({error.resp.status}): {error_content}"

    except Exception as e:
        return None, f"Failed to create draft: {e}"

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def create_gmail_draft(
    html_file: str,
    to_email: str,
    subject: str,
    token_file: Optional[str] = None,
    save_preprocessed: Optional[str] = None,
    verbose: bool = False
) -> int:
    """
    Main workflow: load HTML → preprocess → build MIME → create draft.

    Returns: exit code (0=success, 1=failure)
    """
    # ========================================================================
    # STEP 1: SETUP
    # ========================================================================

    logger.info("=" * 70)
    logger.info("GMAIL DRAFT CREATION WORKFLOW")
    logger.info("=" * 70)

    # Set up logging level
    if verbose:
        logger.setLevel(logging.DEBUG)

    # Determine token path
    if not token_file:
        token_file = Path.home() / ".claude" / ".credentials.json"
    else:
        token_file = Path(token_file)

    logger.info(f"Token file: {token_file}")
    logger.info(f"Target email: {to_email}")
    logger.info(f"Subject: {subject}")

    # ========================================================================
    # STEP 2: INPUT VALIDATION
    # ========================================================================

    logger.info("\n[1/5] Validating inputs...")

    # Validate email
    if not validate_email(to_email):
        logger.error(f"✗ Invalid email address: {to_email}")
        return 1

    # Load HTML
    html_file_path = Path(html_file)
    if not html_file_path.exists():
        logger.error(f"✗ HTML file not found: {html_file}")
        return 1

    try:
        html = html_file_path.read_text(encoding="utf-8")
        logger.info(f"✓ Loaded HTML from {html_file} ({len(html)} bytes)")
    except Exception as e:
        logger.error(f"✗ Failed to read HTML file: {e}")
        return 1

    # Validate HTML
    is_valid, error = validate_html(html)
    if not is_valid:
        logger.error(f"✗ HTML validation failed: {error}")
        return 1
    logger.info(f"✓ HTML validation passed")

    # ========================================================================
    # STEP 3: PREPROCESSING
    # ========================================================================

    logger.info("\n[2/5] Preprocessing HTML...")

    try:
        processed_html, preproc_log = preprocess_html(html)

        if save_preprocessed:
            Path(save_preprocessed).write_text(processed_html, encoding="utf-8")
            logger.info(f"✓ Saved preprocessed HTML to {save_preprocessed}")

    except Exception as e:
        logger.error(f"✗ Preprocessing failed: {e}")
        return 1

    # ========================================================================
    # STEP 4: GMAIL SERVICE INITIALIZATION
    # ========================================================================

    logger.info("\n[3/5] Initializing Gmail API...")

    service, error = initialize_gmail_service(token_file)
    if not service:
        logger.error(f"✗ {error}")
        return 1

    # ========================================================================
    # STEP 5: BUILD AND SEND
    # ========================================================================

    logger.info("\n[4/5] Building MIME message...")

    raw_message, error = build_mime_message(processed_html, to_email, subject)
    if not raw_message:
        logger.error(f"✗ {error}")
        return 1

    logger.info("\n[5/5] Creating Gmail draft...")

    draft, error = create_draft(service, raw_message, to_email, subject)
    if not draft:
        logger.error(f"✗ {error}")
        return 1

    # ========================================================================
    # SUCCESS
    # ========================================================================

    logger.info("\n" + "=" * 70)
    logger.info("✅ SUCCESS!")
    logger.info("=" * 70)

    draft_id = draft.get("id")
    message_id = draft.get("message", {}).get("id")

    summary = f"""
Workflow Summary:
  Input HTML:           {len(html):,} bytes
  Preprocessed HTML:    {len(processed_html):,} bytes
  Size reduction:       {100 * (1 - len(processed_html) / len(html)):.1f}%
  Draft ID:             {draft_id}
  Message ID:           {message_id}
  To:                   {to_email}
  Subject:              {subject}

Preprocessing Changes:
  {preproc_log.summary()}
  Tags removed:         {', '.join(set(preproc_log.tags_removed)) or 'none'}
  CSS unsafe removed:   {', '.join(set(preproc_log.css_unsafe_removed)) or 'none'}
  Div→Table conversions: {preproc_log.div_to_table_conversions}
"""

    logger.info(summary)

    logger.info("\nAccess draft at:")
    logger.info(f"  https://mail.google.com/mail/?ui=2&view=cm&fs=1&tf=0&to={to_email}")

    return 0

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create Gmail draft with hardened HTML preprocessing"
    )
    parser.add_argument(
        "--html", required=True,
        help="Path to HTML file"
    )
    parser.add_argument(
        "--to", required=True,
        help="Recipient email address"
    )
    parser.add_argument(
        "--subject", required=True,
        help="Email subject"
    )
    parser.add_argument(
        "--token",
        help="Path to OAuth token file (default: ~/.claude/.credentials.json)"
    )
    parser.add_argument(
        "--save-preprocessed",
        help="Save preprocessed HTML to file for inspection"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    exit_code = create_gmail_draft(
        html_file=args.html,
        to_email=args.to,
        subject=args.subject,
        token_file=args.token,
        save_preprocessed=args.save_preprocessed,
        verbose=args.verbose
    )

    return exit_code

if __name__ == "__main__":
    sys.exit(main())

"""
Dreams2Memories Google Forms MCP Module
========================================

Extends the travel MCP server with Google Forms operations:
- Create forms and add questions
- Collect and read form responses
- Look up form metadata
- Discover forms via Drive

Auth: Uses unified OAuth token from thunderbird_google_auth.
The Forms API scope is already included in gmail_token.json scopes.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth
"""

import json
import logging
import time
import functools
from pathlib import Path
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from api.thunderbird_google_auth import get_forms, get_drive

# Configuration
THUNDERBIRD_DIR = Path.home() / "Thunderbird"

logger = logging.getLogger(__name__)


def _retry_on_error(func):
    """Retry wrapper for transient Google API errors (429, 500, 503)."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        retries = 3
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status in (429, 500, 503) and attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Forms API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _escape_query(value: str) -> str:
    """Escape single quotes for Drive API query strings."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def register_forms_mcp_tools(mcp: FastMCP):
    """Register all Google Forms tools with the MCP server."""

    @mcp.tool(
        name="forms_create_form",
        annotations={"title": "Create Google Form", "readOnlyHint": False},
    )
    @_retry_on_error
    async def forms_create_form(
        title: str = Field(..., description="Form title"),
        description: str = Field("", description="Optional form description"),
    ) -> str:
        """Create a new Google Form with the given title and optional description."""
        try:
            service = get_forms()

            # Forms API only allows info.title on create — info.description (and
            # everything else) must go through a follow-up batchUpdate, or create
            # 400s with "Only info.title can be set when creating a form."
            body = {"info": {"title": title}}
            result = service.forms().create(body=body).execute()
            form_id = result.get("formId", "")

            if description:
                service.forms().batchUpdate(
                    formId=form_id,
                    body={"requests": [{
                        "updateFormInfo": {
                            "info": {"description": description},
                            "updateMask": "description",
                        }
                    }]},
                ).execute()
                result.setdefault("info", {})["description"] = description

            responder_uri = result.get("responderUri", "")
            form_url = result.get("info", {}).get("documentTitle", "")

            return json.dumps({
                "status": "success",
                "form_id": form_id,
                "title": result.get("info", {}).get("title", title),
                "url": responder_uri,
                "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
            }, indent=2)

        except HttpError as e:
            logger.error(f"Forms create error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "forms_error"})
        except Exception as e:
            logger.error(f"Forms create error: {e}")
            return json.dumps({"error": str(e), "type": "forms_error"})

    @mcp.tool(
        name="forms_add_question",
        annotations={"title": "Add Question to Form", "readOnlyHint": False},
    )
    @_retry_on_error
    async def forms_add_question(
        form_id: str = Field(..., description="Google Form ID"),
        question_text: str = Field(..., description="Question text"),
        question_type: str = Field(
            "TEXT",
            description="Question type: TEXT, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOX, DROPDOWN",
        ),
        choices_json: str = Field(
            "",
            description='JSON array of choice strings for choice types, e.g. ["A","B","C"]',
        ),
    ) -> str:
        """Add a question to an existing Google Form.

        Supports text, paragraph, multiple choice, checkbox, and dropdown types.
        For choice-based types, provide choices_json.
        """
        try:
            service = get_forms()
            qtype = question_type.upper()

            # Build the question item
            question_item = {}

            if qtype in ("MULTIPLE_CHOICE", "CHECKBOX", "DROPDOWN"):
                # Parse choices
                choices = []
                if choices_json:
                    try:
                        parsed = json.loads(choices_json)
                        if isinstance(parsed, list):
                            choices = [{"value": str(c)} for c in parsed]
                    except (json.JSONDecodeError, TypeError) as e:
                        return json.dumps({
                            "error": f"Invalid choices_json: {e}",
                            "type": "forms_error",
                        })

                if not choices:
                    return json.dumps({
                        "error": f"Question type '{qtype}' requires at least one choice in choices_json",
                        "type": "forms_error",
                    })

                choice_type_map = {
                    "MULTIPLE_CHOICE": "RADIO",
                    "CHECKBOX": "CHECKBOX",
                    "DROPDOWN": "DROP_DOWN",
                }

                question_item["choiceQuestion"] = {
                    "type": choice_type_map[qtype],
                    "options": choices,
                }

            elif qtype == "PARAGRAPH":
                question_item["textQuestion"] = {
                    "paragraph": True,
                }

            else:  # TEXT (default)
                question_item["textQuestion"] = {}

            # Build the batch update request
            body = {
                "requests": [
                    {
                        "createItem": {
                            "item": {
                                "title": question_text,
                                "questionItem": {
                                    "question": question_item,
                                },
                            },
                            "location": {"index": 0},
                        }
                    }
                ]
            }

            result = service.forms().batchUpdate(formId=form_id, body=body).execute()

            created_id = None
            replies = result.get("replies", [])
            if replies:
                create_reply = replies[0].get("createItem", {})
                created_id = create_reply.get("itemId")

            return json.dumps({
                "status": "success",
                "form_id": form_id,
                "question": question_text,
                "question_type": qtype,
                "item_id": created_id,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Forms add question error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "forms_error"})
        except Exception as e:
            logger.error(f"Forms add question error: {e}")
            return json.dumps({"error": str(e), "type": "forms_error"})

    @mcp.tool(
        name="forms_get_responses",
        annotations={"title": "Get Form Responses", "readOnlyHint": True},
    )
    @_retry_on_error
    async def forms_get_responses(
        form_id: str = Field(..., description="Google Form ID"),
    ) -> str:
        """Get all form responses submitted for a Google Form.

        Returns a list of response objects with answer data.
        """
        try:
            service = get_forms()

            result = service.forms().responses().list(formId=form_id).execute()
            responses = result.get("responses", [])

            # Enrich with question titles for readability
            try:
                form_info = service.forms().get(formId=form_id).execute()
                items = form_info.get("items", [])
                question_map = {}
                for item in items:
                    qid = item.get("questionItem", {}).get("question", {}).get("questionId")
                    if qid:
                        question_map[qid] = item.get("title", "")
            except Exception:
                question_map = {}

            enriched = []
            for resp in responses:
                answers = resp.get("answers", {})
                enriched_answers = []
                for qid, answer_data in answers.items():
                    entry = {
                        "question_id": qid,
                        "question": question_map.get(qid, ""),
                    }
                    # Extract the actual answer value
                    text_answers = answer_data.get("textAnswers", {}).get("answers", [])
                    if text_answers:
                        entry["answer"] = text_answers[0].get("value", "")
                    else:
                        entry["answer"] = ""
                    enriched_answers.append(entry)

                enriched.append({
                    "response_id": resp.get("responseId", ""),
                    "create_time": resp.get("createTime", ""),
                    "last_submitted_time": resp.get("lastSubmittedTime", ""),
                    "answers": enriched_answers,
                })

            return json.dumps({
                "status": "success",
                "form_id": form_id,
                "response_count": len(enriched),
                "responses": enriched,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Forms get responses error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "forms_error"})
        except Exception as e:
            logger.error(f"Forms get responses error: {e}")
            return json.dumps({"error": str(e), "type": "forms_error"})

    @mcp.tool(
        name="forms_get_form_info",
        annotations={"title": "Get Form Info", "readOnlyHint": True},
    )
    @_retry_on_error
    async def forms_get_form_info(
        form_id: str = Field(..., description="Google Form ID"),
    ) -> str:
        """Get metadata about a Google Form: title, description, item count, response count, URL."""
        try:
            service = get_forms()

            form = service.forms().get(formId=form_id).execute()

            info = form.get("info", {})
            items = form.get("items", [])
            responder_uri = form.get("responderUri", "")

            # Get response count
            try:
                responses_result = service.forms().responses().list(formId=form_id).execute()
                response_count = len(responses_result.get("responses", []))
            except Exception:
                response_count = 0

            # Extract item summary
            question_summary = []
            for item in items:
                q_item = item.get("questionItem", {})
                question = q_item.get("question", {})
                qtype = "TEXT"
                if "choiceQuestion" in question:
                    cq = question["choiceQuestion"]
                    qtype = cq.get("type", "CHOICE")
                    options = [o.get("value", "") for o in cq.get("options", [])]
                elif "textQuestion" in question:
                    qtype = "PARAGRAPH" if question["textQuestion"].get("paragraph") else "TEXT"
                    options = []
                else:
                    options = []

                question_summary.append({
                    "item_id": item.get("itemId", ""),
                    "title": item.get("title", ""),
                    "type": qtype,
                    "options": options if options else None,
                    "required": question.get("required", False),
                })

            return json.dumps({
                "status": "success",
                "form_id": form_id,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "document_title": info.get("documentTitle", ""),
                "responder_uri": responder_uri,
                "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
                "question_count": len(question_summary),
                "response_count": response_count,
                "questions": question_summary,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Forms get info error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "forms_error"})
        except Exception as e:
            logger.error(f"Forms get info error: {e}")
            return json.dumps({"error": str(e), "type": "forms_error"})

    @mcp.tool(
        name="forms_list_forms",
        annotations={"title": "List Google Forms", "readOnlyHint": True},
    )
    @_retry_on_error
    async def forms_list_forms(
        query: str = Field("", description="Optional search query to filter form names"),
    ) -> str:
        """List Google Forms in Drive. Uses Drive API with mimeType filter.

        Optionally filter by name with the query parameter.
        Returns form id, name, and URL for each form found.
        """
        try:
            drive = get_drive()

            query_parts = [
                "mimeType = 'application/vnd.google-apps.form'",
                "trashed = false",
            ]
            if query:
                safe_query = _escape_query(query)
                query_parts.append(f"name contains '{safe_query}'")

            q = " and ".join(query_parts)

            results = (
                drive.files()
                .list(
                    q=q,
                    pageSize=100,
                    fields="files(id, name, modifiedTime, createdTime, webViewLink)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )

            files = results.get("files", [])

            # Build Form edit/view URLs
            enriched = []
            for f in files:
                enriched.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "modified_time": f.get("modifiedTime"),
                    "created_time": f.get("createdTime"),
                    "edit_url": f"https://docs.google.com/forms/d/{f['id']}/edit",
                    "view_url": f"https://docs.google.com/forms/d/{f['id']}/viewform",
                    "drive_url": f.get("webViewLink"),
                })

            return json.dumps({
                "status": "success",
                "query": query,
                "count": len(enriched),
                "forms": enriched,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Forms list error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "forms_error"})
        except Exception as e:
            logger.error(f"Forms list error: {e}")
            return json.dumps({"error": str(e), "type": "forms_error"})

    logger.info("Google Forms MCP tools registered successfully")


if __name__ == "__main__":
    print("Google Forms MCP Module")
    print("=======================")
    print()
    print("This module registers MCP tools with a FastMCP server.")
    print("Import and call register_forms_mcp_tools(mcp) from your server setup.")
    print()
    print("Prerequisites:")
    print("  1. gmail_token.json must exist with forms scope")
    print("     Run: python3 api/thunderbird_google_auth.py --status")
    print("  2. If forms scope is missing, re-authorize:")
    print("     python3 api/thunderbird_google_auth.py --authorize")

"""
Dreams2Memories Google People / Contacts MCP Module
====================================================

Extends the travel MCP server with Google People API operations:
- Search contacts by name, email, or phone
- Get full contact details by resource name
- Create new contacts
- Update existing contact fields
- List all contacts with pagination

Auth: OAuth 2.0 via thunderbird_google_auth (unified token).
Uses People API v1 — contacts scope already in master token.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import time
import functools
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from api.thunderbird_google_auth import get_people

logger = logging.getLogger(__name__)

# Fields to request for all contact reads
_CONTACT_FIELDS = "names,emailAddresses,phoneNumbers,organizations,photos,urls,addresses,birthdays,biographies"

_CONTACT_FIELDS_MINI = "names,emailAddresses,phoneNumbers,organizations"


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
                    logger.warning(f"People API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _safe_name(names: list) -> str:
    """Extract display name from People API names list."""
    if not names:
        return ""
    n = names[0]
    parts = [p for p in (n.get("givenName", ""), n.get("middleName", ""), n.get("familyName", "")) if p]
    return " ".join(parts) or n.get("displayName", "")


def _safe_email(emails: list) -> str:
    """Extract first email value from People API emailAddresses list."""
    if not emails:
        return ""
    return emails[0].get("value", "")


def _safe_phone(phones: list) -> str:
    """Extract first phone value from People API phoneNumbers list."""
    if not phones:
        return ""
    return phones[0].get("canonicalForm", phones[0].get("value", ""))


def _safe_org(orgs: list) -> str:
    """Extract organization name from People API organizations list."""
    if not orgs:
        return ""
    return orgs[0].get("name", "")


def _summarize_contact(person: dict) -> dict:
    """Return a summary dict for a contact person resource."""
    return {
        "resource_name": person.get("resourceName", ""),
        "name": _safe_name(person.get("names", [])),
        "email": _safe_email(person.get("emailAddresses", [])),
        "phone": _safe_phone(person.get("phoneNumbers", [])),
        "organization": _safe_org(person.get("organizations", [])),
        "etag": person.get("etag", ""),
    }


def register_contacts_mcp_tools(mcp: FastMCP):
    """Register all Google People/Contacts tools with the MCP server."""

    @mcp.tool(
        name="contacts_search",
        annotations={"title": "Search Google Contacts", "readOnlyHint": True},
    )
    @_retry_on_error
    async def contacts_search(
        query: str = Field(..., description="Search query — matches name, email, or phone number"),
        page_size: int = Field(20, description="Maximum results to return (1-100)", ge=1, le=100),
    ) -> str:
        """Search contacts by name, email, or phone number.

        Returns matching contacts with names, emails, phone numbers, and organizations.
        """
        try:
            service = get_people()

            results = (
                service.people()
                .searchContacts(
                    query=query,
                    pageSize=min(page_size, 100),
                    readMask=_CONTACT_FIELDS_MINI,
                )
                .execute()
            )

            matches = results.get("results", [])
            contacts = [_summarize_contact(m.get("person", {})) for m in matches]

            return json.dumps(
                {"status": "success", "query": query, "count": len(contacts), "contacts": contacts},
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Contacts search error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "people_error"})
        except Exception as e:
            logger.error(f"Contacts search error: {e}")
            return json.dumps({"error": str(e), "type": "people_error"})

    @mcp.tool(
        name="contacts_get",
        annotations={"title": "Get Contact Details", "readOnlyHint": True},
    )
    @_retry_on_error
    async def contacts_get(
        resource_name: str = Field(..., description="Contact resource name, e.g. 'people/c12345'"),
    ) -> str:
        """Get full details for a specific contact by resource name.

        Returns all available fields: names, emails, phones, organizations,
        addresses, photos, URLs, birthdays, and biographies.
        """
        try:
            service = get_people()

            person = (
                service.people()
                .get(
                    resourceName=resource_name,
                    personFields=_CONTACT_FIELDS,
                )
                .execute()
            )

            return json.dumps({"status": "success", "contact": person}, indent=2, default=str)
        except HttpError as e:
            logger.error(f"Contacts get error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "people_error"})
        except Exception as e:
            logger.error(f"Contacts get error: {e}")
            return json.dumps({"error": str(e), "type": "people_error"})

    @mcp.tool(
        name="contacts_create",
        annotations={"title": "Create Contact", "readOnlyHint": False},
    )
    @_retry_on_error
    async def contacts_create(
        given_name: str = Field(..., description="Contact's first / given name"),
        family_name: str = Field(..., description="Contact's last / family name"),
        email: str = Field("", description="Primary email address"),
        phone: str = Field("", description="Primary phone number"),
        organization: str = Field("", description="Company or organization name"),
    ) -> str:
        """Create a new contact. Minimum: given_name + family_name."""
        try:
            service = get_people()

            names = [{"givenName": given_name, "familyName": family_name}]
            body = {"names": names}

            if email:
                body["emailAddresses"] = [{"value": email, "type": "work"}]
            if phone:
                body["phoneNumbers"] = [{"value": phone, "type": "work"}]
            if organization:
                body["organizations"] = [{"name": organization, "type": "work"}]

            person = (
                service.people()
                .createContact(
                    body=body,
                )
                .execute()
            )

            result = _summarize_contact(person)
            return json.dumps({"status": "success", "created": result}, indent=2)
        except HttpError as e:
            logger.error(f"Contacts create error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "people_error"})
        except Exception as e:
            logger.error(f"Contacts create error: {e}")
            return json.dumps({"error": str(e), "type": "people_error"})

    @mcp.tool(
        name="contacts_update",
        annotations={"title": "Update Contact", "readOnlyHint": False},
    )
    @_retry_on_error
    async def contacts_update(
        resource_name: str = Field(..., description="Contact resource name to update, e.g. 'people/c12345'"),
        given_name: str = Field("", description="New first / given name (leave empty to keep current)"),
        family_name: str = Field("", description="New last / family name (leave empty to keep current)"),
        email: str = Field("", description="New primary email address (leave empty to keep current)"),
        phone: str = Field("", description="New primary phone number (leave empty to keep current)"),
        organization: str = Field("", description="New organization name (leave empty to keep current)"),
    ) -> str:
        """Update an existing contact's fields. Only non-empty fields are updated.

        Uses the People API updateContact method with PATCH semantics.
        Include the contact's etag to prevent overwriting concurrent changes.
        """
        try:
            service = get_people()

            # Fetch current etag and build update masks
            existing = (
                service.people()
                .get(
                    resourceName=resource_name,
                    personFields=_CONTACT_FIELDS,
                )
                .execute()
            )

            body = {"etag": existing.get("etag", "")}
            update_masks = []

            if given_name or family_name:
                curr_names = existing.get("names", [{}])[0] if existing.get("names") else {}
                names_entry = {
                    "givenName": given_name or curr_names.get("givenName", ""),
                    "familyName": family_name or curr_names.get("familyName", ""),
                }
                if "metadata" in curr_names:
                    names_entry["metadata"] = curr_names["metadata"]
                body["names"] = [names_entry]
                update_masks.append("names")

            if email:
                body["emailAddresses"] = [{"value": email, "type": "work"}]
                update_masks.append("emailAddresses")

            if phone:
                body["phoneNumbers"] = [{"value": phone, "type": "work"}]
                update_masks.append("phoneNumbers")

            if organization:
                body["organizations"] = [{"name": organization, "type": "work"}]
                update_masks.append("organizations")

            if not update_masks:
                return json.dumps(
                    {"status": "success", "message": "No fields provided to update — contact unchanged."},
                    indent=2,
                )

            update_person_field = ",".join(update_masks)

            updated = (
                service.people()
                .updateContact(
                    resourceName=resource_name,
                    body=body,
                    updatePersonFields=update_person_field,
                )
                .execute()
            )

            result = _summarize_contact(updated)
            return json.dumps({"status": "success", "updated": result}, indent=2)
        except HttpError as e:
            logger.error(f"Contacts update error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "people_error"})
        except Exception as e:
            logger.error(f"Contacts update error: {e}")
            return json.dumps({"error": str(e), "type": "people_error"})

    @mcp.tool(
        name="contacts_list",
        annotations={"title": "List All Contacts", "readOnlyHint": True},
    )
    @_retry_on_error
    async def contacts_list(
        page_size: int = Field(50, description="Number of contacts per page (1-200)", ge=1, le=200),
    ) -> str:
        """List all contacts with pagination.

        Returns names, email addresses, phone numbers, and organizations.
        If the result includes a nextPageToken, call again with it to get the next page.
        """
        try:
            service = get_people()

            all_contacts = []
            page_token = None
            max_per_page = min(page_size, 200)
            total_wanted = page_size

            while len(all_contacts) < total_wanted:
                params = {
                    "pageSize": max_per_page,
                    "personFields": _CONTACT_FIELDS_MINI,
                }
                if page_token:
                    params["pageToken"] = page_token

                results = service.people().connections().list(
                    resourceName="people/me",
                    **params,
                ).execute()

                connections = results.get("connections", [])
                for c in connections:
                    all_contacts.append(_summarize_contact(c))

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            all_contacts = all_contacts[:total_wanted]

            return json.dumps(
                {
                    "status": "success",
                    "count": len(all_contacts),
                    "contacts": all_contacts,
                    "next_page_token": page_token,
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Contacts list error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "people_error"})
        except Exception as e:
            logger.error(f"Contacts list error: {e}")
            return json.dumps({"error": str(e), "type": "people_error"})

    logger.info("Google People/Contacts tools registered successfully")

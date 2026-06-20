"""
TESSWriteClient — write operations for TESS CRM.
Extends TESSClient with Trip, Booking, and Client creation/update.

All writes go through _api_request() which handles auth and 401 retry.
PUT endpoints return 405 in TESS — use POST + action param for updates.

CRITICAL — Agent DTO shape for POST /Trip and POST /Booking:
  The Agent requires fresh $ProtectedEncrypted tokens (fetched live from GET /User
  and GET /Trip). The Company must include CompanyName, CompanyLegalName,
  CompanyShortName alongside CompanyID.$ProtectedEncrypted.
  See _build_agent_dto() for the canonical pattern. Validated 2026-05-28.
"""
import copy
import logging
from typing import Optional

from core.booking.thunderbird_tess import TESSClient, TESSAuth

logger = logging.getLogger(__name__)


class TESSWriteError(Exception):
    pass


class TESSWriteClient(TESSClient):

    def _build_agent_dto(self) -> dict:
        """Build a fresh Agent DTO suitable for POST /Trip and POST /Booking.

        TESS POST endpoints require:
          - UserID.$ProtectedEncrypted  (time-limited, from GET /User)
          - Company.$ProtectedEncrypted (time-limited, from GET /User)
          - Company.CompanyName / CompanyLegalName / CompanyShortName
          - Contact.FirstName / LastName / ContactType.ID
          - UserName, UserStatus.ID

        The $ProtectedEncrypted tokens are generated server-side per-request and
        must be fetched fresh; cached values cause 500 Internal Server Errors.

        The Agent shape is seeded from an existing Trip GET (which includes the
        correct server-serialised Contact shape), then the encrypted tokens and
        company name fields are replaced with fresh values from GET /User.
        """
        user_id = self.auth._tokens.get("userID") or ""
        if not user_id:
            # userID missing from token file — extract from JWT payload
            import base64 as _b64, json as _json
            try:
                payload_b64 = self.auth._tokens.get("access_token", "").split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = _json.loads(_b64.urlsafe_b64decode(payload_b64))
                user_id = str(payload.get("UserID") or payload.get("userID") or "")
            except Exception:
                pass

        # Fetch fresh encrypted tokens — TESS uses path param, not query string
        fresh_user = self._api_request("GET", f"User/{user_id}")
        if "error" in fresh_user:
            raise TESSWriteError(f"Could not fetch User DTO: {fresh_user['error']}")

        # Seed from an existing trip to get the correct Contact/UserStatus shape
        trips = self._api_request("GET", "Trip", params={
            "pageNumber": 1, "pageSize": 1,
            "sortBy": "CreatedDateTimeUTC", "sortAscending": "false",
        })
        items = trips.get("Items", [])
        if not items:
            raise TESSWriteError("No existing trips found to seed Agent shape")
        seed_agent = copy.deepcopy(items[0]["Agent"])

        # Replace with fresh encrypted tokens
        seed_agent["UserID"] = fresh_user["UserID"]
        seed_agent["Company"]["CompanyID"] = fresh_user["Company"]["CompanyID"]

        # Add name fields required by POST validation (stripped from GET responses)
        seed_agent["Company"]["CompanyName"] = fresh_user["Company"]["CompanyName"]
        seed_agent["Company"]["CompanyLegalName"] = fresh_user["Company"]["CompanyLegalName"]
        seed_agent["Company"]["CompanyShortName"] = fresh_user["Company"]["CompanyShortName"]
        seed_agent["UserName"] = fresh_user.get("UserName", "johnloucks3")

        # Remove server-generated read-only fields
        for k in ("ActivationDateTimeUTC", "MyAccountApplicationSecurityLevel",
                   "CreatedDateTimeUTC", "Permission"):
            seed_agent.pop(k, None)

        return seed_agent

    def create_trip(
        self,
        description: str,
        trip_type_id: int = 2,
        trip_type_name: str = "Vacation",
        trip_main_type_id: int = 1,
        trip_main_type_name: str = "Regular Trip",
        status_id: int = 1,
    ) -> dict:
        """Create a new TESS trip. Returns full API response dict.

        Required TESS POST /Trip shape (validated 2026-05-28):
          TripDescription, Agent (full DTO with fresh $ProtectedEncrypted),
          Extended.TripMainType, Extended.Extended.TripType, TripStatus.
        """
        agent = self._build_agent_dto()
        body = {
            "TripDescription": description,
            "Agent": agent,
            "Extended": {
                "TripMainType": {
                    "TripMainTypeID": trip_main_type_id,
                    "TripMainTypeName": trip_main_type_name,
                    "Description": trip_main_type_name,
                    "HasAccess": True,
                },
                "Extended": {
                    "TripType": {
                        "TripTypeID": trip_type_id,
                        "TripTypeName": trip_type_name,
                        "Description": trip_type_name,
                    }
                },
            },
            "TripStatus": {"StatusID": status_id, "StatusName": "Active", "Default": True},
        }
        result = self._api_request("POST", "Trip", json_body=body)
        logger.info("create_trip: TripID=%s description=%r", result.get("TripID"), description)
        return result

    def create_booking(
        self,
        booking_number: str,
        tour_operator_id: int,
        tour_operator_name: str,
        trip_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        package_price: float = 0.0,
        personal_travel: bool = False,
    ) -> dict:
        """Create a new TESS booking.

        Required TESS POST /Booking shape (validated 2026-05-28):
          BookingNumber, TripID, TourOperator (ID + Name), Agent (full DTO),
          BookingCategoryType, BookingType, BookingStatus.

        Note: All existing bookings use BookingCategoryTypeID=1 "Regular Booking"
        regardless of booking type (cruise, hotel, etc.).
        """
        agent = self._build_agent_dto()

        # Seed from existing booking to get correct shape (PackagePrice, PersonalTravel, etc.)
        bookings = self._api_request("GET", "Booking", params={
            "pageNumber": 1, "pageSize": 1,
            "sortBy": "BookingDate", "sortAscending": "false",
        })
        items = bookings.get("Items", [])
        if not items:
            raise TESSWriteError("No existing bookings found to seed shape")
        template = copy.deepcopy(items[0])

        # Swap in new booking data
        template["BookingNumber"] = booking_number
        template["Agent"] = agent
        template["TourOperator"] = {
            "TourOperatorID": tour_operator_id,
            "TourOperatorName": tour_operator_name,
            "TourOperatorOwner": 2,
            "ContactCount": 0,
            "BookingCount": 0,
            "TotalPackagePrice": 0.0,
            "PrivateLinkCount": 0,
        }
        if trip_id is not None:
            template["TripID"] = trip_id
        if start_date:
            template["StartDate"] = start_date
        if end_date:
            template["EndDate"] = end_date
        if package_price:
            template["PackagePrice"] = package_price
        template["PersonalTravel"] = personal_travel

        # Remove read-only / auto-generated fields
        for k in ("BookingID", "TripMainTypeEnum", "TripDescription", "CreatedDateTimeUTC",
                   "Number", "ReceiptCount", "PaymentCount", "ReservationCount",
                   "Commission", "PaymentsAndItemizations", "ActualPackagePrice"):
            template.pop(k, None)

        result = self._api_request("POST", "Booking", json_body=template)
        logger.info(
            "create_booking: BookingID=%s number=%r tourOp=%s",
            result.get("BookingID"), booking_number, tour_operator_name,
        )
        return result

    def _get_agent_dto(self) -> dict:
        """Return the full Agent DTO (backward compat alias for _build_agent_dto)."""
        return self._build_agent_dto()

    def upsert_client(
        self,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Create or update a TESS client.

        TESS requires the full Agent DTO (UserID + Contact incl. $ProtectedEncrypted).
        Bare Agent.UserID.ID alone returns HTTP 400.
        """
        agent = self._build_agent_dto()
        contact = {
            "FirstName": first_name,
            "LastName": last_name,
            "ContactType": {"ID": 1},
        }
        contact.update(kwargs.pop("contact_extra", {}))
        body = {
            "Contact": contact,
            "Agent": agent,
            "ContactDetails": None,
        }
        body.update(kwargs)
        result = self._api_request(
            "POST",
            "Client",
            params={"updateAddress": "true", "updatePassport": "false"},
            json_body=body,
        )
        client_obj = result.get("Client", result)
        logger.info(
            "upsert_client: ClientID=%s name=%r %r",
            client_obj.get("ClientID", {}).get("ID"),
            first_name,
            last_name,
        )
        return client_obj

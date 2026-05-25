"""
TESSWriteClient — write operations for TESS CRM.
Extends TESSClient with Trip, Booking, and Client creation/update.

All writes go through _api_request() which handles auth and 401 retry.
PUT endpoints return 405 in TESS — use POST + action param for updates.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import from sibling module — same package
# sys.path is already set up for Thunderbird project
from core.booking.thunderbird_tess import TESSClient, TESSAuth

logger = logging.getLogger(__name__)


class TESSWriteError(Exception):
    pass


class TESSWriteClient(TESSClient):

    def create_trip(
        self,
        description: str,
        trip_main_type_id: int = 1,
        trip_main_type_name: str = "Regular Trip",
        status_id: int = 1,
    ) -> dict:
        """Create a new TESS trip. Returns full API response dict.

        Minimum viable body per live DTO mapping (09_write_dto_shapes.md):
          TripDescription, Agent.UserID.ID, Extended.TripMainType
        """
        user_id = self.auth._tokens.get("userID")
        body = {
            "TripDescription": description,
            "Agent": {"UserID": {"ID": user_id}},
            "Extended": {
                "TripMainType": {
                    "TripMainTypeID": trip_main_type_id,
                    "TripMainTypeName": trip_main_type_name,
                },
                "Extended": {},
            },
            "TripStatus": {"StatusID": status_id},
        }
        result = self._api_request("POST", "/Trip", json_body=body)
        logger.info("create_trip: TripID=%s description=%r", result.get("TripID"), description)
        return result

    def create_booking(
        self,
        booking_number: str,
        tour_operator_company_id: int,
        trip_id: Optional[int] = None,
        **kwargs,
    ) -> dict:
        """Create a new TESS booking.

        Required per DTO: BookingNumber, TourOperator.CompanyID.ID
        Optional: TripID to associate with an existing trip.
        Additional fields can be passed via **kwargs and are merged into body.
        """
        user_id = self.auth._tokens.get("userID")
        body = {
            "BookingNumber": booking_number,
            "TourOperator": {"CompanyID": {"ID": tour_operator_company_id}},
            "Agent": {"UserID": {"ID": user_id}},
        }
        if trip_id is not None:
            body["TripID"] = trip_id
        body.update(kwargs)
        result = self._api_request("POST", "/Booking", json_body=body)
        logger.info("create_booking: BookingID=%s number=%r", result.get("BookingID"), booking_number)
        return result

    def upsert_client(
        self,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Create or update a TESS client.

        TESS upsert endpoint: POST /Client?updateAddress=true&updatePassport=false
        Required per DTO: Contact.FirstName, Contact.LastName, Agent.UserID.ID
        """
        user_id = self.auth._tokens.get("userID")
        contact = {
            "FirstName": first_name,
            "LastName": last_name,
        }
        if email:
            contact["Email"] = email
        if phone:
            contact["Phone"] = phone
        contact.update(kwargs.pop("contact_extra", {}))
        body = {
            "Contact": contact,
            "Agent": {"UserID": {"ID": user_id}},
        }
        body.update(kwargs)
        result = self._api_request(
            "POST",
            "/Client",
            params={"updateAddress": "true", "updatePassport": "false"},
            json_body=body,
        )
        logger.info(
            "upsert_client: ClientID=%s name=%r %r",
            result.get("ClientID"),
            first_name,
            last_name,
        )
        return result

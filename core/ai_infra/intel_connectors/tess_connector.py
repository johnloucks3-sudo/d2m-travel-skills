"""
TESS CRM → intel_index connector.
Ingests trips, bookings, and clients from the live TESS REST API.
TTL: trips=4h, bookings=4h, clients=12h
"""
import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def ingest_tess(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.booking.thunderbird_tess import TESSClient

    client = TESSClient()
    base = "https://crm.myagentgenie.com/api/api/"

    # --- Trips ---
    t0 = time.monotonic()
    try:
        page, all_trips = 1, []
        while True:
            resp = client._api_request("GET", "Trip", params={
                "pageNumber": page, "pageSize": 50,
                "sortBy": "CreatedDateTimeUTC", "sortAscending": "false",
            })
            items = resp.get("Items", [])
            all_trips.extend(items)
            if len(items) < 50:
                break
            page += 1
        rows = [{
            "id": t.get("TripID"),
            "trip_id": t.get("TripID"),
            "description": t.get("TripDescription"),
            "status": t.get("TripStatus", {}).get("StatusName"),
            "start_date": t.get("Extended", {}).get("Extended", {}).get("StartDate"),
            "end_date": t.get("Extended", {}).get("Extended", {}).get("EndDate"),
            "booking_count": t.get("Extended", {}).get("Extended", {}).get("Detail", {}).get("BookingCount", 0),
            "traveler_count": t.get("Extended", {}).get("Extended", {}).get("Detail", {}).get("TravelerCount", 0),
            "package_price": t.get("Extended", {}).get("Extended", {}).get("Detail", {}).get("BookingPaymentAggregate", {}).get("PackagePrice", 0),
        } for t in all_trips]
        n = upsert_rows(con, "tess", "trips", rows, ttl, provenance=f"{base}Trip")
        log_run(con, "tess", "trips_refresh", rows_in=n, rows_out=n, elapsed=time.monotonic()-t0)
        logger.info("tess/trips: %d rows", n)
    except Exception as e:
        log_run(con, "tess", "trips_error", error=str(e), elapsed=time.monotonic()-t0)
        logger.error("tess/trips failed: %s", e)

    # --- Bookings ---
    t0 = time.monotonic()
    try:
        page, all_bk = 1, []
        while True:
            resp = client._api_request("GET", "Booking", params={
                "pageNumber": page, "pageSize": 50,
                "sortBy": "BookingDate", "sortAscending": "false",
            })
            items = resp.get("Items", [])
            all_bk.extend(items)
            if len(items) < 50:
                break
            page += 1
        rows = [{
            "id": b.get("BookingID"),
            "booking_id": b.get("BookingID"),
            "booking_number": b.get("BookingNumber"),
            "trip_id": b.get("TripID"),
            "trip_description": b.get("TripDescription"),
            "tour_operator": b.get("TourOperator", {}).get("TourOperatorName"),
            "tour_operator_id": b.get("TourOperator", {}).get("TourOperatorID"),
            "start_date": b.get("StartDate"),
            "end_date": b.get("EndDate"),
            "status": b.get("BookingStatus", {}).get("StatusName"),
            "package_price": b.get("PackagePrice", 0),
            "final_payment_date": b.get("FinalPaymentDate"),
            "commission_amount": b.get("Commission", {}).get("CommissionAmount", 0),
            "commission_received": b.get("Commission", {}).get("CommissionReceived", 0),
        } for b in all_bk]
        n = upsert_rows(con, "tess", "bookings", rows, ttl, provenance=f"{base}Booking")
        log_run(con, "tess", "bookings_refresh", rows_in=n, rows_out=n, elapsed=time.monotonic()-t0)
        logger.info("tess/bookings: %d rows", n)
    except Exception as e:
        log_run(con, "tess", "bookings_error", error=str(e), elapsed=time.monotonic()-t0)
        logger.error("tess/bookings failed: %s", e)

    # --- Clients ---
    t0 = time.monotonic()
    try:
        page, all_cl = 1, []
        while True:
            resp = client._api_request("GET", "Client", params={
                "pageNumber": page, "pageSize": 50,
                "sortBy": "LastName", "sortAscending": "true",
            })
            items = resp.get("Items", [])
            all_cl.extend(items)
            if len(items) < 50:
                break
            page += 1
        rows = [{
            "id": c.get("ClientID", {}).get("ID") or c.get("ClientID"),
            "client_id": c.get("ClientID", {}).get("ID") or c.get("ClientID"),
            "first_name": c.get("Contact", {}).get("FirstName"),
            "last_name": c.get("Contact", {}).get("LastName"),
            "email": (c.get("Contact", {}).get("EmailAddresses") or {}).get("Primary", {}).get("ContactDetailValue", {}).get("Value"),
            "booking_count": c.get("BookingCount", 0),
        } for c in all_cl]
        client_ttl = 12 * 3600
        n = upsert_rows(con, "tess", "clients", rows, client_ttl, provenance=f"{base}Client")
        log_run(con, "tess", "clients_refresh", rows_in=n, rows_out=n, elapsed=time.monotonic()-t0)
        logger.info("tess/clients: %d rows", n)
    except Exception as e:
        log_run(con, "tess", "clients_error", error=str(e), elapsed=time.monotonic()-t0)
        logger.error("tess/clients failed: %s", e)

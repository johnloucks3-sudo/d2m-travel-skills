#!/usr/bin/env python3
"""
TESS Web API — M-039
Flask wrapper over thunderbird_tess.py → /tess/trips, /tess/bookings, /tess/clients, /tess/health
Port 8901 | Internal only (Cloudflare tunnel not exposed by default)
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, jsonify, request
from core.booking.thunderbird_tess import TESSClient as TessClient

app = Flask(__name__)
_tess: TessClient | None = None
_tess_init_time: float = 0


def get_tess() -> TessClient:
    global _tess, _tess_init_time
    if _tess is None or (time.time() - _tess_init_time) > 300:
        _tess = TessClient()
        _tess_init_time = time.time()
    return _tess


def tess_response(data: dict) -> tuple:
    """Normalize TESS response — bubble up errors as 503, success as 200."""
    if "error" in data:
        err_type = data.get("type", "unknown")
        if err_type in ("auth_required", "auth_expired"):
            return jsonify({"error": data["error"], "type": err_type,
                            "fix": "python3 thunderbird_tess.py --authorize"}), 503
        return jsonify(data), 502
    return jsonify(data), 200


@app.route("/tess/health")
def health():
    t = get_tess()
    result = t._api_request("GET", "Trip", params={"pageNumber": 1, "pageSize": 1})
    if "error" in result:
        return jsonify({
            "status": "OFFLINE",
            "error": result["error"],
            "type": result.get("type"),
            "timestamp": datetime.now().isoformat(),
        }), 503
    return jsonify({
        "status": "ONLINE",
        "timestamp": datetime.now().isoformat(),
        "api_base": "crm.myagentgenie.com/api",
    })


@app.route("/tess/trips")
def trips():
    t = get_tess()
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 50))
    result = t.list_trips(page_number=page, page_size=min(size, 100))
    return tess_response(result)


@app.route("/tess/trips/<int:trip_id>")
def get_trip(trip_id: int):
    t = get_tess()
    result = t.get_trip(trip_id)
    return tess_response(result)


@app.route("/tess/bookings")
def bookings():
    t = get_tess()
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 50))
    filters = {}
    for f in ("bookingStatus", "tripID", "startDate", "endDate", "startDateEnd"):
        if request.args.get(f):
            filters[f] = request.args[f]
    result = t.list_bookings(page_number=page, page_size=min(size, 100), **filters)
    return tess_response(result)


@app.route("/tess/bookings/<int:booking_id>")
def get_booking(booking_id: int):
    t = get_tess()
    result = t.get_booking(booking_id)
    return tess_response(result)


@app.route("/tess/clients")
def clients():
    t = get_tess()
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 50))
    filters = {}
    for f in ("clientFirstName", "clientLastName", "emailAddress"):
        if request.args.get(f):
            filters[f] = request.args[f]
    result = t.list_clients(page_number=page, page_size=min(size, 100), **filters)
    return tess_response(result)


@app.route("/tess/clients/<int:client_id>")
def get_client(client_id: int):
    t = get_tess()
    result = t.get_client(client_id)
    return tess_response(result)


@app.route("/tess/checks")
def checks():
    t = get_tess()
    result = t.list_checks_received()
    return tess_response(result)


if __name__ == "__main__":
    print("TESS Web API starting on port 8904…")
    print("Endpoints: /tess/health /tess/trips /tess/bookings /tess/clients /tess/checks")
    app.run(host="127.0.0.1", port=8904, debug=False)

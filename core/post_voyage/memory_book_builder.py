"""
D2M Post-Voyage Memory Book Builder
=====================================

Collects a client's post-voyage photos, curates highlights, and generates a
branded PDF + interactive HTML memory book, with an optional print-on-demand
hand-off (Blurb / Shutterfly).

⚠️ PLATFORM CONSTRAINT — verified live against Google's own docs 2026-07-06,
read this before wiring to TP 5.1 ("shared Google Photos album link"):

Google removed the `photoslibrary.readonly` scope on 2025-03-31. As of that
date, `mediaItems.list`, `mediaItems.search`, and `albums.get`/`list` — the
exact tools `api/thunderbird_photos_mcp.py` exposes — return 403 for any
album or media item this app did not itself create. A client's own shared
album (the TP 5.1 use case) can no longer be read that way, no matter what
scope gets re-granted on our OAuth token. This was confirmed two ways this
session: (1) a live call to `albums.list` 403'd with SERVICE_DISABLED even
after the Photos Library API was enabled on the project, and (2) Google's
migration notes (developers.google.com/photos/support/updates) state plainly
that `photoslibrary.readonly` is removed and library-wide/shared-album reads
are restricted to the new Picker API.

Google's replacement — the Photos Picker API — requires the GUEST's own
OAuth consent and an interactive picker session *they* complete (open a
pickerUri, sign in, choose photos). It cannot run as a silent backend job.
`GooglePhotosPickerSource` below implements that flow correctly for when a
guest-consent UX exists, but calling it today will not collect anything
without the guest completing that step first.

**`DriveFolderSource` is the source that actually works end-to-end today**:
D2M's Drive OAuth (gmail_token.json) already has read access with no new
consent required. Ask the client to drop voyage photos into a shared Drive
folder (or upload on their guests' behalf from photos they text/email), and
this module curates and books from there. Recommend updating the TP 5.1
copy to ask for a Drive folder rather than promising automatic collection
from a Google Photos link — that promise cannot be honored under the
current API surface.

Everything downstream of `PhotoAsset` (curation, PDF/HTML rendering,
print-on-demand) is source-agnostic and works regardless of which
`PhotoSource` feeds it.

Usage:
    from core.post_voyage.memory_book_builder import build_memory_book, DriveFolderSource

    result = build_memory_book(
        booking_id="2984034",
        client_name="Erik McLeod & Melissa McGlasson",
        ship_name="Silver Muse",
        voyage_name="Mediterranean",
        voyage_dates="June 23 - July 6, 2026",
        source=DriveFolderSource(folder_id="<drive-folder-id>"),
    )
    print(result.pdf_path, result.digital_html_path, result.print_on_demand.order_url)
"""

from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "output" / "memory_books"
PRINT_CREDENTIALS_FILE = REPO_ROOT / "config" / "print_on_demand_credentials.json"

DEFAULT_TARGET_COUNT = 60
DEFAULT_MIN_RESOLUTION = 800 * 600      # drop low-res thumbnails / screenshots
DEFAULT_BURST_WINDOW_SECONDS = 90       # collapse burst shots taken within 90s of each other


# ── Photo model ──────────────────────────────────────────────────────────────

@dataclass
class PhotoAsset:
    """One photo, source-agnostic."""
    id: str
    filename: str
    creation_time: Optional[datetime]
    width: int
    height: int
    mime_type: str = "image/jpeg"
    download_url: str = ""                # HTTP(S) URL, fetched lazily by the source


class PhotoSource(Protocol):
    """Anything that can hand back a flat list of PhotoAsset for a voyage."""

    def collect(self) -> list[PhotoAsset]: ...

    def fetch_bytes(self, asset: PhotoAsset, max_width: int = 1600) -> bytes: ...


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Drive-folder source (works today — no new OAuth consent needed) ─────────

class DriveFolderSource:
    """Collects photos from a shared Drive folder guests/staff drop images into.

    Uses the already-authorized `get_drive()` service — this is the source
    that is actually exercisable end-to-end today (see module docstring).
    """

    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        self._service = None

    def _drive(self):
        if self._service is None:
            from api.thunderbird_google_auth import get_drive
            self._service = get_drive()
        return self._service

    def collect(self) -> list[PhotoAsset]:
        service = self._drive()
        assets: list[PhotoAsset] = []
        page_token = None
        while True:
            resp = (
                service.files()
                .list(
                    q=f"'{self.folder_id}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, imageMediaMetadata, createdTime)",
                    pageSize=200,
                    pageToken=page_token,
                )
                .execute()
            )
            for f in resp.get("files", []):
                mime = f.get("mimeType", "")
                if not mime.startswith("image/"):
                    continue
                meta = f.get("imageMediaMetadata") or {}
                assets.append(
                    PhotoAsset(
                        id=f["id"],
                        filename=f.get("name", f["id"]),
                        creation_time=_parse_iso(f.get("createdTime")),
                        width=int(meta.get("width") or 0),
                        height=int(meta.get("height") or 0),
                        mime_type=mime,
                    )
                )
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return assets

    def fetch_bytes(self, asset: PhotoAsset, max_width: int = 1600) -> bytes:
        from googleapiclient.http import MediaIoBaseDownload

        service = self._drive()
        request = service.files().get_media(fileId=asset.id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()


# ── Google Photos Picker source (correct replacement API; needs guest consent) ─

class GooglePhotosPickerSource:
    """Photos Picker API session — requires the GUEST's own OAuth token and an
    interactive picker session *they* complete. Not silently automatable from
    the backend. Included so the correct integration exists once a guest-facing
    consent UX is built; `collect()` raises until the guest has finished picking.
    """

    SESSIONS_URL = "https://photospicker.googleapis.com/v1/sessions"
    MEDIA_ITEMS_URL = "https://photospicker.googleapis.com/v1/mediaItems"

    def __init__(self, guest_access_token: str, session_id: Optional[str] = None):
        self.guest_access_token = guest_access_token
        self.session_id = session_id

    def create_session(self) -> dict:
        """Create a picker session. Returns dict with `pickerUri` — send that link
        to the guest; they must open it and pick photos before collect() works."""
        import requests

        resp = requests.post(
            self.SESSIONS_URL,
            headers={"Authorization": f"Bearer {self.guest_access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self.session_id = data.get("id")
        return data

    def poll_session(self) -> dict:
        import requests

        if not self.session_id:
            raise RuntimeError("No session_id — call create_session() first.")
        resp = requests.get(
            f"{self.SESSIONS_URL}/{self.session_id}",
            headers={"Authorization": f"Bearer {self.guest_access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def collect(self) -> list[PhotoAsset]:
        import requests

        session = self.poll_session()
        if not session.get("mediaItemsSet"):
            raise RuntimeError(
                "Guest has not finished picking photos yet in the Google Photos "
                "picker UI — poll again later, don't retry in a tight loop."
            )

        assets: list[PhotoAsset] = []
        page_token = None
        while True:
            params = {"sessionId": self.session_id, "pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(
                self.MEDIA_ITEMS_URL,
                headers={"Authorization": f"Bearer {self.guest_access_token}"},
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("mediaItems", []):
                mf = item.get("mediaFile", {}) or {}
                meta = mf.get("mediaFileMetadata", {}).get("photoMetadata", {}) if mf else {}
                assets.append(
                    PhotoAsset(
                        id=item.get("id"),
                        filename=mf.get("filename", item.get("id", "")),
                        creation_time=_parse_iso(item.get("createTime")),
                        width=int(meta.get("width") or 0),
                        height=int(meta.get("height") or 0),
                        mime_type=mf.get("mimeType", "image/jpeg"),
                        download_url=mf.get("baseUrl", ""),
                    )
                )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return assets

    def fetch_bytes(self, asset: PhotoAsset, max_width: int = 1600) -> bytes:
        import requests

        url = f"{asset.download_url}=w{max_width}"
        resp = requests.get(
            url, headers={"Authorization": f"Bearer {self.guest_access_token}"}, timeout=30
        )
        resp.raise_for_status()
        return resp.content


# ── Curation ─────────────────────────────────────────────────────────────────

@dataclass
class CurationResult:
    selected: list[PhotoAsset]
    dropped_low_res: int
    dropped_burst_duplicates: int


def curate_highlights(
    photos: list[PhotoAsset],
    target_count: int = DEFAULT_TARGET_COUNT,
    min_resolution: int = DEFAULT_MIN_RESOLUTION,
    burst_window_seconds: int = DEFAULT_BURST_WINDOW_SECONDS,
) -> CurationResult:
    """Heuristic curation over metadata only — no pixel/ML inspection.

    1. Drop anything below the resolution floor (screenshots, thumbnails, receipts).
    2. Collapse burst shots: consecutive photos within `burst_window_seconds`
       of each other are treated as one moment — keep the highest-resolution frame.
    3. Spread the remainder across the voyage timeline round-robin by day, so
       the book reads as a journey instead of a pile from one afternoon.
    4. Trim to `target_count`.
    """
    dropped_low_res = 0
    candidates: list[PhotoAsset] = []
    for p in photos:
        if p.width and p.height and (p.width * p.height) < min_resolution:
            dropped_low_res += 1
            continue
        candidates.append(p)

    candidates.sort(key=lambda p: p.creation_time or datetime.min)

    deduped: list[PhotoAsset] = []
    dropped_burst_duplicates = 0
    bucket: list[PhotoAsset] = []
    last_time: Optional[datetime] = None

    def flush(current_bucket: list[PhotoAsset]) -> int:
        if not current_bucket:
            return 0
        best = max(current_bucket, key=lambda p: p.width * p.height)
        deduped.append(best)
        return len(current_bucket) - 1

    for p in candidates:
        t = p.creation_time
        same_burst = (
            last_time is not None
            and t is not None
            and (t - last_time).total_seconds() <= burst_window_seconds
        )
        if same_burst:
            bucket.append(p)
        else:
            dropped_burst_duplicates += flush(bucket)
            bucket = [p]
        last_time = t
    dropped_burst_duplicates += flush(bucket)

    day_buckets: dict[str, list[PhotoAsset]] = {}
    for p in deduped:
        key = p.creation_time.date().isoformat() if p.creation_time else "undated"
        day_buckets.setdefault(key, []).append(p)

    day_keys = sorted(day_buckets.keys())
    day_queues = {k: sorted(v, key=lambda p: -(p.width * p.height)) for k, v in day_buckets.items()}

    selected: list[PhotoAsset] = []
    while len(selected) < target_count and any(day_queues.values()):
        for k in day_keys:
            if not day_queues[k]:
                continue
            selected.append(day_queues[k].pop(0))
            if len(selected) >= target_count:
                break

    return CurationResult(
        selected=selected,
        dropped_low_res=dropped_low_res,
        dropped_burst_duplicates=dropped_burst_duplicates,
    )


# ── PDF / HTML page assembly ─────────────────────────────────────────────────

def _build_pages(selected: list[PhotoAsset], source: PhotoSource):
    from templates.memory_book_schema import PhotoCaption, PhotoPage

    day_groups: dict[str, list[PhotoAsset]] = {}
    for p in selected:
        title = f"{p.creation_time:%A, %B} {p.creation_time.day}" if p.creation_time else "Onboard"
        day_groups.setdefault(title, []).append(p)

    pages = []
    for title, items in day_groups.items():
        captions = []
        for p in items:
            data = source.fetch_bytes(p)
            b64 = base64.b64encode(data).decode("utf-8")
            uri = f"data:{p.mime_type};base64,{b64}"
            caption = f"{p.creation_time:%b %-d, %-I:%M %p}" if p.creation_time else ""
            captions.append(PhotoCaption(data_uri=uri, caption=caption))
        pages.append(PhotoPage(section_title=title, photos=captions))
    return pages


# ── Print-on-demand (thin stub — no funded account exists) ──────────────────

@dataclass
class PrintOnDemandResult:
    provider: str
    order_url: str
    manual: bool
    note: str = ""


_MANUAL_ORDER_URLS = {
    "blurb": "https://www.blurb.com/create/photo-book",
    "shutterfly": "https://www.shutterfly.com/photo-books",
}


def request_print_on_demand(
    pdf_path: Path,
    provider: str = "blurb",
    credentials_path: Optional[Path] = None,
) -> PrintOnDemandResult:
    """Hand off the finished PDF for print-on-demand.

    No Blurb/Shutterfly account is provisioned or funded (that's a financial
    commitment — a Commander gate, not something to build speculatively). Per
    "don't design for hypothetical requirements": this stays a thin stub —
    absent credentials, it returns the manual upload flow instead of faking
    an API integration nothing can authenticate against. Once a provider is
    chosen and an account funded, add a real client here; every other piece
    of this module (curation, PDF, HTML) stays unchanged.
    """
    creds_file = credentials_path or PRINT_CREDENTIALS_FILE
    if creds_file.exists():
        creds = json.loads(creds_file.read_text())
        if provider in creds:
            raise NotImplementedError(
                f"{provider} credentials found in {creds_file} but no API client is "
                "wired up yet — this stub only implements the no-credentials manual path."
            )

    url = _MANUAL_ORDER_URLS.get(provider, _MANUAL_ORDER_URLS["blurb"])
    return PrintOnDemandResult(
        provider=provider,
        order_url=url,
        manual=True,
        note=f"No {provider} API credentials on file — upload {pdf_path.name} manually at the link above.",
    )


# ── Top-level orchestration ──────────────────────────────────────────────────

@dataclass
class MemoryBookResult:
    booking_id: str
    pdf_path: Path
    digital_html_path: Path
    photo_count: int
    curation_note: str
    print_on_demand: PrintOnDemandResult


def build_memory_book(
    booking_id: str,
    client_name: str,
    ship_name: str,
    voyage_name: str,
    voyage_dates: str,
    source: PhotoSource,
    target_count: int = DEFAULT_TARGET_COUNT,
    print_provider: str = "blurb",
    output_dir: Optional[Path] = None,
) -> MemoryBookResult:
    from templates.memory_book_schema import CoverMeta, MemoryBookContext, render_to_interactive_html, render_to_pdf

    out_dir = output_dir or OUTPUT_DIR

    photos = source.collect()
    curation = curate_highlights(photos, target_count=target_count)
    pages = _build_pages(curation.selected, source)

    ctx = MemoryBookContext(
        cover=CoverMeta(
            client_name=client_name,
            ship_name=ship_name,
            voyage_name=voyage_name,
            voyage_dates=voyage_dates,
            booking_id=booking_id,
        ),
        pages=pages,
    )

    pdf_path = render_to_pdf(ctx, out_dir / f"memory_book_{booking_id}.pdf")
    html_path = render_to_interactive_html(ctx, out_dir / f"memory_book_{booking_id}.html")
    print_result = request_print_on_demand(pdf_path, provider=print_provider)

    note = (
        f"Collected {len(photos)} photo(s), curated {len(curation.selected)} "
        f"(dropped {curation.dropped_low_res} low-res, collapsed "
        f"{curation.dropped_burst_duplicates} burst duplicate(s))."
    )

    return MemoryBookResult(
        booking_id=booking_id,
        pdf_path=pdf_path,
        digital_html_path=html_path,
        photo_count=len(curation.selected),
        curation_note=note,
        print_on_demand=print_result,
    )

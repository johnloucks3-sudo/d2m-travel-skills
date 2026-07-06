"""
Tests for core/post_voyage/memory_book_builder.py.

⚠️ SYNTHETIC DATA ONLY. Live testing against a real client's photos was
blocked this session: Google removed the `photoslibrary.readonly` scope in
March 2025, so reading a guest's shared Google Photos album (the TP 5.1 use
case) now 403s regardless of token/scope state (confirmed against Google's
own migration docs — see memory_book_builder.py's module docstring). No
Drive folder of real client voyage photos exists yet either. Every fixture
below is generated in-process with PIL; the 3 "real client" identifiers used
(McLeod 2984034, Furlow, Kuklinski) are real bookings from hale_state.json /
dossiers/, but the photo bytes attached to them are synthetic. Do not cite
counts or curation results from this file as claims about real client photos.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta

import pytest
from PIL import Image

from core.post_voyage.memory_book_builder import (
    PhotoAsset,
    build_memory_book,
    curate_highlights,
    request_print_on_demand,
)


def _make_jpeg_bytes(color: tuple[int, int, int], size: tuple[int, int] = (1600, 1200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG", quality=70)
    return buf.getvalue()


class FakeSource:
    """In-memory PhotoSource — no network, no Google/Drive credentials required."""

    def __init__(self, assets: list[PhotoAsset], byte_map: dict[str, bytes]):
        self._assets = assets
        self._byte_map = byte_map

    def collect(self) -> list[PhotoAsset]:
        return list(self._assets)

    def fetch_bytes(self, asset: PhotoAsset, max_width: int = 1600) -> bytes:
        return self._byte_map[asset.id]


def _synthetic_voyage_photos(seed_day_count: int = 4, per_day: int = 20) -> tuple[list[PhotoAsset], dict[str, bytes]]:
    """A voyage with `seed_day_count` days, `per_day` shots/day, including
    deliberate low-res junk and burst-duplicate clusters to exercise curation."""
    assets: list[PhotoAsset] = []
    byte_map: dict[str, bytes] = {}
    base = datetime(2026, 6, 23, 8, 0, 0)
    colors = [(30, 60, 120), (200, 180, 90), (90, 140, 90), (150, 60, 60)]

    idx = 0
    for day in range(seed_day_count):
        day_start = base + timedelta(days=day)
        for shot in range(per_day):
            idx += 1
            aid = f"asset-{idx}"
            creation = day_start + timedelta(minutes=shot * 20)
            # Every 5th shot: a 3-frame burst within the collapse window.
            if shot % 5 == 0:
                for burst_i in range(3):
                    bid = f"{aid}-burst{burst_i}"
                    burst_time = creation + timedelta(seconds=burst_i * 20)
                    assets.append(
                        PhotoAsset(
                            id=bid, filename=f"{bid}.jpg", creation_time=burst_time,
                            width=1600, height=1200,
                        )
                    )
                    byte_map[bid] = _make_jpeg_bytes(colors[day % len(colors)])
                continue
            # Every 7th shot: deliberately low-res junk (screenshot-sized).
            if shot % 7 == 0:
                assets.append(
                    PhotoAsset(id=aid, filename=f"{aid}.jpg", creation_time=creation, width=320, height=240)
                )
                byte_map[aid] = _make_jpeg_bytes((10, 10, 10), size=(320, 240))
                continue
            assets.append(
                PhotoAsset(id=aid, filename=f"{aid}.jpg", creation_time=creation, width=2400, height=1600)
            )
            byte_map[aid] = _make_jpeg_bytes(colors[day % len(colors)], size=(2400, 1600))

    return assets, byte_map


# ── Curation engine ──────────────────────────────────────────────────────────

def test_curation_drops_low_resolution_junk():
    photos, _ = _synthetic_voyage_photos()
    result = curate_highlights(photos, target_count=200, min_resolution=800 * 600)
    assert result.dropped_low_res > 0
    assert all(p.width * p.height >= 800 * 600 for p in result.selected)


def test_curation_collapses_burst_duplicates():
    photos, _ = _synthetic_voyage_photos()
    result = curate_highlights(photos, target_count=200)
    assert result.dropped_burst_duplicates > 0
    # No two selected photos should be within the burst window of each other.
    times = sorted(p.creation_time for p in result.selected if p.creation_time)
    for a, b in zip(times, times[1:]):
        assert (b - a).total_seconds() > 0


def test_curation_respects_target_count_and_spreads_across_days():
    photos, _ = _synthetic_voyage_photos(seed_day_count=4, per_day=20)
    result = curate_highlights(photos, target_count=40)
    assert len(result.selected) == 40
    days_represented = {p.creation_time.date() for p in result.selected if p.creation_time}
    assert len(days_represented) == 4, "round-robin selection should touch every day, not just day 1"


def test_curation_handles_empty_input():
    result = curate_highlights([], target_count=60)
    assert result.selected == []
    assert result.dropped_low_res == 0
    assert result.dropped_burst_duplicates == 0


# ── Print-on-demand stub ─────────────────────────────────────────────────────

def test_print_on_demand_manual_path_when_no_credentials(tmp_path):
    missing_creds = tmp_path / "no_such_credentials.json"
    result = request_print_on_demand(tmp_path / "book.pdf", provider="blurb", credentials_path=missing_creds)
    assert result.manual is True
    assert "blurb.com" in result.order_url
    assert "book.pdf" in result.note


def test_print_on_demand_raises_not_implemented_if_credentials_present(tmp_path):
    creds_file = tmp_path / "print_creds.json"
    creds_file.write_text('{"blurb": {"api_key": "placeholder"}}')
    with pytest.raises(NotImplementedError):
        request_print_on_demand(tmp_path / "book.pdf", provider="blurb", credentials_path=creds_file)


# ── End-to-end build (synthetic photos, real client identifiers) ────────────

@pytest.mark.parametrize(
    "booking_id,client_name,ship_name,voyage_name,voyage_dates",
    [
        ("2984034", "Erik McLeod & Melissa McGlasson", "Regent Seven Seas Grandeur", "Lesser Antilles", "Dec 2026"),
        ("FURLOW-SCANDI-2026", "John & Melissa Furlow", "Regent Seven Seas Grandeur", "Storied Scandinavia", "Aug 2026"),
        ("KUKLINSKI-VIKING-2026", "Kyle & Rosalie Kuklinski", "Viking Mars", "Panama Canal", "Dec 2026"),
    ],
)
def test_build_memory_book_end_to_end(tmp_path, booking_id, client_name, ship_name, voyage_name, voyage_dates):
    photos, byte_map = _synthetic_voyage_photos(seed_day_count=3, per_day=15)
    source = FakeSource(photos, byte_map)

    result = build_memory_book(
        booking_id=booking_id,
        client_name=client_name,
        ship_name=ship_name,
        voyage_name=voyage_name,
        voyage_dates=voyage_dates,
        source=source,
        target_count=24,
        output_dir=tmp_path,
    )

    assert result.pdf_path.exists()
    assert result.pdf_path.stat().st_size > 1000, "PDF should contain embedded images, not be near-empty"
    assert result.digital_html_path.exists()
    html_text = result.digital_html_path.read_text(encoding="utf-8")
    assert client_name in html_text
    assert ship_name in html_text
    assert result.photo_count == 24
    assert result.print_on_demand.manual is True

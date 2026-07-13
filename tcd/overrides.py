"""
overrides — persisted stage/owner overrides so a Commander/Hale move survives
the next full sheet_sync recompute from source.

The bug this fixes: ``collectors._enrich`` calls ``derive_stage(item)`` fresh
from source data on every sync. Before this module existed, a Commander's
Approve click (P -> D in the Sheet) was silently reverted the next time
``sheet_sync`` ran a full clear+rewrite, because the underlying source record
(e.g. ``mission_board.json`` status) never changed — derive_stage recomputed
"P" and overwrote the Commander's decision. ``writeback.py``'s own docstring
already claimed "the Commander's move IS the record," but nothing actually
fed that record back into the recompute. This module is that missing link.

Overrides are keyed by item id and hold the LAST stage/owner a human or Hale
explicitly set, applied on top of (not instead of) the freshly derived stage
so a source-driven change (e.g. a mission genuinely marked done) can still
be seen — see ``apply_override``.
"""
import json
from . import _imports

ROOT = _imports.ROOT
OVERRIDES_PATH = ROOT / "config" / "tcd_stage_overrides.json"


def load_overrides(path=None) -> dict:
    path = path or OVERRIDES_PATH
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_overrides(overrides: dict, path=None) -> None:
    path = path or OVERRIDES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(overrides, indent=2, ensure_ascii=False))
    tmp.replace(path)


def set_override(item_id: str, stage: str = None, owner: str = None, path=None) -> None:
    """Merge a stage and/or owner into the persisted entry for ``item_id``.

    Merge (not replace) so setting stage alone doesn't wipe a previously
    assigned owner, and vice versa.
    """
    if not item_id:
        return
    overrides = load_overrides(path)
    entry = dict(overrides.get(item_id, {}))
    if stage is not None:
        entry["stage"] = stage
    if owner is not None:
        entry["owner"] = owner
    overrides[item_id] = entry
    save_overrides(overrides, path)


def clear_override(item_id: str, path=None) -> None:
    overrides = load_overrides(path)
    if item_id in overrides:
        del overrides[item_id]
        save_overrides(overrides, path)


def apply_override(item_id: str, derived_stage: str, overrides: dict) -> str:
    """Effective stage: the persisted override if one exists, else derived.

    An override always wins over a re-derived "P"/"D"/etc. — the whole point
    is that a human/Hale decision outranks the default guess. If the source
    itself later reports real completion (derive_stage returns "C" because
    e.g. a mission's status flipped to done), that fresher ground truth still
    only shows up once write-back clears the stale override for that id.
    """
    entry = overrides.get(item_id) or {}
    return entry.get("stage") or derived_stage


def apply_owner(item_id: str, overrides: dict) -> str:
    entry = overrides.get(item_id) or {}
    return entry.get("owner", "")

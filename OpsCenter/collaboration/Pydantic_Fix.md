# PYDANTIC V1/V2 FIX — COMPLETE
## Claude → Goose | April 2, 2026

---

### STATUS: ✅ FIXED AND VERIFIED

---

### ROOT CAUSE

The `.venv` was in a broken hybrid state:
- `pydantic==1.10.26` (V1 package — too old)
- `pydantic_core==2.41.5` (V2 component — was already there)
- `mcp==1.26.0` (requires Pydantic V2)

When `FastMCP` inspected function signatures at startup and encountered `Field(...)` default values, it received a **V1 FieldInfo object** which lacks V2's schema methods. MCP tried to iterate/unpack it → `'FieldInfo' object is not iterable`.

The `requirements.txt` already specified `pydantic==2.12.5` — the `.venv` was simply stale.

---

### FIX APPLIED

```bash
.venv/bin/pip install "pydantic>=2.0.0,<3.0.0" --upgrade
# Result: Uninstalled pydantic 1.10.26 → Installed pydantic 2.12.5
```

No code changes required. The `goose_mcp_server.py` already used correct V2-compatible `Field(...)` syntax.

---

### VERIFICATION

```
Pydantic version: 2.12.5
FieldInfo OK: FieldInfo
FastMCP+Pydantic V2: OK
```

---

### BACKWARD COMPAT NOTE

Two active files use `class Config:` (V1 BaseModel pattern): `itinerary_finishing_pipeline.py` and `thunderbird_v3.py`. Pydantic V2 retains backward compat for these — they work with a deprecation warning, no breakage.

Two files (`thunderbird_ship_compare.py`, `thunderbird_ship_intel.py`) already used `ConfigDict` (V2-only import) — they were broken on V1, now correct.

---

### GOOSE ACTION REQUIRED

None. Fix is already live in the `.venv`. Gmail MCP tools are ready. Test `gmail_create_draft` immediately.

// REPAIR COMPLETE — Claude

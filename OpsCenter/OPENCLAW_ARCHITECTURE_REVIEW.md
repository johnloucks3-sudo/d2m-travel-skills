# OpenClaw Architectural Patterns for Thunderbird
**Architecture Review & Implementation Plan | 2026-05-03**

---

## EXECUTIVE SUMMARY

OpenClaw (11.8T tokens on OpenRouter) has 6 core patterns highly applicable to Thunderbird. We adapt the highest-leverage pattern (P0: Messaging-Based Skill Builder) into our existing Telegram C2 infrastructure without replacing D2M customizations.

---

## OPENCLAW CORE PATTERNS → THUNDERBIRD ADAPTATION

### Pattern 1: Messaging-Based Skill Builder (P0 — IMPLEMENT FIRST)

**OpenClaw Architecture:**
- User describes workflow in chat: "Check hotel prices and format as quote"
- Agent generates Python skill module, registers with MCP runtime, hot-reloads
- Skill becomes callable within the same conversation

**Thunderbird Adaptation:**
```
Commander → Telegram /build-skill "Check 5-star hotels in any city, return D2M pricing"
         ↓
Telegram C2 Bot (thunderbird_telegram_c2.py) receives command
         ↓
Brain 2 (Claude Sonnet) reads requirements, generates Python module
         ↓
Module written to /core/<domain>/<skill_name>.py
         ↓
MCP server (travel_mcp_server.py) hot-reloads function registry
         ↓
Skill callable within next Telegram command: @hotel_checker("Paris")
```

**Implementation Location:**
- Command handler: `core/communication/thunderbird_telegram_c2.py` (add `/build-skill` parser)
- Generator: `core/ai_infra/thunderbird_skill_builder.py` (new module)
- MCP integration: Existing `core/mcp/travel_mcp_server.py` (add dynamic registration)
- Storage: `core/<domain>/{skill_name}.py` (generated modules live alongside existing code)

**Key Design Decisions:**
1. **No subprocess overhead** — Skills are pure Python functions, imported directly
2. **MCP function registry** — Tools list updates dynamically on reload
3. **Type safety** — Generated skills include type hints, parameter validation
4. **Audit trail** — Generated skill stored with metadata (timestamp, generator prompt, Commander ID)
5. **Scope boundary** — Skills cannot execute client-facing sends (WF-17 gate stays)

---

### Pattern 2: Persistent Memory System (P1 — DEFER)

**Why defer:** Thunderbird already has `hale_memory.md` + dossier system + wing comms. Vector embedding adds cost/complexity without clearing ROI against existing pattern.

**When to revisit:** If semantic recall needs ("What did we learn from Lyons?") become frequent and grep/human search insufficient.

---

### Pattern 3: Proactive Heartbeat Assessments (P2 — DEFER)

**Why defer:** COS already runs proactive scans. Heartbeat cron adds redundancy unless it brings new signals.

**When to revisit:** If Commander asks for autonomous opportunity detection beyond current status sweeps.

---

### Pattern 4: Hot-Reloadable Configurations (P3 — DEPENDS ON P0)

**Relationship:** P0 (skill builder) *requires* hot-reload to make new skills immediately available. If we build P0, hot-reload is necessary.

**Implementation:** File watcher on `core/ai_infra/thunderbird_model_dispatcher.py` and config files. Python `importlib.reload()` on MCP function registry.

---

### Pattern 5: Multi-Agent Spawn from Chat (P4 — DEFER)

**Why defer:** OpenCode already spawns. This pattern is useful for parallel research (e.g., "spawn 5 agents to compare 5 cruise lines"). Low urgency vs. P0.

---

### Pattern 6: OAuth Self-Provisioning (P5 — DEFER)

**Why defer:** We have standing timers for token refresh. Self-healing OAuth adds complexity for rare failures.

**When to revisit:** If token management becomes failure-prone.

---

## P0 IMPLEMENTATION PLAN — MESSAGING-BASED SKILL BUILDER

### Architecture Diagram

```
Commander Telegram (C2 Bot)
    │
    ├─ /build-skill "Hotel checker: take city name, return prices formatted as D2M quote"
    │
    ↓
thunderbird_skill_builder.py (Sonnet 4.6)
    │
    ├─ Parse requirement from Commander message
    ├─ Generate Python skill code (function + type hints + validation)
    ├─ Generate docstring + usage example
    ├─ Generate unit tests
    │
    ↓
core/<domain>/<skill_name>.py (written to disk)
    │
    ├─ Python function (e.g., check_hotel_prices_d2m)
    ├─ Metadata YAML (created_ts, generator_prompt, version)
    ├─ Unit tests (test_<skill_name>.py)
    │
    ↓
travel_mcp_server.py (hot-reload)
    │
    ├─ Detect new .py file in core/
    ├─ Import module, extract function signature
    ├─ Register function with MCP tools list
    │
    ↓
Next Telegram command can call: /invoke hotel_checker city="Paris"
    │
    ↓
Response returned to Commander (no client send without approval)
```

### File Locations & Dependencies

| Component | File | Purpose |
|-----------|------|---------|
| **Skill Builder** | `core/ai_infra/thunderbird_skill_builder.py` (NEW) | Sonnet→Python code generator |
| **Telegram Parser** | `core/communication/thunderbird_telegram_c2.py` (MODIFY) | Add `/build-skill` command handler |
| **MCP Integration** | `core/mcp/travel_mcp_server.py` (MODIFY) | Hot-reload function registry |
| **Skill Storage** | `core/<domain>/<skill_name>.py` (GENERATED) | Generated skill functions live here |
| **Test Suite** | `tests/test_skill_builder.py` (NEW) | Verify generated code quality |
| **Config** | `core/ai_infra/skill_builder_config.py` (NEW) | Skill categories, templates, constraints |

### Core Algorithm (Skill Builder)

```python
def build_skill_from_description(requirement: str, commander_id: str) -> SkillGenerationResult:
    """
    1. Parse Commander's natural language requirement
    2. Classify domain (travel, finance, ops, client-facing)
    3. Check if already exists (avoid duplication)
    4. Generate Python function + tests
    5. Write to disk + register with MCP
    6. Return SkillGenerationResult with invocation example
    """
    # Step 1: Extract intent
    intent = classify_requirement(requirement)  # "hotel_checker", "price_monitor", etc.
    
    # Step 2: Validate scope (no client sends without approval)
    if intent.requires_external_send:
        raise SkillConstraintError("Skills cannot trigger client-facing sends. Use WF-17 gate.")
    
    # Step 3: Generate code via Sonnet
    prompt = f"""
    Generate a Python skill function for: {requirement}
    
    Requirements:
    - Function name: {intent.skill_name}
    - Input parameters with type hints
    - Return type: Union[dict, str, list]
    - Docstring with usage example
    - Input validation
    - Error handling (try/except, return error dict)
    - No external subprocess calls
    
    Output format:
    ```python
    def {intent.skill_name}(...) -> ...:
        \"\"\"Docstring\"\"\"
        ...
    ```
    """
    
    skill_code = claude_sonnet(prompt)
    
    # Step 4: Write to disk
    skill_file = Path(f"core/{intent.domain}/{intent.skill_name}.py")
    skill_file.write_text(skill_code)
    
    # Step 5: Generate tests
    test_code = generate_test_suite(skill_code, intent)
    test_file = Path(f"tests/test_{intent.skill_name}.py")
    test_file.write_text(test_code)
    
    # Step 6: Register with MCP
    mcp_server.reload_function_registry()
    
    return SkillGenerationResult(
        skill_name=intent.skill_name,
        file_path=skill_file,
        invocation_example=f"@{intent.skill_name}(...)",
        test_file=test_file,
        metadata={
            "created": datetime.now().isoformat(),
            "commander_id": commander_id,
            "generator_prompt": requirement,
            "domain": intent.domain
        }
    )
```

### Safety Constraints

1. **No client sends** — Skills cannot call `gmail_send_email`, `send_sms`, etc. without explicit WF-17 gate
2. **No subprocess spawning** — Skills cannot shell out to unknown commands
3. **No credential access** — Skills cannot read OAuth tokens, API keys directly
4. **Type validation** — Generated code includes input parameter validation
5. **Audit trail** — Every generated skill includes metadata (creator, timestamp, source prompt)

---

## P0 INTEGRATION WITH EXISTING THUNDERBIRD

### Telegram Command Flow

```
/build-skill "Check Silversea current occupancy rates by cabin type"
    ↓
thunderbird_telegram_c2.py regex: r'^/build-skill (.+)$'
    ↓
dispatch_skill_builder(requirement="Check Silversea...", commander_id=7554895206)
    ↓
brain_dispatch.py classifies as "SONNET" (creative code generation task)
    ↓
thunderbird_skill_builder.py runs Sonnet, generates Python function
    ↓
Function written to core/travel/check_silversea_occupancy.py
    ↓
MCP server reloads tools list
    ↓
Telegram response: "✅ Skill created. Usage: /invoke check_silversea_occupancy"
    ↓
Next command: /invoke check_silversea_occupancy cabin_type="Ocean View"
    ↓
MCP server calls generated function, returns result to Telegram
```

### Model Routing

- **Skill generation:** Claude Sonnet 4.6 (creative, code generation)
- **Requirement classification:** DeepSeek V3.1 (fast pattern matching)
- **Test generation:** Claude Sonnet 4.6 (thorough coverage)
- **Code execution:** Python interpreter (skill_builder_executor.py)

### Cost & Performance

| Operation | Model | Cost | Latency | Notes |
|-----------|-------|------|---------|-------|
| Generate skill | Sonnet | ~$0.015-0.05 | 8-15 sec | Includes code + tests + docs |
| Classify requirement | DeepSeek | ~$0.0001 | <1 sec | Fast intent matching |
| Register with MCP | N/A | $0 | <0.5 sec | In-process Python reload |
| Execute skill | N/A | $0 | <2 sec | Pure Python, no external calls |

---

## TEST STRATEGY FOR P0

### Unit Tests

```python
def test_build_skill_hotel_checker():
    """Skill builder generates valid Python for hotel price checker"""
    requirement = "Check 5-star hotels in a city, format as D2M quote"
    result = build_skill_from_description(requirement, "7554895206")
    
    # Verify file created
    assert result.skill_file.exists()
    
    # Verify syntax valid
    compile(result.skill_file.read_text(), result.skill_file, 'exec')
    
    # Verify function callable
    skill_module = import_generated_skill(result.skill_file)
    assert callable(skill_module.check_hotels_d2m)
    
    # Verify MCP registration
    mcp_tools = travel_mcp_server.list_tools()
    assert "check_hotels_d2m" in [t.name for t in mcp_tools]

def test_skill_type_validation():
    """Generated skill validates input types"""
    skill = import_generated_skill("core/travel/check_hotels_d2m.py")
    
    # Valid call
    result = skill.check_hotels_d2m(city="Paris", star_rating=5)
    assert isinstance(result, dict)
    
    # Invalid type → should return error dict (not crash)
    result = skill.check_hotels_d2m(city=12345, star_rating="five")
    assert "error" in result or isinstance(result, dict)

def test_skill_no_client_send():
    """Skill builder rejects requirements that would trigger client sends"""
    requirement = "Send a follow-up email to all clients without bookings"
    
    with pytest.raises(SkillConstraintError):
        build_skill_from_description(requirement, "7554895206")

def test_skill_hot_reload():
    """MCP server detects new skill file and hot-reloads"""
    # Create new skill file manually
    new_skill_file = Path("core/ops/test_skill.py")
    new_skill_file.write_text("def test_skill(): return 'OK'")
    
    # Trigger reload
    travel_mcp_server.reload_function_registry()
    
    # Verify in tools list
    tools = travel_mcp_server.list_tools()
    assert "test_skill" in [t.name for t in tools]
    
    # Cleanup
    new_skill_file.unlink()
```

### Integration Tests

1. **End-to-end Telegram command** → Skill builder → MCP registration → Invocation
2. **Skill invocation via `/invoke` command** with various parameter types
3. **Error handling** (malformed requirement, duplicate skill name, constraint violation)
4. **Code quality** (generated code passes linting, type checking)

---

## IMPLEMENTATION SEQUENCE FOR P0

### Phase 1 (This session): Core Infrastructure
1. [ ] Write `core/ai_infra/thunderbird_skill_builder.py` (generator + logic)
2. [ ] Write `core/ai_infra/skill_builder_config.py` (constraints, templates)
3. [ ] Modify `core/communication/thunderbird_telegram_c2.py` (add `/build-skill` handler)

### Phase 2: MCP Integration
4. [ ] Modify `core/mcp/travel_mcp_server.py` (hot-reload function registry)
5. [ ] Verify skill functions appear in MCP tools list after generation

### Phase 3: Testing & Validation
6. [ ] Write `tests/test_skill_builder.py` (unit + integration tests)
7. [ ] Run full test suite, verify all 5 test scenarios PASS
8. [ ] Manual Telegram test: `/build-skill "simple test skill"`

### Phase 4: Documentation & Deployment
9. [ ] Update `docs/AGENTS.md` with `/build-skill` documentation
10. [ ] Deploy to prod, monitor first 10 skills generated
11. [ ] Report progress to `claude_outbox.md`

---

## DELIVERABLES (P0 ONLY)

✅ This document (architecture spec)  
⏳ `core/ai_infra/thunderbird_skill_builder.py` (implementation)  
⏳ `core/ai_infra/skill_builder_config.py` (constraints + templates)  
⏳ Modified `core/communication/thunderbird_telegram_c2.py` (Telegram handler)  
⏳ Modified `core/mcp/travel_mcp_server.py` (MCP hot-reload)  
⏳ `tests/test_skill_builder.py` (test suite)  
⏳ Updated `docs/AGENTS.md`  

---

## NEXT STEPS

Proceed to P0 implementation. All code follows Thunderbird conventions:
- Flat imports + PYTHONPATH via `mcp_launcher_core.sh`
- Systemd timer-compatible (no blocking I/O)
- Client sends blocked at WF-17 gate
- All outputs via Commander approval until skill matures

---

*Architecture review complete. Ready to implement P0. — COS Hale, 2026-05-03*

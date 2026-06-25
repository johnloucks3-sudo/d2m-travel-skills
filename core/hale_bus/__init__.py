"""
HALE BUS — Inter-Hale Communication & State Handoff

Allows all 8 Hale instances to share operational state via JSON.
- Mandatory read at session startup
- Automatic write at session end
- Shared file: hale_bus_state.json

Usage:
  from core.hale_bus import read_bus, write_bus, startup_brief

  # At session startup (MANDATORY)
  from core.hale_bus.hale_bus_read import load_bus_at_startup
  load_bus_at_startup("claude_code")

  # At session end
  from core.hale_bus.hale_bus_write import checkpoint_session
  checkpoint_session("claude_code")
"""

__version__ = "1.0"
__author__ = "Hale / Thunderbird Wing"

from .hale_bus_read import (
    read_bus_state,
    get_other_instances_state,
    get_critical_directives,
    get_fpd_alerts,
    get_handoff_queue,
    startup_brief,
    load_bus_at_startup,
)
from .hale_bus_write import (
    read_hale_state,
    write_bus_state,
    checkpoint_session,
)

__all__ = [
    "read_bus_state",
    "get_other_instances_state",
    "get_critical_directives",
    "get_fpd_alerts",
    "get_handoff_queue",
    "startup_brief",
    "load_bus_at_startup",
    "read_hale_state",
    "write_bus_state",
    "checkpoint_session",
]

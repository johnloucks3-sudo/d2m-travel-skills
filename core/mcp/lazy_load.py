"""Lazy-load wrapper for heavy MCP tool modules.

Defers initialization of memory-intensive modules until first use.
Breaks accumulation pattern across systemd restarts.
"""

import logging
from typing import Callable, Dict, Tuple

logger = logging.getLogger(__name__)

# Registry: module_name -> (is_loaded, register_func)
_registry: Dict[str, Tuple[bool, Callable]] = {}


def lazy_register(module_name: str, register_func: Callable) -> None:
    """Register a tool module's factory without calling it immediately.

    Args:
        module_name: Unique identifier (e.g., "gmail", "centrav_flights")
        register_func: Function that takes (mcp) and registers tools
    """
    _registry[module_name] = (False, register_func)


def ensure_loaded(module_name: str, mcp) -> bool:
    """Trigger lazy registration on first tool call.

    Args:
        module_name: Identifier from lazy_register()
        mcp: FastMCP instance to register tools into

    Returns:
        True if loaded (either just-loaded or already-loaded), False if error/unknown
    """
    if module_name not in _registry:
        logger.warning(f"ensure_loaded({module_name}): not registered")
        return False

    is_loaded, register_func = _registry[module_name]

    if is_loaded:
        # Already loaded; no-op
        return True

    # First call to this module; load it
    try:
        logger.info(f"Lazy-loading tool module: {module_name}")
        register_func(mcp)
        _registry[module_name] = (True, register_func)
        logger.info(f"  ✓ {module_name} registered ({len(getattr(mcp, 'tools', []))} tools total)")
        return True
    except Exception as e:
        logger.error(f"  ✗ {module_name} failed to load: {e}", exc_info=True)
        return False


def get_registry_status() -> Dict[str, bool]:
    """Return loaded status of all registered modules."""
    return {name: is_loaded for name, (is_loaded, _) in _registry.items()}

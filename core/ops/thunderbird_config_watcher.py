"""
Thunderbird Config Watcher — OpenClaw P3 Pattern Adaptation
Hot-reloadable configurations without restarting services.

Watches: model_dispatcher config, keyword_router patterns, skill registry
Mechanism: inotify (watchdog) → detect change → reload in-memory state
"""

import os
import json
import time
import logging
import importlib
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try watchdog; fall back to polling if unavailable
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    _HAS_WATCHDOG = True
except ImportError:
    _HAS_WATCHDOG = False


# ============================================================================
# CONFIG REGISTRY
# ============================================================================

@dataclass
class ReloadableModule:
    """A module that supports hot-reload"""
    name: str
    config_path: Path
    reload_fn: Optional[Callable] = None
    last_mtime: float = 0.0
    last_reload: float = 0.0
    reload_count: int = 0
    error_count: int = 0


class ConfigRegistry:
    """Registry of reloadable configuration modules"""

    def __init__(self, thunderbird_root: Optional[Path] = None):
        self.thunderbird_root = thunderbird_root or Path.home() / "Thunderbird"
        self._modules: Dict[str, ReloadableModule] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, Path], None]] = []
        self._register_defaults()

    def _register_defaults(self):
        """Register default Thunderbird config files"""
        defaults = [
            ("keyword_router", self.thunderbird_root / "OpsCenter" / "keyword_router.py"),
            ("model_dispatcher", self.thunderbird_root / "agents" / "thunderbird_model_dispatcher.py"),
            ("skill_builder_config", self.thunderbird_root / "core" / "ai_infra" / "skill_builder_config.py"),
            ("poe_config", self.thunderbird_root / "config" / "poe.env"),
            ("persona_registry", self.thunderbird_root / "Personas" / "ROSTER.md"),
        ]
        for name, path in defaults:
            if path.exists():
                self.register(name, path)

    def register(self, name: str, config_path: Path,
                 reload_fn: Optional[Callable] = None):
        """Register a reloadable config file"""
        with self._lock:
            mtime = config_path.stat().st_mtime if config_path.exists() else 0.0
            self._modules[name] = ReloadableModule(
                name=name,
                config_path=config_path,
                reload_fn=reload_fn,
                last_mtime=mtime,
                last_reload=time.time(),
            )
            logger.info(f"Registered config: {name} ({config_path})")

    def unregister(self, name: str):
        """Remove a config from the registry"""
        with self._lock:
            self._modules.pop(name, None)

    def get_module(self, name: str) -> Optional[ReloadableModule]:
        """Get a registered module"""
        return self._modules.get(name)

    def list_modules(self) -> Dict[str, Dict[str, Any]]:
        """List all registered modules with status"""
        with self._lock:
            result = {}
            for name, mod in self._modules.items():
                result[name] = {
                    "config_path": str(mod.config_path),
                    "last_mtime": mod.last_mtime,
                    "last_reload": mod.last_reload,
                    "reload_count": mod.reload_count,
                    "error_count": mod.error_count,
                    "exists": mod.config_path.exists(),
                }
            return result

    def on_reload(self, callback: Callable[[str, Path], None]):
        """Register a callback for config reload events"""
        self._callbacks.append(callback)

    def reload_module(self, name: str) -> bool:
        """Hot-reload a specific module"""
        with self._lock:
            mod = self._modules.get(name)
            if not mod:
                logger.warning(f"Module not registered: {name}")
                return False

            if not mod.config_path.exists():
                logger.warning(f"Config file missing: {mod.config_path}")
                return False

        try:
            # Execute custom reload function if provided
            if mod.reload_fn:
                mod.reload_fn()
            else:
                # Default: re-import the module
                self._reload_python_module(mod)

            # Update state
            with self._lock:
                mod.last_mtime = mod.config_path.stat().st_mtime
                mod.last_reload = time.time()
                mod.reload_count += 1

            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb(name, mod.config_path)
                except Exception as e:
                    logger.warning(f"Reload callback failed for {name}: {e}")

            logger.info(f"Hot-reloaded config: {name} (reload #{mod.reload_count})")
            return True

        except Exception as e:
            logger.error(f"Hot-reload failed for {name}: {e}")
            with self._lock:
                mod.error_count += 1
            return False

    def _reload_python_module(self, mod: ReloadableModule):
        """Reload a Python module by path"""
        module_name = mod.config_path.stem
        if module_name in importlib.sys.modules:
            importlib.reload(importlib.sys.modules[module_name])
            logger.info(f"Reloaded Python module: {module_name}")
        else:
            # Add parent dir to path and import
            parent = str(mod.config_path.parent)
            if parent not in importlib.sys.path:
                importlib.sys.path.insert(0, parent)
            importlib.import_module(module_name)
            logger.info(f"Imported Python module: {module_name}")

    def reload_all(self) -> Dict[str, bool]:
        """Hot-reload all registered modules"""
        results = {}
        for name in list(self._modules.keys()):
            results[name] = self.reload_module(name)
        return results


# ============================================================================
# FILE WATCHER
# ============================================================================

class ConfigFileHandler:
    """Watchdog event handler for config file changes"""

    def __init__(self, registry: ConfigRegistry):
        self.registry = registry
        self._debounce: Dict[str, float] = {}
        self._debounce_delay = 1.0  # seconds

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Only process FileModifiedEvent
        if not hasattr(event, 'src_path'):
            return

        path = Path(event.src_path)
        
        # Check if this path is registered
        for name, mod in self.registry._modules.items():
            if mod.config_path.resolve() == path.resolve():
                now = time.time()
                last = self._debounce.get(name, 0)
                if now - last < self._debounce_delay:
                    return  # Debounce rapid changes
                
                self._debounce[name] = now
                logger.info(f"Config change detected: {name} ({path.name})")
                
                # Reload in background thread
                threading.Thread(
                    target=self.registry.reload_module,
                    args=(name,),
                    daemon=True,
                ).start()
                break


class ConfigWatcher:
    """Main config watcher: monitors files and triggers hot-reloads"""

    def __init__(self, registry: Optional[ConfigRegistry] = None,
                 thunderbird_root: Optional[Path] = None):
        self.registry = registry or ConfigRegistry(thunderbird_root)
        self._observer = None
        self._poll_thread = None
        self._running = False
        self._poll_interval = 5.0  # seconds (fallback mode)

    def start(self, use_watchdog: bool = True):
        """Start watching config files"""
        self._running = True
        
        if use_watchdog and _HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()
        
        logger.info(f"Config watcher started (mode={'watchdog' if _HAS_WATCHDOG else 'polling'})")

    def stop(self):
        """Stop watching"""
        self._running = False
        
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
            self._poll_thread = None
        
        logger.info("Config watcher stopped")

    def _start_watchdog(self):
        """Start watchdog-based file watching"""
        handler = ConfigFileHandler(self.registry)
        self._observer = Observer()
        
        # Watch all directories containing registered configs
        watched_dirs = set()
        for mod in self.registry._modules.values():
            watched_dirs.add(str(mod.config_path.parent))
        
        for dir_path in watched_dirs:
            self._observer.schedule(handler, dir_path, recursive=False)
            logger.info(f"Watching directory: {dir_path}")
        
        self._observer.start()

    def _start_polling(self):
        """Start polling-based file watching (fallback)"""
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True
        )
        self._poll_thread.start()

    def _poll_loop(self):
        """Polling loop for file changes"""
        while self._running:
            for name, mod in self.registry._modules.items():
                if not mod.config_path.exists():
                    continue
                
                current_mtime = mod.config_path.stat().st_mtime
                if current_mtime > mod.last_mtime:
                    logger.info(f"Poll detected change: {name}")
                    self.registry.reload_module(name)
            
            time.sleep(self._poll_interval)


# ============================================================================
# PUBLIC API
# ============================================================================

def create_watcher(thunderbird_root: Optional[Path] = None) -> ConfigWatcher:
    """Create a config watcher with default Thunderbird configs"""
    registry = ConfigRegistry(thunderbird_root)
    return ConfigWatcher(registry)


def hot_reload_config(name: str, thunderbird_root: Optional[Path] = None) -> bool:
    """Hot-reload a specific config by name"""
    registry = ConfigRegistry(thunderbird_root)
    return registry.reload_module(name)


def list_configs(thunderbird_root: Optional[Path] = None) -> Dict[str, Any]:
    """List all registered configs and their status"""
    registry = ConfigRegistry(thunderbird_root)
    return registry.list_modules()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Config Watcher — OpenClaw P3")
    print("=" * 40)
    
    # List registered configs
    configs = list_configs()
    print(f"Registered configs: {len(configs)}")
    for name, info in configs.items():
        status = "✅" if info["exists"] else "❌"
        print(f"  {status} {name}: {info['config_path']}")
    
    # Test hot-reload
    print("\nTesting hot-reload...")
    result = hot_reload_config("keyword_router")
    print(f"keyword_router reload: {'success' if result else 'failed'}")

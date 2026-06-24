# Shim — re-exports from core.comms.wing_page
# CI scripts import OpsCenter.wing_page; real module lives at core.comms.wing_page
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.comms.wing_page import *  # noqa: F401,F403
try:
    from core.comms.wing_page import page  # noqa: F401
except ImportError:
    # page() shim for scripts that use the old function-style API
    from core.comms.wing_page import send_page as page  # noqa: F401

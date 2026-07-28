import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.intel.thunderbird_twitter_osint import run_twitter_osint_sweep

print(run_twitter_osint_sweep())

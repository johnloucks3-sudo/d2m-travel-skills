#!/usr/bin/env python3
"""
silver_gate.py — CLI shim onto core/silver/gate.py (the real gate module).

Usage:
  python3 scripts/silver_gate.py <work_product> --criteria "..." [--mission ID]
                                 [--others name1,name2] [--dossier path]
  python3 scripts/silver_gate.py --internal-ops
"""
import sys
sys.path.insert(0, "/home/john/Thunderbird")

from core.silver.gate import run_gate, internal_ops_verdict, print_verdict


def _flag(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


if __name__ == "__main__":
    if "--internal-ops" in sys.argv:
        sys.exit(print_verdict(internal_ops_verdict()))
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    others = (_flag("--others") or "").split(",") if "--others" in sys.argv else []
    v = run_gate(
        sys.argv[1],
        _flag("--criteria", ""),
        mission_id=_flag("--mission", "ADHOC"),
        others=[o for o in others if o],
        dossier=_flag("--dossier"),
    )
    sys.exit(print_verdict(v))

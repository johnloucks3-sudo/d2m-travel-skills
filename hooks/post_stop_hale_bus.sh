#!/bin/bash
# Stop hook — checkpoint HALE BUS state at session end
# Part of HALE BUS CI (SO-2026-06-24): Enable inter-Hale communication via JSON handoff
#
# This hook ensures that when a Hale session ends, its current state is written to the
# shared HALE BUS state file so other instances can read it at startup.

cd /home/john/Thunderbird

INSTANCE_TYPE="${HALE_INSTANCE:-claude_code}"

echo "⚡ HALE BUS checkpoint: saving $INSTANCE_TYPE session state..."

python3 -c "
import os
os.chdir('/home/john/Thunderbird')
from core.hale_bus.hale_bus_write import checkpoint_session

instance = os.getenv('HALE_INSTANCE', 'claude_code')
checkpoint_session(instance)
print('✅ HALE BUS checkpointed for:', instance)
" 2>/dev/null || echo "⚠️  HALE BUS checkpoint failed (non-critical)"

# Continue with other stop hooks

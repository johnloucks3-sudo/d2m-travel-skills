#!/bin/bash
# Fix Thunderbird daemon memory limits on YOGA
# Run on YOGA: ssh yoga bash /home/john/Thunderbird/scripts/fix_memory_ceilings.sh
#
# ⚠️ LAYOUT IS LOAD-BEARING (A7 Sterling, 2026-07-16). Per-service limits MUST go in
# per-unit dirs ~/.config/systemd/user/<unit>.service.d/override.conf, NOT in the shared
# top-level service.d/. A bare service.d/ is systemd's "drop-in for a unit TYPE" that
# applies to EVERY .service; systemd merges all drop-ins by basename across dirs and the
# lexically-last one wins for MemoryMax (per-unit dirs get NO precedence — verified live).
# The prior version of this script wrote everything into service.d/, so
# thunderbird-default-memory.conf (sorts last) silently capped qdrant/opencode/etc. to 1G
# — the fleet-wide OOM root cause. The ONLY thing that belongs in service.d/ is the
# 00-prefixed default (sorts FIRST = base layer that per-unit overrides beat).

set -e

echo "🔧 Applying memory ceilings to Thunderbird daemons (per-unit layout)..."

USER_UNIT_DIR="$HOME/.config/systemd/user"
SHARED_DIR="$USER_UNIT_DIR/service.d"
mkdir -p "$SHARED_DIR"

# ----------------------------------------------------------------------------
# 0. Remove legacy shared-dir confs from the old (broken) layout, if present.
#    These applied to every unit and clobbered per-service limits.
# ----------------------------------------------------------------------------
for legacy in opencode-spsa-monitor-memory qdrant-memory \
              d2m-gmail-agentmail-bridge-memory hale-credential-check-memory \
              thunderbird-default-memory; do
    rm -f "$SHARED_DIR/${legacy}.conf"
done

# write_override <unit> <MemoryMax> <MemoryHigh>
write_override() {
    local unit="$1" max="$2" high="$3"
    local dir="$USER_UNIT_DIR/${unit}.service.d"
    mkdir -p "$dir"
    cat > "$dir/override.conf" << EOF
# Per-unit memory limit (fix_memory_ceilings.sh). MUST live here, not in service.d/.
# override.conf sorts after 00-thunderbird-default-memory.conf so it wins for THIS unit.
[Service]
MemoryMax=${max}
MemoryHigh=${high}
EOF
    echo "  ${unit} → MemoryMax=${max}"
}

# ----------------------------------------------------------------------------
# Per-service ceilings (each in its OWN unit dir)
# ----------------------------------------------------------------------------
write_override opencode-spsa-monitor      2147483648 1610612736   # 2.0 GB
write_override qdrant                      4294967296 3221225472   # 4.0 GB
write_override d2m-gmail-agentmail-bridge  1610612736 1342177280   # 1.5 GB
write_override hale-credential-check        536870912  469762048   # 512 MB
write_override thunderbird-continuity      1610612736 1342177280   # 1.5 GB
write_override staff_tasking_timers_system  536870912  469762048   # 512 MB
write_override inbox-hygiene                134217728  117440512   # 128 MB

# ----------------------------------------------------------------------------
# Fleet default — 00- prefix so it sorts FIRST (base layer, overridden per-unit).
# ----------------------------------------------------------------------------
echo "  00-default (fleet fallback) → MemoryMax=1073741824 (1 GB)"
cat > "$SHARED_DIR/00-thunderbird-default-memory.conf" << 'EOF'
# FLEET-WIDE DEFAULT — applies to every user .service unit WITHOUT its own override.
# 00- prefix is load-bearing: it must sort FIRST so per-unit override.conf files win.
# Do NOT add other MemoryMax confs to this service.d/ dir — they apply to every unit
# and the lexically-last basename silently clobbers all per-service limits.
[Service]
MemoryMax=1073741824
MemoryHigh=805306368
EOF

# ----------------------------------------------------------------------------
# Reload + verify
# ----------------------------------------------------------------------------
echo ""
echo "Reloading systemd user services..."
systemctl --user daemon-reload

echo "Restarting services with new memory limits..."
for svc in opencode-spsa-monitor d2m-gmail-agentmail-bridge hale-credential-check; do
    systemctl --user restart "${svc}.service" 2>/dev/null || echo "  (${svc} not running)"
done

echo ""
echo "✅ Memory ceilings applied. Enforced values (kernel truth):"
for svc in qdrant opencode-spsa-monitor d2m-gmail-agentmail-bridge \
           hale-credential-check thunderbird-continuity ci-sentinel; do
    printf "  %-32s " "$svc"
    systemctl --user show "${svc}.service" -p MemoryMax --value 2>/dev/null || echo "(not found)"
done

echo ""
echo "📊 System memory status:"
free -h
echo ""
echo "✅ DONE. Per-unit overrides win; ci-sentinel should show the 1G fallback."

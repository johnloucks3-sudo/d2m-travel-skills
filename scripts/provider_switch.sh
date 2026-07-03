#!/usr/bin/env bash
# provider_switch.sh — Thunderbird Wing AI Provider Switcher
# Source this in ~/.bashrc: source ~/Thunderbird/scripts/provider_switch.sh
# Then type: pswitch <provider>  to hop between AI providers instantly.
#
# How it works:
#   Claude Code reads ANTHROPIC_BASE_URL — if set, it routes through LiteLLM
#   instead of calling Anthropic directly. ANTHROPIC_MODEL tells LiteLLM which
#   model to use. ANTHROPIC_AUTH_TOKEN is the LiteLLM gateway key.
#
# Gateway: http://localhost:4000  (d2m-litellm-gateway.service)
# Config:  ~/.claude/gateway/litellm_config.yaml
# Poe models: routed through gateway → https://api.poe.com/v1

_GATEWAY="http://localhost:4000"
_GATEWAY_KEY="sk-ant-d2m-gateway-key"

pswitch() {
  local p="${1:-status}"
  case "$p" in

    # ── DIRECT ANTHROPIC (Claude Code native, no gateway) ──────────────────
    a|anthropic|direct|native|claude)
      unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY
      unset ANTHROPIC_MODEL
      echo "✅ Provider: Anthropic direct  (no gateway — Claude Code native)"
      ;;

    # ── POE.COM PROVIDERS (points-based, via LiteLLM gateway) ──────────────
    ds|deepseek|poe-deepseek)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-deepseek"
      echo "✅ Provider: DeepSeek V3.2  (via Poe → gateway:4000)"
      ;;

    grok|poe-grok)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-grok4"
      echo "✅ Provider: Grok 4.3  (via Poe → gateway:4000)"
      ;;

    gf|grok-fast|poe-grok-fast)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-grok-fast"
      echo "✅ Provider: Grok 4.1 Fast  (via Poe → gateway:4000)"
      ;;

    poe-gemini|pg)
      echo "⚠  poe-gemini disabled — Poe Gemini forced-thinking mode returns empty content. Use: pswitch gemini"
      ;;

    r1|poe-r1)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-r1"
      echo "✅ Provider: DeepSeek V4 Flash-E (cheapest)  (via Poe → gateway:4000)"
      echo "⚠  PII fence: no client data"
      ;;

    kimi|poe-kimi)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-kimi"
      echo "✅ Provider: Kimi K2.5 (2M context)  (via Poe → gateway:4000)"
      echo "⚠  PII fence: no client data"
      ;;

    poe-claude|pc)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="poe-claude"
      echo "✅ Provider: Claude Sonnet 4.6  (via Poe → gateway:4000)"
      ;;

    # ── OPENFERENCE (free plan — open-source models) ─────────────────────────
    of|openference)
      export ANTHROPIC_BASE_URL="https://api.openference.com/"
      export ANTHROPIC_API_KEY="$OPENFERENCE_API_KEY"
      export ANTHROPIC_AUTH_TOKEN="$OPENFERENCE_API_KEY"
      export ANTHROPIC_MODEL="GLM-5.2"
      echo "✅ Provider: Openference — GLM 5.2 (free plan via api.openference.com)"
      ;;

    # ── DEEPINFRA ($10 balance — cheap inference) ──────────────────────────
    di|deepinfra)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="deepinfra-llama"
      echo "✅ Provider: DeepInfra Llama-3.3-70B  (paid, cheap → gateway:4000)"
      ;;

    di-r1|deepinfra-r1)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="deepinfra-r1"
      echo "✅ Provider: DeepInfra DeepSeek-R1  (paid, reasoning → gateway:4000)"
      ;;

    di-ds|deepinfra-ds)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="deepinfra-deepseek"
      echo "✅ Provider: DeepInfra DeepSeek-V3  (paid → gateway:4000)"
      ;;

    # ── FREE TIER PROVIDERS (via LiteLLM gateway) ──────────────────────────
    groq)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="groq-llama"
      echo "✅ Provider: Groq Llama-3.3-70B  (free tier → gateway:4000)"
      ;;

    cerebras)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="cerebras-llama"
      echo "✅ Provider: Cerebras  (free tier → gateway:4000)"
      ;;

    gemini|flash)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="gemini-fallback"
      echo "✅ Provider: Gemini 2.5 Flash  (via API key → gateway:4000)"
      ;;

    grok-direct|xai)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="grok"
      echo "✅ Provider: Grok  (xAI direct API → gateway:4000)"
      ;;

    # ── TRAVEL AGENT (auto-failover chain) ─────────────────────────────────
    ta|travel-agent)
      export ANTHROPIC_BASE_URL="$_GATEWAY"
      export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
      export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
      export ANTHROPIC_MODEL="travel-agent"
      echo "✅ Provider: travel-agent  (Sonnet → Groq → Poe-DeepSeek → Gemini)"
      ;;

    # ── GATEWAY STATUS ──────────────────────────────────────────────────────
    ping|health)
      echo -n "Gateway status: "
      curl -s --max-time 3 "$_GATEWAY/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ ONLINE' if d.get('status')=='healthy' else '⚠ ' + str(d))" 2>/dev/null || echo "❌ OFFLINE (start: systemctl --user start d2m-litellm-gateway)"
      ;;

    # ── STATUS ──────────────────────────────────────────────────────────────
    status|"")
      echo ""
      if [ -n "${ANTHROPIC_BASE_URL}" ]; then
        echo "  Active provider : ${ANTHROPIC_MODEL:-unknown}  via  ${ANTHROPIC_BASE_URL}"
      else
        echo "  Active provider : Anthropic direct  (no gateway)"
      fi
      echo ""
      echo "  Providers:"
      echo "    pswitch a          → Anthropic direct (Claude Code native)"
      echo "    pswitch ds         → DeepSeek V3.2     (Poe)"
      echo "    pswitch grok       → Grok 4.3           (Poe)"
      echo "    pswitch gf         → Grok 4.1 Fast      (Poe)"
      echo "    pswitch gemini     → Gemini 2.5 Flash   (direct API key — Poe Gemini broken)"
      echo "    pswitch r1         → DeepSeek V4 Flash-E (Poe, PII-fence)"
      echo "    pswitch kimi       → Kimi K2.5 2M ctx   (Poe, PII-fence)"
      echo "    pswitch di         → DeepInfra Llama-3.3 (\$10 balance)"
      echo "    pswitch di-r1      → DeepInfra R1        (\$10 balance)"
      echo "    pswitch di-ds      → DeepInfra DeepSeek-V3 (\$10 balance)"
      echo "    pswitch groq       → Groq Llama-3.3     (free)"
      echo "    pswitch cerebras   → Cerebras            (free)"
      echo "    pswitch gemini     → Gemini 2.5 Flash   (API key)"
      echo "    pswitch ta         → travel-agent        (auto-failover)"
      echo "    pswitch of         → Openference GLM-5.2 (free plan)"
      echo "    pswitch ping       → gateway health check"
      echo ""
      ;;

    *)
      echo "Unknown provider: $p  |  Run: pswitch status"
      return 1
      ;;
  esac
}

# Short alias — ps <keyword> switches provider env vars only
alias ps=pswitch

# ── ONE-WORD LAUNCH FUNCTIONS ───────────────────────────────────────────────
# Each function: sets ANTHROPIC_BASE_URL + API key spoofing + model, then
# launches `claude` (or passes args through). Completely self-contained —
# no dependency on pswitch being already run.

_ps_launch() {
  local model="$1"; shift
  local label="$1"; shift
  export ANTHROPIC_BASE_URL="$_GATEWAY"
  export ANTHROPIC_AUTH_TOKEN="$_GATEWAY_KEY"
  export ANTHROPIC_API_KEY="$_GATEWAY_KEY"
  export ANTHROPIC_MODEL="$model"
  echo "⚡ $label → gateway:4000"
  cd ~/Thunderbird && claude "$@"
}

pa()      { unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY ANTHROPIC_MODEL; echo "⚡ Anthropic direct (native — explicit override)"; cd ~/Thunderbird && claude "$@"; }
poc()     { echo "⚡ OpenCode (DeepSeek direct)"; cd ~/Thunderbird && opencode "$@"; }
pds()     { _ps_launch "poe-deepseek"      "DeepSeek V3.2 (Poe)"         "$@"; }
pgrok()   { _ps_launch "poe-grok4"         "Grok 4.3 (Poe)"              "$@"; }
pgf()     { _ps_launch "poe-grok-fast"     "Grok 4.1 Fast (Poe)"         "$@"; }
pr1()     { _ps_launch "poe-r1"            "DeepSeek V4 Flash-E (Poe·PII-fence)" "$@"; }
pkimi()   { _ps_launch "poe-kimi"          "Kimi K2.5 2M (Poe·PII-fence)" "$@"; }
ppc()     { _ps_launch "poe-claude"        "Claude Sonnet 4.6 (Poe)"     "$@"; }
pgemini() { _ps_launch "gemini-fallback"   "Gemini 2.5 Flash"            "$@"; }
pdi()     { _ps_launch "deepinfra-llama"   "DeepInfra Llama-3.3 (\$10)"  "$@"; }
pdir1()   { _ps_launch "deepinfra-r1"      "DeepInfra R1 (\$10)"         "$@"; }
pdids()   { _ps_launch "deepinfra-deepseek" "DeepInfra DeepSeek (\$10)"  "$@"; }
pgroq()   { _ps_launch "groq-llama"        "Groq Llama-3.3 (free)"       "$@"; }
pcb()     { _ps_launch "cerebras-llama"    "Cerebras (free)"             "$@"; }
pta()     { _ps_launch "travel-agent"      "travel-agent (auto-failover)" "$@"; }
pxai()    { _ps_launch "grok"              "Grok xAI direct"             "$@"; }
pof()     { export ANTHROPIC_BASE_URL="https://api.openference.com/"; export ANTHROPIC_API_KEY="$OPENFERENCE_API_KEY"; export ANTHROPIC_AUTH_TOKEN="$OPENFERENCE_API_KEY"; export ANTHROPIC_MODEL="GLM-5.2"; echo "⚡ Openference GLM 5.2 (free plan)"; cd ~/Thunderbird && claude "$@"; }

# Auto-announce current provider when sourced
if [ -n "${ANTHROPIC_BASE_URL}" ]; then
  echo "  [provider_switch] Gateway active: ${ANTHROPIC_MODEL} via ${ANTHROPIC_BASE_URL}"
fi

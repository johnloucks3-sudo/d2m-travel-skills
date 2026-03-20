#!/usr/bin/env bash
# thunderbird-remote.sh — Launch Claude Code Remote Control for Thunderbird OS
# IOC-3: Remote Control — access YOGA Claude Code from phone/Chromebook/anywhere
#
# Modes:
#   ./scripts/thunderbird-remote.sh              # Interactive + remote accessible
#   ./scripts/thunderbird-remote.sh --server      # Server mode (waits for connections)
#   ./scripts/thunderbird-remote.sh --headless "prompt"  # Non-interactive (scripting)
#   ./scripts/thunderbird-remote.sh --daemon      # tmux detached server
#
# Remote Control shows a URL + QR code. Open on phone/tablet to control the session.
# Headless mode runs non-interactively for scripting/cron.

set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

# Check prerequisites
if ! command -v claude &>/dev/null; then
    echo "ERROR: claude CLI not found."
    exit 1
fi

MODE="${1:-interactive}"
shift 2>/dev/null || true

case "$MODE" in
    --server)
        echo "═══════════════════════════════════════════════"
        echo "  THUNDERBIRD OS — Remote Control Server"
        echo "  Working dir: $(pwd)"
        echo "═══════════════════════════════════════════════"
        echo ""
        echo "Waiting for remote connections..."
        echo "Press SPACE to show QR code."
        echo ""
        exec claude remote-control --name "Thunderbird OS"
        ;;

    --headless)
        # Non-interactive mode for scripting
        PROMPT="${1:?Usage: thunderbird-remote.sh --headless \"your prompt\"}"
        shift
        claude -p "$PROMPT" \
            --allowedTools "Read,Edit,Bash,Grep,Glob,Write" \
            --output-format json \
            "$@"
        ;;

    --daemon)
        # Launch in detached tmux session
        SESSION="thunderbird-remote"
        if tmux has-session -t "$SESSION" 2>/dev/null; then
            echo "Session '$SESSION' already running. Attach with: tmux attach -t $SESSION"
            exit 0
        fi
        tmux new-session -d -s "$SESSION" \
            "cd $(pwd) && claude remote-control --name 'Thunderbird OS'"
        echo "Remote Control launched in tmux session: $SESSION"
        echo "Attach: tmux attach -t $SESSION"
        echo "Kill:   tmux kill-session -t $SESSION"
        ;;

    --help|-h)
        head -14 "$0" | grep '^#' | sed 's/^# \?//'
        exit 0
        ;;

    *)
        # Default: interactive + remote accessible
        echo "═══════════════════════════════════════════════"
        echo "  THUNDERBIRD OS — Interactive + Remote Control"
        echo "  Working dir: $(pwd)"
        echo "═══════════════════════════════════════════════"
        echo ""
        exec claude --remote-control
        ;;
esac

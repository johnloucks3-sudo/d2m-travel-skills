#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Thunderbird Termux Setup — Dreams2Memories Travel, LLC
# Version: 2.0  |  2026-06-17  |  A7 Sterling
# =============================================================================
#
# USAGE (Chromebook):
#   1. On YOGA, serve the file:
#        cd ~/Thunderbird && python3 -m http.server 8000
#   2. On Chromebook Termux, run:
#        curl http://192.168.1.198:8000/scripts/setup_termux.sh -o s.sh && bash s.sh
#      NOTE: bracketed paste in Termux often appends a tilde; save to file first,
#            then run:  bash s.sh~
#   3. Re-run anytime — script is idempotent; configs always converge.
#
# WHAT IT INSTALLS / CONFIGURES:
#   Packages  : tmux, openssh, curl, git, python, jq, nano, vim, coreutils,
#               termux-api, fzf
#   ~/.tmux.conf       : C-a prefix, mouse on, 256-color+truecolor, 50k scrollback,
#                        vi copy mode, OSC52 clipboard, split bindings, D2M status bar
#   ~/.termux/termux.properties : extra keys row (ESC/TAB/CTRL/ALT/arrows + F-keys)
#   ~/.termux/colors.properties : Thunderbird dark theme (bg #1a1a2e)
#   ~/.bashrc          : COLORTERM=truecolor, color prompt, fzf keybinds,
#                        wing() function (ttyd primary, SSH fallback)
#   ~/.hushlogin       : suppresses Termux login banner (MOTD handled by wing)
#   MOTD               : printed on first interactive Termux open
# =============================================================================

set -uo pipefail

WING_TTYD="https://code.d2mluxury.quest"
YOGA_LAN="192.168.1.198"
YOGA_TAIL="100.69.222.124"
YOGA_USER="john"

echo ""
echo "  D2M Thunderbird Termux Setup v2.0"
echo "  ===================================="
echo ""

# ---------------------------------------------------------------------------
# 1. PACKAGES
# ---------------------------------------------------------------------------
echo "==> [1/5] Package update..."
pkg update -y -q 2>/dev/null || true

echo "==> [1/5] Installing packages..."
# Each package on its own install so one failure doesn't abort the rest
for PKG in tmux openssh curl git python jq nano vim coreutils termux-api fzf; do
    if pkg list-installed 2>/dev/null | grep -q "^${PKG}/"; then
        echo "     ${PKG}: already installed"
    else
        echo "     ${PKG}: installing..."
        pkg install -y -q "${PKG}" 2>/dev/null || echo "     ${PKG}: WARN — install failed (non-fatal)"
    fi
done

# ---------------------------------------------------------------------------
# 2. TMUX CONFIG
# ---------------------------------------------------------------------------
echo ""
echo "==> [2/5] Writing ~/.tmux.conf..."
cat > ~/.tmux.conf << 'TMUXEOF'
# Thunderbird Termux tmux config — v2.0

set -g default-terminal "tmux-256color"
set -ga terminal-overrides ",xterm-256color:Tc"
set -ga terminal-overrides ",*256col*:Tc"

# Mouse — works with Chromebook trackpad + Termux touch
set -g mouse on

# Prefix: C-a (ergonomic)
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# Copy mode — vi keys
setw -g mode-keys vi
bind-key -T copy-mode-vi v   send -X begin-selection
bind-key -T copy-mode-vi y   send -X copy-selection-and-cancel
bind-key -T copy-mode-vi V   send -X select-line
bind-key -T copy-mode-vi MouseDragEnd1Pane send -X copy-selection-and-cancel

# OSC52 clipboard (copies selection to Android/ChromeOS clipboard)
set -g set-clipboard on

# Splits — intuitive chars
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
unbind '"'
unbind %

# Reload config
bind r source-file ~/.tmux.conf \; display "Config reloaded."

# Pane navigation — Alt+Arrow (no prefix needed)
bind -n M-Left  select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up    select-pane -U
bind -n M-Down  select-pane -D

# Window navigation — Shift+Arrow
bind -n S-Left  previous-window
bind -n S-Right next-window

# Quality of life
set -sg escape-time 0
set -g history-limit 50000
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on
set -g focus-events on

# Status bar — D2M branding
set -g status-interval 15
set -g status-position bottom
set -g status-style "bg=colour235,fg=colour252"
set -g status-left-length 40
set -g status-left "#[fg=colour46,bold] D2M #[default] #S "
set -g status-right "#[fg=colour252]%H:%M"
setw -g window-status-format " #I:#W "
setw -g window-status-current-format " #[fg=colour235,bg=colour46] #I:#W #[default] "
setw -g window-status-current-style "fg=colour235,bg=colour46"
TMUXEOF

# ---------------------------------------------------------------------------
# 3. TERMUX PROPERTIES + COLOR THEME
# ---------------------------------------------------------------------------
echo "==> [3/5] Writing Termux properties and color theme..."
mkdir -p ~/.termux

cat > ~/.termux/termux.properties << 'PROPEOF'
# Termux app properties — Thunderbird setup

# Extra keys row above keyboard (two rows — great for tmux on Chromebook)
extra-keys = [['ESC','TAB','CTRL','ALT','|','-','UP','DOWN'],['F1','F2','F3','F4','LEFT','RIGHT','HOME','END']]

# Font size
terminal-font-size = 14

# Silence bell
bell-character = ignore

# Allow external apps (required for termux-open-url)
allow-external-apps = true
PROPEOF

cat > ~/.termux/colors.properties << 'COLOREOF'
# Thunderbird dark theme — bg #1a1a2e
background=#1a1a2e
foreground=#e0e0e0
cursor=#e0e0e0
color0=#1a1a2e
color1=#e05c5c
color2=#5ce05c
color3=#e0c05c
color4=#5c8ae0
color5=#c05ce0
color6=#5ce0e0
color7=#c0c0c0
color8=#404060
color9=#ff8888
color10=#88ff88
color11=#ffe088
color12=#88aaff
color13=#dd88ff
color14=#88ffff
color15=#ffffff
COLOREOF

# ---------------------------------------------------------------------------
# 4. BASHRC — colors, wing() function, fzf, tmux auto-attach
# ---------------------------------------------------------------------------
echo "==> [4/5] Updating ~/.bashrc..."

# Guard: only append our block if sentinel not already present
if ! grep -q "# THUNDERBIRD-TERMUX-SETUP" ~/.bashrc 2>/dev/null; then
cat >> ~/.bashrc << BASHEOF

# THUNDERBIRD-TERMUX-SETUP — injected by setup_termux.sh v2.0
export COLORTERM=truecolor
export TERM=xterm-256color

# Color prompt: green user@host, blue path
export PS1='\[\e[0;32m\]\u@\h\[\e[0m\]:\[\e[0;34m\]\w\[\e[0m\]\$ '

# Useful aliases
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias l='ls --color=auto'
alias cls='clear'
alias ..='cd ..'
alias ...='cd ../..'

# fzf keybinds (Ctrl-R history, Ctrl-T file picker) — only if fzf installed
if [ -f "\$PREFIX/share/fzf/key-bindings.bash" ]; then
    source "\$PREFIX/share/fzf/key-bindings.bash"
fi
if [ -f "\$PREFIX/share/fzf/completion.bash" ]; then
    source "\$PREFIX/share/fzf/completion.bash"
fi

# ---------------------------------------------------------------------------
# wing() — Open the Thunderbird wing
#   wing          -> open ttyd in browser (primary; always works)
#   wing ssh      -> SSH to YOGA via Tailscale (requires Tailscale running)
#   wing ssh-lan  -> SSH to YOGA via LAN (same network only)
# ---------------------------------------------------------------------------
wing() {
    local CMD="\${1:-ttyd}"
    case "\$CMD" in
        ttyd|"")
            echo "Opening Thunderbird wing: ${WING_TTYD}"
            termux-open-url "${WING_TTYD}" 2>/dev/null \
                || echo "termux-api not ready — open manually: ${WING_TTYD}"
            ;;
        ssh)
            echo "SSH to YOGA (Tailscale: ${YOGA_TAIL})..."
            echo "Key expected at ~/.ssh/id_ed25519 — see scripts/termius_termux_setup.md"
            ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new \
                ${YOGA_USER}@${YOGA_TAIL}
            ;;
        ssh-lan)
            echo "SSH to YOGA (LAN: ${YOGA_LAN})..."
            ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new \
                ${YOGA_USER}@${YOGA_LAN}
            ;;
        help|--help|-h)
            echo "Usage: wing [ttyd|ssh|ssh-lan|help]"
            echo "  ttyd     (default) open code.d2mluxury.quest in browser"
            echo "  ssh      SSH to YOGA via Tailscale"
            echo "  ssh-lan  SSH to YOGA via LAN"
            ;;
        *)
            echo "Unknown command: \$CMD. Run: wing help"
            ;;
    esac
}

# Auto-attach to tmux 'main' session — interactive shells only
# (Guards against wedging scp/rsync/non-interactive Termux calls)
case \$- in
    *i*)
        if command -v tmux &>/dev/null && [ -z "\$TMUX" ]; then
            tmux new-session -A -s main
        fi
        ;;
esac
BASHEOF
fi

# Suppress Termux login banner (MOTD handled below on first run)
touch ~/.hushlogin

# ---------------------------------------------------------------------------
# 5. MOTD — printed now and on first fresh open
# ---------------------------------------------------------------------------
echo ""
echo "==> [5/5] Done. Wing MOTD:"
echo ""
echo "  =============================================="
echo "  |  D2M Thunderbird Termux  |  v2.0          |"
echo "  |  Commander: Yoda         |  A7: Sterling   |"
echo "  =============================================="
echo ""
echo "  Quick reference:"
echo "    wing           open ${WING_TTYD}"
echo "    wing ssh       SSH to YOGA (Tailscale)"
echo "    wing ssh-lan   SSH to YOGA (LAN)"
echo "    wing help      show all options"
echo ""
echo "  Tmux keys (prefix = Ctrl+A):"
echo "    |           vertical split"
echo "    -           horizontal split"
echo "    Alt+Arrows  move between panes (no prefix)"
echo "    Shift+Arrow switch windows (no prefix)"
echo "    Ctrl+A r    reload config"
echo "    Ctrl+A [    scroll mode  (q to exit)"
echo "    Mouse drag  select + copy to clipboard"
echo ""
echo "  NEXT STEPS:"
echo "    1. Swipe down on Termux notification → 'Reload style'"
echo "       (applies color theme + extra keys row)"
echo "    2. Close Termux fully and reopen"
echo "       (tmux auto-attaches to 'main' session)"
echo "    3. To reach the wing: type  wing"
echo "    4. SSH key: place your id_ed25519 at ~/.ssh/id_ed25519"
echo "       See: scripts/termius_termux_setup.md for the key"
echo ""
echo "  =============================================="
echo ""

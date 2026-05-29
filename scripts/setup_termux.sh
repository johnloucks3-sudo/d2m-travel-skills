#!/data/data/com.termux/files/usr/bin/bash
# Thunderbird Termux Setup
# Paste into Termux and run:  bash setup_termux.sh
# Or one-liner from YOGA:
#   curl http://192.168.1.198:8000/scripts/setup_termux.sh | bash

set -e

echo "==> Installing packages..."
pkg update -y -q && pkg install -y -q tmux curl

echo "==> Writing ~/.tmux.conf..."
cat > ~/.tmux.conf << 'TMUXEOF'
# Thunderbird Termux tmux config

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

# OSC52 clipboard (copies to Android/ChromeOS clipboard)
set -g set-clipboard on

# Splits
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

# Status bar
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

echo "==> Updating ~/.bashrc..."
grep -q "COLORTERM=truecolor" ~/.bashrc 2>/dev/null || cat >> ~/.bashrc << 'BASHEOF'

# Thunderbird terminal config
export COLORTERM=truecolor
export TERM=xterm-256color

# Auto-attach to tmux session when opening Termux
if command -v tmux &>/dev/null && [ -z "$TMUX" ]; then
  tmux new-session -A -s main
fi
BASHEOF

echo "==> Writing ~/.termux/termux.properties..."
mkdir -p ~/.termux
cat > ~/.termux/termux.properties << 'PROPEOF'
# Termux app properties — Thunderbird setup

# Extra keys row above keyboard (two rows — great for tmux without Hacker's Keyboard)
extra-keys = [['ESC','TAB','CTRL','ALT','|','-','UP','DOWN'],['F1','F2','F3','F4','LEFT','RIGHT','HOME','END']]

# Font size (adjust to taste)
terminal-font-size = 14

# Silence bell
bell-character = ignore

# Allow external apps to access Termux storage
allow-external-apps = true
PROPEOF

echo "==> Writing ~/.termux/colors.properties (Thunderbird dark theme)..."
cat > ~/.termux/colors.properties << 'COLOREOF'
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

echo ""
echo "============================================"
echo " Thunderbird Termux setup complete."
echo "============================================"
echo ""
echo " Next steps:"
echo "   1. Swipe down on Termux notification → 'Reload style'"
echo "      (applies color theme and extra keys row)"
echo "   2. source ~/.bashrc  (or close and reopen Termux)"
echo "      (tmux will auto-start on next open)"
echo ""
echo " Tmux key reference:"
echo "   Prefix      = Ctrl+A"
echo "   |           = vertical split"
echo "   -           = horizontal split"
echo "   Alt+Arrows  = move between panes (no prefix)"
echo "   Shift+Arrow = switch windows (no prefix)"
echo "   Ctrl+A r    = reload config"
echo "   Ctrl+A [    = scroll mode (q to exit)"
echo "   Mouse drag  = select + copy to clipboard"
echo ""

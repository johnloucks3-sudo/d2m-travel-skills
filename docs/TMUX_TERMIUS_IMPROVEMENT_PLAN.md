# tmux + Termius Improvement Plan
**Baseline source:** Hwee-Boon Yar, "Using tmux with Claude Code" (Nov 2025, updated Jul 2026)
**Author:** Hale · 2026-07-19

---

## Article summary

The author runs Claude Code (and Droid/Codex) entirely inside plain tmux — no
tmux-specific Claude Code plugin. His argument: tmux already has the
primitives coding agents need (`capture-pane` to read logs/other-agent
output, `send-keys` to drive a pane, stable targets like `main:3.1`,
copy-mode for scroll/search), so the real work is (1) a thin, correctly
configured `~/.tmux.conf` and (2) documenting the session convention in
AGENTS.md so the agent can act on it — not building a wrapper.

Concrete recommendations:
- One main tmux session; windows = projects/agents; panes addressed as
  `session:window.pane` (his shorthand: "tmux 3.1").
- Dev servers and long-running jobs live in tmux, not backgrounded blind —
  the agent can read their pane output directly and iterate on errors.
- Auto-rename windows from pane content (`hb post draft` instead of five
  panes all named "claude") so the status bar is scannable at a glance.
- `~/.tmux.conf`: `allow-passthrough on`, `extended-keys on`,
  `terminal-features 'xterm*:extkeys'` — lets Shift+Enter insert a newline
  instead of submitting, and lets desktop notifications pass through tmux to
  the outer terminal.
- Plain tmux inside iTerm2, **not** `tmux -CC` integration mode — it breaks
  the alternate screen buffer / mouse tracking Claude Code's fullscreen UI
  needs.
- `mouse on` if you want wheel-scroll in Claude Code's `/tui fullscreen` mode.
- Bind through ctrl-shortcuts the agent needs (his example: `bind o send-keys
  C-o`) when your tmux prefix collides with an agent's own ctrl-shortcut.
- `tmux capture-pane -t 0 -p -S -10000 | <editor>` to dump a whole pane's
  scrollback into an editor for review.
- Runs 3-5 agent sessions in parallel, each its own window, coordinated by
  telling one agent to read another's pane.

---

## Current-state audit (Thunderbird / YOGA, verified 2026-07-19)

| Area | State |
|---|---|
| `~/.tmux.conf` | Exists, actively maintained (updated 2026-05-24). Has: `tmux-256color` + truecolor, **OSC52 clipboard passthrough already** (ahead of the article — needed for ttyd/xterm.js browser copy-paste), vi copy-mode, 50k scrollback, mouse on, custom D2M status bar (`usage_chyron.py` in status-right), prefix remapped to `C-a`. |
| Article's passthrough settings | **Missing**: `allow-passthrough on`, `extended-keys on`, `terminal-features 'xterm*:extkeys'`. Shift+Enter behavior and desktop-notification passthrough are not guaranteed without these. |
| Window auto-rename | **Not implemented.** Windows carry manual/default names only. |
| tmux convention documented for agents | **Not documented.** Neither `AGENTS.md` nor `CLAUDE.md` state a canonical session name, window/pane addressing convention, or where dev servers live. Article's core insight — "the agent can act on the convention if you document it" — isn't captured yet. |
| Multi-agent tmux coordination | **Already have something better than the article's manual approach**: `cc-fleet` (`ccf`, on PATH at `~/.local/bin/ccf`) is installed. It spawns real `claude` processes with the backend swapped to any Anthropic/OpenAI-compatible provider (DeepSeek, GLM, Kimi, Qwen, Codex) as live tmux-pane teammates (`ccf spawn`, `/team`, `/workflow`, `/subagent`), with `ccf hide`/`ccf show` to park panes and `ccf teardown` to guarantee no ghost process keeps billing. This *is* the "auto-rename + coordinate agent panes" problem, already solved, one layer up from raw tmux. |
| Native Claude Code Agent Teams flag | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` **not set** in `~/.claude/settings.json` — cc-fleet's team/pane features sit on top of this flag; it's currently off, so `ccf`'s pane-teammate mode can't engage until it's set (cc-fleet's own first-run offers to write it, per its README). |
| Remote access | Termius (Z Fold phone) + Termux (Android fallback) → SSH over Tailscale (`100.69.222.124`) to YOGA, key-based auth (rotated 2026-07-05 after a leaked-key incident, `docs/SECURITY_REMEDIATION_RUNBOOK_20260617.md`). `scripts/termius_termux_setup.md` is current and accurate. Primary path is actually `wing()` bash function → ttyd web terminal at `code.d2mluxury.quest`, SSH+tmux is the fallback. |
| Long-running/detached sessions | `scripts/thunderbird-remote.sh --daemon` already launches `claude remote-control` in a detached tmux session (`thunderbird-remote`) — matches the article's "keep dev servers / long jobs in tmux" pattern. |
| `/tui fullscreen` | Not referenced anywhere in the repo — unconfirmed whether current Claude Code version on YOGA has it. |
| capture-pane→editor helper | Not present. No `v`-equivalent script. |

**Net assessment:** the config foundation is solid and in some ways ahead of
the article (OSC52, status-bar chyron). The gap is entirely on the
*convention* side — nothing documents tmux session/window/pane addressing
for agents, no auto-rename, and the one feature that would give the biggest
win (native multi-provider agent-team panes via `cc-fleet`) is one flag away
from being usable and isn't mentioned in AGENTS.md at all.

---

## Improvement plan

### P0 — done this session (low-risk, config/doc only)
1. **Add the three missing passthrough settings** to `~/.tmux.conf`
   (`allow-passthrough on`, `extended-keys on`, `terminal-features
   'xterm*:extkeys'`) — fixes Shift+Enter and notification passthrough.
2. **Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`** in
   `~/.claude/settings.json` — unlocks the flag `cc-fleet` needs for
   pane-teammate mode; additive, no behavior change unless invoked.
3. **Document the tmux convention in `AGENTS.md`**: canonical single main
   session, `session:window.pane` addressing, where dev servers live,
   pointer to `cc-fleet` for multi-provider teammates instead of a
   hand-rolled pattern, and the `capture-pane` idiom for reading another
   pane/agent's output.

### P1 — next (needs a short build, no external dependency)
4. **Window auto-rename hook.** Article's biggest ergonomic win and the one
   piece genuinely missing here. Implement as a small `tmux.conf`
   `set-hook -g pane-focus-in` / periodic `status-interval` script that
   inspects `#{pane_current_command}` and the first line of
   `capture-pane -p -S -3`, and calls `rename-window`. Since Thunderbird
   already runs multi-agent panes via `cc-fleet` (which assigns names+colors
   per teammate) and via `thunderbird-remote.sh --daemon` (single fixed
   session name), scope this first to *manually opened* windows — don't
   fight `cc-fleet`'s own naming.
5. **Ctrl-shortcut passthrough audit.** Current prefix is `C-a`, not the
   article's `C-w`, so the specific collision he hit (`ctrl-o`) likely
   doesn't apply here — but audit Claude Code's own ctrl-shortcuts
   (transcript expand, etc.) against the current tmux bind table and add
   `send-keys` passthroughs for any that collide.
6. **`capture-pane`-to-file helper script** (`scripts/tmux-dump.sh`) —
   `tmux capture-pane -t <target> -p -S -10000 > /tmp/pane_dump.txt`, wired
   for both interactive use and headless-agent use (e.g. an agent asking
   "what did the dev server pane just print").

### P2 — verify / defer
7. **Confirm `/tui fullscreen` availability** on the installed Claude Code
   version; if present, decide whether the D2M status-bar chyron and OSC52
   clipboard setup still behave correctly under it before rolling it out as
   default.
8. **`tmux -CC` warning** — nothing in the repo suggests iTerm2 integration
   mode is in use (YOGA is Linux; Termius/Termux are plain SSH+tmux clients,
   not `-CC`), so this article warning is likely moot here — no action
   needed, just noting it's already avoided by the current architecture.

---

## Why cc-fleet changes the shape of this plan

The article's author hand-rolls multi-agent tmux coordination because his
tool doesn't have anything better. Thunderbird already has `cc-fleet`, which
does the same job with more structure: named/colored panes per teammate,
`hide`/`show` to park work without losing state, `teardown` to guarantee no
orphaned billing process, and provider-swap (DeepSeek/GLM/Kimi/Qwen/Codex)
built in — the same mechanism [[project_deepseek_claude_code_backend]]
proved out manually earlier today, but productized. The highest-leverage
move here isn't re-deriving the article's manual conventions from scratch;
it's turning `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` on (P0-2) and writing
`cc-fleet` into AGENTS.md as the default answer to "I need another agent
working alongside me in this session" (P0-3), then layering the article's
raw-tmux ergonomics (auto-rename, passthrough, capture-pane helper) on top
for the windows `cc-fleet` doesn't manage.

#!/usr/bin/env bash
# Per-seat git identity — C2 RECALIBRATION task 4, Commander directive 2026-07-29.
#
# WHY THIS EXISTS
#   Every one of the ~1,260 commits in this repo was authored as
#   "Claude Haiku 4.5 <noreply@anthropic.com>" because that string is hardcoded in
#   .git/config — NOT because Haiku wrote them. The Commander identified the real
#   mechanism on 2026-07-29: Gemini Flash brokered the headless /ask lane for Sonnet,
#   and every return was signed at the wrapper, not by the producing model. Result:
#   "who wrote this stub?" was permanently unanswerable, and no seat could be held to
#   the equal-performance standard.
#
# USAGE — source this before committing, from whichever seat you are:
#   source hooks/git_seat_identity.sh CC     # Claude Code
#   source hooks/git_seat_identity.sh OC     # OpenCode
#   source hooks/git_seat_identity.sh AG     # Victory / Antigravity
#   THUNDERBIRD_MODEL="claude-opus-5" source hooks/git_seat_identity.sh CC
#
# GIT_AUTHOR_NAME/EMAIL override .git/config, so this wins wherever it is set.
# If NOTHING sets a seat, .git/config now reads "Thunderbird Wing (seat unset)" —
# an honestly unattributed commit, never a falsely attributed one.

SEAT="${1:-${THUNDERBIRD_SEAT:-}}"

case "$SEAT" in
  CC) NAME="Hale CC (Claude Code)";      EMAIL="cc@thunderbird.d2m" ;;
  OC) NAME="Hale OC (OpenCode)";         EMAIL="oc@thunderbird.d2m" ;;
  AG) NAME="Hale AG (Victory)";          EMAIL="ag@thunderbird.d2m" ;;
  *)
    echo "git_seat_identity: unknown seat '${SEAT}' — expected CC, OC, or AG." >&2
    echo "Leaving identity unset; commits will be recorded as unattributed." >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

export THUNDERBIRD_SEAT="$SEAT"
export GIT_AUTHOR_NAME="$NAME"
export GIT_AUTHOR_EMAIL="$EMAIL"
export GIT_COMMITTER_NAME="$NAME"
export GIT_COMMITTER_EMAIL="$EMAIL"

echo "git identity → ${NAME} <${EMAIL}>  (model: ${THUNDERBIRD_MODEL:-unset})"

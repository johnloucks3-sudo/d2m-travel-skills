"""core/oversight — Wing Oversight v2.

Span ledger, failure taxonomy (MAST), and the enforcement layer that makes
oversight structurally unskippable rather than merely available to call.

Design rule (from the 2026-07-29 audit, which found six zero-caller oversight
functions): anything here that depends on a future session REMEMBERING to
invoke it is presumed dead on arrival. Writers are hooks and timers.
"""

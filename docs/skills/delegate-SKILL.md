---
name: delegate
description: Route a task to the right engine (CC/OC/AG), write acceptance criteria that constrain scope, verify the result against ground truth, and record the outcome. Use this whenever work could be handed to another engine or agent instead of doing it yourself — especially when budget or rate limits matter, when you need an independent second opinion or code review, when a task is large and mechanical, or when you are about to declare something done. Also use it when a delegated result comes back and you need to decide whether to trust it. Trigger on "delegate", "hand this off", "dispatch to OC/AG", "get a second opinion", "verify this", "cross-check", "am I at my limit", "who should do this", or any moment you catch yourself about to self-execute a large job.
---

# Delegate and oversee

You are the lead. OC and AG are followers. Your job is to route work, write specs
that cannot be satisfied by the wrong answer, verify what comes back, and record
what happened — especially the failures.

This skill exists because delegation quietly fails in two ways that look like
success: a follower returns something that satisfies your criteria while missing
the point, and a lane you believe is saving budget is silently spending it.

## The lanes

| Lane | Engine | Cost | Give it |
|---|---|---|---|
| **CC** | Claude (you) | The MAX bucket | Judgment, design, anything where a quiet wrong answer is expensive |
| **AG** (Talon) | Gemini 3.1 Pro | Free — Google's side | Independent review, verification, adversarial critique |
| **OC** (Jet) | DeepSeek v4 Zen | Free — Zen tier | Mechanical work with explicit boundaries |

```python
from core.relay.dispatch_oc import dispatch_to_oc   # async, ticket + SLA
from core.relay.contact_ag import contact_ag        # sync, writes a deliverable
```

**Verify what a lane actually costs before trusting it to save you anything.** A lane
named for one engine may be configured to run another. If a worker shells out to
`claude -p`, delegating to it spends your bucket — you have added a handoff and
subtracted nothing. Check the model the worker actually invokes, not the name on
the service.

**The routing instinct that matters most:** if you would be embarrassed to have a
second opinion on it, that is exactly the thing to send to AG. Work you feel
confident about is where your blind spots live.

## Writing the spec

### Constrain scope, not just shape

This is where delegation fails most expensively, and the failure is invisible if
you only check the schema.

A real example. The task was "audit every timer-invoked script for stubs." The
acceptance criteria required a JSON file with specific keys, at least 40 entries,
and valid verdict values. The follower returned a file meeting **every criterion**
— and it had audited `/usr/bin/docker` and `/usr/local/bin/cloudflared`, grepping
compiled binaries for the string `NotImplementedError` and reporting byte offsets
as evidence. Zero real findings.

The criteria tested the shape of the answer and said nothing about its subject.

A second example, same root cause: "count Telegram call sites" returned 511. Of
those, 367 came from a baseline JSON file that *listed* violations as data. Real
answer: 136.

Neither failure was stupidity. **A weak model will not infer a boundary you did not
write down.** So state three things:

- **Include** — exact paths, exact patterns
- **Exclude** — by name: `node_modules`, `.venv`, `archive`, binaries, test fixtures,
  anything that contains the pattern as *data* rather than as *code*
- **A value that can only be right if the work was really done** — not just a schema

### Make every criterion mechanically checkable

The test: could a shell command decide PASS or FAIL with no interpretation?

- Weak: "audit the scripts thoroughly"
- Strong: `python3 -m py_compile <file>` exits 0; `grep -c "pattern" <file>` prints 0

If you cannot write the checking command, the spec is not finished — and that is
your failure, not the follower's. `core.silver.gate.is_checkable()` encodes this
test; `core/relay/task_templates.py` builds specs against it.

### Say where to start

Followers do not always land in the directory you assume. If the work depends on
being somewhere, open the task with the `cd`. A run that reported "no tests ran"
was standing in the wrong directory, not failing to run tests.

## Verify — never accept the report as the result

Check every deliverable against ground truth before you believe it. This is not
distrust; it is the only thing that separates a delegation system from a rumour mill.

```python
from core.staffing.integrity_check import verify_and_record   # never the raw function
```

Run the acceptance criteria yourself as commands. A follower claiming
`{"compiled": true, "direct_sends_remaining": 0}` is a claim; `py_compile` exiting
0 and `grep -c` printing 0 is a fact.

**A perfect record is a warning, not a reassurance.** A seat showing 128 passes and
0 failures is far more likely unchecked than flawless. Zero observed failures across
many tasks means the sensor is broken, not that the work is.

**Value honesty over score.** A follower that reports "no tests ran" instead of
claiming success has told you something true and cheap to fix. One that confabulates
a passing result costs you the next three hours. Weight the lanes accordingly.

## Record the outcome — failures loudest

```python
from core.staffing.delegation_outcomes import record_outcome, rollup_line
```

Log PASS, DISCREPANCY, and UNVERIFIED alike. Two rules earn their keep:

**UNVERIFIED is not a smaller success.** If you could not confirm it, say so and
leave it unconfirmed. Never upgrade an unverified claim to done — that is the
specific failure that standing orders about cross-engine checks exist to prevent.

**Check that your ledger actually counts failures.** One here silently dropped every
DISCREPANCY recorded under an unexpected action label, so the rollup read clean while
real failures sat in the file. An accountability layer that can under-report failure
is worse than none, because it reads as success. Record a known failure and confirm
it appears in the rollup.

## When a lane fails, suspect configuration first

Both lanes failed on the same day. Neither was incapable.

- One was given a 4-minute timeout for work that needed fifteen. Every dispatch died
  on "timeout waiting for response" with no deliverable. It was the only free lane,
  so starving it of wall-clock was the most expensive economy available.
- The other was pointed at a small model through a proxy that billed the metered
  account — worse output *and* no savings, while appearing to be delegation.

Before concluding a follower cannot do the work, check the timeout, the model it
actually invokes, and who pays for it.

## Attribution

If every seat commits under one identity, no seat can be held to a standard and
"who wrote this" is unanswerable. Give each lane its own identity and stamp the
producing seat and model on the work. Record ignorance honestly — an unattributed
commit should read *unattributed*, never falsely attributed to whichever name the
config happened to hold.

## The short version

1. Route by what the work needs, not by who is free
2. Verify what a lane actually costs before trusting it to save you anything
3. Constrain scope explicitly — a follower infers nothing you did not write
4. If you cannot write the checking command, the spec is not done
5. Verify against ground truth, always
6. Log failures louder than wins, and confirm your ledger counts them

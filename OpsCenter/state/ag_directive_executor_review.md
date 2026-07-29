# ADVERSARIAL REVIEW: core/comms/directive_executor.py

Here is the requested breakdown of the vulnerabilities in `directive_executor.py`. 

### 1. Path to DONE without real verification (Self-Graded Homework)
**Vulnerability:** The caller defines the test it is graded on. 
**Line references:** Lines 76-81, 126
The `execute_directive` function accepts `ground_truth_cmds` directly from the caller. If an agent (or caller) provides trivial shell commands, it completely bypasses the integrity check.
**Exploit call:**
```python
execute_directive(
    directive_text="Deploy the database",
    work=lambda: "did nothing",
    claims=["Database is deployed"],
    ground_truth_cmds=["echo 'Database is deployed'"] # Trivial truth
)
```
The independent engine evaluates the output of `echo` and trivially returns `PASS`, returning `DONE` without any real verification. 

### 2. Path where Commander gets a completion reply for incomplete work
**Vulnerability:** Empty claims default to a generic "Done" message.
**Line references:** Lines 80, 143
There is no validation that `claims` actually contains any assertions. If `claims` is an empty list, `verify_and_record` has nothing to falsify and may default to `PASS`. The code then blindly formats a success string using a fallback.
**Exploit call:**
```python
execute_directive(
    directive_text="Build the payment gateway",
    work=lambda: "Failed to build due to missing API keys",
    claims=[],
    ground_truth_cmds=["echo pass"]
)
```
**Resulting Reply:** `"Done — directive executed\nArtifact: Failed to build due to missing API keys..."`
This tells the Commander it is "Done", implying completion, while the artifact actually contains a failure message.

### 3. UNVERIFIED-means-silence: A C2 Failure Mode
**Vulnerability:** Silent reads violate the closed-loop doctrine.
**Line references:** Lines 154-155 (`should_reply()`)
UNVERIFIED meaning silence is the wrong approach. It directly violates **SO-2026-06-25 (EMAIL CLOSED-LOOP)**: *"Every Commander email gets a closed-loop response... No silent reads."*
When `should_reply` suppresses UNVERIFIED responses, silence becomes an ambiguous failure mode for the Commander. He cannot distinguish between:
1. The agent is still thinking/working.
2. The agent crashed completely (process died).
3. The agent did the work but the verifier engine failed the check.
**Correction:** UNVERIFIED must generate a reply (e.g., `"UNVERIFIED — Work attempted but could not be independently confirmed. Manual review required."`) to close the loop without falsely asserting completion.

### 4. Swallowing exceptions in _capture() defeats its purpose
**Vulnerability:** Silent failure on critical audit logging.
**Line references:** Lines 66-73
The docstring for `_capture` explicitly states: *"A directive that is executed but never captured is how a MANDATORY instruction went missing"*. However, by wrapping the import and execution in a bare `try/except: pass`, any failure (e.g., disk full, module import error, permissions issue) will allow the work to proceed *without* capturing the directive. 
**Argument:** This is fundamentally incorrect. If capturing is "best-effort", a failure shouldn't silently discard the record. It should at least fall back to a raw append (like `_log` does on lines 60-62) so the record isn't lost. Silently swallowing the exception guarantees that the exact failure mode it was designed to stop (missing instructions) will happen again, just invisibly. 

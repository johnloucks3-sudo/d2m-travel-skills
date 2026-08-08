# AG Sanity Check — OpenCode Diagnosis & Instructor Mode Fix

**BLUF:** Diagnosis is solid; proposed scoped `--auto` + dedicated prompt fix is sound, with one cleaner staging alternative to consider.

## Findings & Evaluation
- **Diagnosis Confirmed:** OpenCode default security sandbox blocks writes outside workspace root without `--auto`. The `oc_worker.py` wrapper caused prompt collision ("write summary to out_file" vs target task) and false `rc=0` completion without inspecting mutations.
- **Scoped `--auto` Safety:** Safe when strictly bounded by Silver pre/post-gates, explicit file allowlists, and specific invocation flags. Never make `--auto` global.
- **Cleaner Pattern (Staging/Patch):** Alternatively, standard async worker practice has OC output diffs/patches or staging files *inside* repo; orchestrator applies and verifies externally. Keeps OC in-repo sandbox intact.
- **Recommendation:** Proceed with scoped `--auto` for reviewed Instructor Mode build lanes using dedicated prompt framing, verified by Silver post-gate (`grep -c`).

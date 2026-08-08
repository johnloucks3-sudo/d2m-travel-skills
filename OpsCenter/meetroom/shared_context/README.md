# shared_context — H3a / H1 file memory (RT-Interop C5)

Home of the RT-Interop schema's shared file memory (Commander decision
2026-08-08: shared-context pointer home is OC-determined):

- **H3a file memory:** `{topic}.jsonl` — append-only shared memory across
  seats. Plain-text JSONL ONLY (SQLite REFUTED by AG: git conflicts, WAL
  lock contention, breaks 0-token human review).
- **H1 session pointers:** `{topic}_pointer.json` — one durable pointer that
  lets another engine resume a workitem without context replay.

Rules:
1. JSONL/MD pointers only. No binary, no daemon, no hosted store.
2. Pointer target_state names a verifiable artifact (path/count/ref) so
   peers and Silver can check the claim — H9 gate discipline.
3. Cross-repo/cross-machine pointers `inbound: hold` (isolate-machines parity).
4. Body discipline unchanged: point, don't reprint (RT-RETRO "no reprints").
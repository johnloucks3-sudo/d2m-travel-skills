# COURIER PROTOCOL (NCO WATCHER)

1. **PICKUP:** Monitor every entity's `outbox.md`.
2. **ROUTE:** Read the `target` metadata in the task file.
3. **DEPOSIT:** Move file to `target/inbox.md`.
4. **LOG:** Append entry to `collaboration/movement_log.md`:
   `[TIMESTAMP] | [DOCUMENT_ID] | FROM: [ENTITY] | TO: [ENTITY] | STATUS: [MOVED/COMPLETE]`
5. **ARCHIVE:** If `status: COMPLETE` + `target: COMPLETE`, move file to `collaboration/COMPLETE/`.

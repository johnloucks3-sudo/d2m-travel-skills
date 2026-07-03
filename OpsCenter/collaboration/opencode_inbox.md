# OC Inbox — RELAY v2

Tasks are stored in `OpsCenter/task_db.sqlite` (WAL SQLite).

**Query tasks:**
```bash
# Last 10 tasks
python3 -c "from OpsCenter.task_queue import get_db; conn=get_db().__enter__(); [print(dict(r)) for r in conn.execute('SELECT id,status,content FROM tasks ORDER BY created_at DESC LIMIT 10').fetchall()]"

# Specific task
python3 -c "from OpsCenter.email_c2 import _db_get; print(_db_get('RELAY-XXXXXXXX'))"
```

**Trigger a task:** Send email to d2mconcierge@gmail.com  
Subject: `[WING] <what you want done>`

**Chat commands:** `[WING] LIST` · `[WING] STATUS <id>` · `[WING] ABORT <id>` · `[WING] BLACKBOARD` · `[WING] BRIEF`

*Archive: `collaboration/archive/opencode_inbox_20260702.md` (340KB, 6753 lines)*

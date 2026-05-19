-- AI Infrastructure Cost Dashboard — Schema
-- Opus architectural design, Haiku implementation
-- Phase 0: Database Schema

CREATE TABLE IF NOT EXISTS claude_events (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL,
  ts_start TEXT NOT NULL,
  ts_end TEXT NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER, output_tokens INTEGER,
  cache_read_tokens INTEGER, cache_create_tokens INTEGER,
  effective_tokens INTEGER,
  source_file TEXT,
  inserted_at TEXT DEFAULT (datetime('now')),
  UNIQUE(session_id, ts_start)
);

CREATE TABLE IF NOT EXISTS openrouter_snapshots (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  total_usage REAL,
  usage_daily REAL,
  usage_weekly REAL,
  usage_monthly REAL,
  limit_amount REAL,
  limit_remaining REAL,
  total_credits REAL,
  is_free_tier BOOLEAN,
  UNIQUE(ts)
);

CREATE TABLE IF NOT EXISTS claude_windows (
  window_start TEXT PRIMARY KEY,
  window_end TEXT NOT NULL,
  effective_tokens INTEGER NOT NULL,
  pct_consumed REAL NOT NULL,
  closed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS daily_rollups (
  date TEXT PRIMARY KEY,
  claude_effective_tokens INTEGER,
  claude_windows_used REAL,
  openrouter_usd REAL,
  openrouter_requests INTEGER,
  total_estimated_usd REAL
);

CREATE INDEX IF NOT EXISTS idx_or_ts ON openrouter_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_claude_ts ON claude_events(ts_start);

CREATE TABLE IF NOT EXISTS poe_snapshots (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  points_balance INTEGER,
  points_used_today INTEGER,
  points_used_week INTEGER,
  points_used_month INTEGER,
  model_gemini_flash INTEGER DEFAULT 0,
  model_kimi_k2 INTEGER DEFAULT 0,
  estimated_cost_usd REAL,
  source TEXT DEFAULT 'log',
  UNIQUE(ts)
);
CREATE INDEX IF NOT EXISTS idx_poe_ts ON poe_snapshots(ts);

CREATE TABLE IF NOT EXISTS plan_snapshots (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  plan_name TEXT DEFAULT 'Max',
  monthly_spent REAL,
  monthly_limit REAL,
  monthly_pct REAL,
  session_pct REAL,
  weekly_all_pct REAL,
  weekly_sonnet_pct REAL,
  balance REAL,
  auto_reload BOOLEAN DEFAULT 0,
  month_resets TEXT,
  UNIQUE(ts)
);

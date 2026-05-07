-- creator-outreach-core unified CRM schema
-- Applies idempotently via CREATE TABLE IF NOT EXISTS

CREATE TABLE IF NOT EXISTS creators (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  handle TEXT NOT NULL,
  profile_url TEXT NOT NULL,
  display_name TEXT,
  bio TEXT,
  category TEXT,
  followers_count INTEGER,
  avg_views INTEGER,
  engagement_rate REAL,
  region TEXT,
  language TEXT,
  contact_email TEXT,
  website TEXT,
  link_in_bio TEXT,
  source TEXT,
  source_url TEXT,
  discovered_at TEXT,
  last_enriched_at TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  score INTEGER,
  risk_level TEXT,
  risk_flags TEXT,
  notes TEXT,
  personalization TEXT,
  UNIQUE(platform, handle)
);

CREATE TABLE IF NOT EXISTS outreach_events (
  id TEXT PRIMARY KEY,
  creator_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  channel TEXT,
  subject TEXT,
  body_path TEXT,
  message_id TEXT,
  thread_id TEXT,
  sent_at TEXT,
  replied_at TEXT,
  next_followup_at TEXT,
  status TEXT,
  raw_metadata TEXT,
  FOREIGN KEY (creator_id) REFERENCES creators(id)
);

CREATE TABLE IF NOT EXISTS suppression_list (
  id TEXT PRIMARY KEY,
  platform TEXT,
  handle TEXT,
  email TEXT,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

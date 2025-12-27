# Database Migrations

This folder contains all SQL migrations for the Serene database schema.

## Migration Order

Migrations should be run in numerical order. Each migration is **idempotent** - safe to re-run.

| # | File | Description |
|---|------|-------------|
| 001 | `001_relationship_members.sql` | Adds relationship_members table for linking users to relationships |
| 002 | `002_multi_tenancy.sql` | Adds couple_profiles table for multi-tenancy support |
| 003 | `003_gender_neutral.sql` | Updates gendered field names to partner_a/partner_b |
| 004 | `004_security_hardening.sql` | Enables RLS policies, adds audit_logs and rate_limits tables |
| 005 | `005_gottman_analytics.sql` | Adds Gottman relationship analysis framework (Four Horsemen, repair tracking) |
| 006 | `006_conflict_triggers.sql` | Adds trigger_phrases, unmet_needs, conflict_enrichment tables |
| 007 | `007_add_sequence_number.sql` | Adds sequence_number column to rant_messages for ordering |

## Base Schema

The base schema (`migration.sql` in parent folder) must be run FIRST before any numbered migrations. It creates the core tables:
- `users`
- `relationships`
- `conflicts`
- `rant_messages`
- `mediator_sessions`
- `mediator_messages`
- `profiles`
- `cycle_events`
- `memorable_dates`
- `intimacy_events`
- `conflict_analysis`
- `repair_plans`
- `chat_messages`

## Running Migrations

### Option 1: Supabase SQL Editor
1. Open Supabase Dashboard > SQL Editor
2. Run `../migration.sql` first (if tables don't exist)
3. Run each numbered migration in order

### Option 2: psql CLI
```bash
# Connect to database
psql $DATABASE_URL

# Run base schema
\i migration.sql

# Run numbered migrations in order
\i migrations/001_relationship_members.sql
\i migrations/002_multi_tenancy.sql
# ... etc
```

## Notes

- All migrations use `IF NOT EXISTS` / `IF EXISTS` for idempotency
- RLS is enabled on all tables with public access policies (MVP mode)
- Foreign keys cascade deletes to maintain data integrity
- Indexes are created for common query patterns

## Dependencies

- **PostgreSQL 12+** with `uuid-ossp` extension
- Migrations assume `relationships` and `conflicts` tables exist from base schema

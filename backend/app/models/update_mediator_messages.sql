-- =====================================================================
-- CLEAN MIGRATION: Drop and Recreate Mediator Messages Table
-- WARNING: This will DELETE all existing mediator messages data!
-- =====================================================================

-- Step 1: Drop existing mediator_messages table if it exists
DROP TABLE IF EXISTS mediator_messages CASCADE;

-- Step 2: Drop existing mediator_sessions table if it exists
DROP TABLE IF EXISTS mediator_sessions CASCADE;

-- Step 3: Recreate mediator_sessions table (needed for foreign key)
CREATE TABLE mediator_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    session_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_ended_at TIMESTAMP WITH TIME ZONE,
    partner_id TEXT, -- Optional: "partner_a" or "partner_b" if known
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for mediator_sessions
CREATE INDEX idx_mediator_sessions_conflict ON mediator_sessions(conflict_id);
CREATE INDEX idx_mediator_sessions_started_at ON mediator_sessions(session_started_at DESC);

-- Enable RLS for mediator_sessions
ALTER TABLE mediator_sessions ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for mediator_sessions
CREATE POLICY "Allow public access to mediator_sessions" ON mediator_sessions FOR ALL USING (true);

-- Step 4: Create NEW mediator_messages table with JSON conversation storage
CREATE TABLE mediator_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES mediator_sessions(id) ON DELETE CASCADE UNIQUE, -- UNIQUE: one row per session
    content JSONB NOT NULL DEFAULT '[]'::jsonb, -- Store entire conversation as JSON array
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- Track last update
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Step 5: Create indexes for performance
CREATE INDEX idx_mediator_messages_session ON mediator_messages(session_id);
CREATE INDEX idx_mediator_messages_created_at ON mediator_messages(created_at ASC);
CREATE INDEX idx_mediator_messages_updated_at ON mediator_messages(updated_at DESC);

-- Step 6: Enable RLS
ALTER TABLE mediator_messages ENABLE ROW LEVEL SECURITY;

-- Step 7: Create RLS policy
CREATE POLICY "Allow public access to mediator_messages" ON mediator_messages FOR ALL USING (true);

-- =====================================================================
-- Migration Complete!
-- 
-- New Structure:
-- - One row per session in mediator_messages
-- - Entire conversation stored in 'content' JSONB column
-- - Format: [{"role": "user", "content": "...", "timestamp": "..."}, ...]
-- =====================================================================

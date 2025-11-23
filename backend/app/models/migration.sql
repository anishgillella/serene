-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create relationships table (if not exists)
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    partner_a_name TEXT,
    partner_b_name TEXT
);

-- Create conflicts table
CREATE TABLE IF NOT EXISTS conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    transcript_path TEXT, -- Path in Supabase Storage (e.g., "relationship_id/conflict_id.json")
    status TEXT DEFAULT 'active', -- active, processing, completed
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create RLS policies (simplified for MVP)
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE conflicts ENABLE ROW LEVEL SECURITY;

-- Create rant_messages table for storing private rant conversation history
CREATE TABLE IF NOT EXISTS rant_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL, -- "partner_a" or "partner_b"
    role TEXT NOT NULL, -- "user" or "assistant"
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_rant_messages_conflict_partner ON rant_messages(conflict_id, partner_id);
CREATE INDEX IF NOT EXISTS idx_rant_messages_created_at ON rant_messages(created_at DESC);

-- Create RLS policies
ALTER TABLE rant_messages ENABLE ROW LEVEL SECURITY;

-- Allow public access for MVP (since we don't have auth yet)
CREATE POLICY "Allow public access to relationships" ON relationships FOR ALL USING (true);
CREATE POLICY "Allow public access to conflicts" ON conflicts FOR ALL USING (true);
CREATE POLICY "Allow public access to rant_messages" ON rant_messages FOR ALL USING (true);

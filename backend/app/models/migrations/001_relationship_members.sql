-- Migration 001: Add relationship_members table for multi-tenancy
-- This table links users to relationships and enables partner invitation flow

-- Create relationship_members table to link users to relationships
CREATE TABLE IF NOT EXISTS relationship_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'partner' CHECK (role IN ('partner', 'invited')),
    display_name TEXT,
    invited_by UUID REFERENCES users(id),
    invitation_token TEXT UNIQUE,
    invitation_email TEXT,
    invitation_status TEXT DEFAULT 'accepted' CHECK (invitation_status IN ('pending', 'accepted', 'rejected', 'expired')),
    invitation_sent_at TIMESTAMP WITH TIME ZONE,
    invitation_expires_at TIMESTAMP WITH TIME ZONE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, relationship_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_relationship_members_user
    ON relationship_members(user_id);
CREATE INDEX IF NOT EXISTS idx_relationship_members_relationship
    ON relationship_members(relationship_id);
CREATE INDEX IF NOT EXISTS idx_relationship_members_token
    ON relationship_members(invitation_token)
    WHERE invitation_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_relationship_members_email
    ON relationship_members(invitation_email)
    WHERE invitation_email IS NOT NULL;

-- Add created_by tracking to conflicts (optional, for audit trail)
ALTER TABLE conflicts
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES users(id);

-- Enable RLS on relationship_members
ALTER TABLE relationship_members ENABLE ROW LEVEL SECURITY;

-- Allow public access for MVP (will be tightened in Phase 5)
CREATE POLICY "Allow public access to relationship_members"
    ON relationship_members FOR ALL USING (true);

-- Seed test users for Adrian/Elara (preserves existing data)
-- These link to the existing default relationship ID
INSERT INTO users (id, auth0_id, email, name, created_at)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'test|adrian', 'adrian@test.com', 'Adrian Malhotra', NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'test|elara', 'elara@test.com', 'Elara Voss', NOW())
ON CONFLICT (auth0_id) DO NOTHING;

-- Link existing default relationship to test users
INSERT INTO relationship_members (user_id, relationship_id, role, display_name, invitation_status, joined_at)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '00000000-0000-0000-0000-000000000000', 'partner', 'Adrian', 'accepted', NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '00000000-0000-0000-0000-000000000000', 'partner', 'Elara', 'accepted', NOW())
ON CONFLICT (user_id, relationship_id) DO NOTHING;

-- Update relationships table partner references
UPDATE relationships
SET
    partner_a_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    partner_b_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    partner_a_name = 'Adrian',
    partner_b_name = 'Elara'
WHERE id = '00000000-0000-0000-0000-000000000000';

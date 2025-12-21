-- Phase 2: Multi-Tenancy Core Migration
-- This migration enables multiple couples to use Serene without authentication

-- Create couple_profiles table to store partner names and relationship configuration
CREATE TABLE IF NOT EXISTS couple_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_a_name TEXT NOT NULL,
    partner_b_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_couple_profiles_relationship UNIQUE (relationship_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_couple_profiles_relationship ON couple_profiles(relationship_id);

-- Enable RLS
ALTER TABLE couple_profiles ENABLE ROW LEVEL SECURITY;

-- Allow public access for MVP (no auth yet)
CREATE POLICY "Allow public access to couple_profiles" ON couple_profiles FOR ALL USING (true);

-- Update relationships table to ensure partner names are stored
-- (partner_a_name and partner_b_name already exist from migration.sql)

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for couple_profiles
DROP TRIGGER IF EXISTS update_couple_profiles_updated_at ON couple_profiles;
CREATE TRIGGER update_couple_profiles_updated_at
    BEFORE UPDATE ON couple_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed Adrian & Elara as default test data (keeps backward compatibility)
-- First ensure the default relationship exists
INSERT INTO relationships (id, partner_a_name, partner_b_name, created_at)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Adrian',
    'Elara',
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    partner_a_name = COALESCE(relationships.partner_a_name, 'Adrian'),
    partner_b_name = COALESCE(relationships.partner_b_name, 'Elara');

-- Create couple_profile for default relationship
INSERT INTO couple_profiles (relationship_id, partner_a_name, partner_b_name)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Adrian',
    'Elara'
)
ON CONFLICT (relationship_id) DO NOTHING;

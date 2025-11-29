
-- Create partner_profiles table for structured onboarding data
CREATE TABLE IF NOT EXISTS partner_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL, -- "partner_a" or "partner_b"
    name TEXT,
    role TEXT, -- "boyfriend", "girlfriend"
    age INTEGER,
    communication_style TEXT,
    stress_triggers TEXT[],
    soothing_mechanisms TEXT[],
    background_story TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(relationship_id, partner_id)
);

-- Create relationship_profiles table for shared relationship data
CREATE TABLE IF NOT EXISTS relationship_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE UNIQUE,
    recurring_arguments TEXT[],
    shared_goals TEXT[],
    relationship_dynamic TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_partner_profiles_relationship ON partner_profiles(relationship_id);
CREATE INDEX IF NOT EXISTS idx_relationship_profiles_relationship ON relationship_profiles(relationship_id);

-- Enable RLS
ALTER TABLE partner_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationship_profiles ENABLE ROW LEVEL SECURITY;

-- Allow public access for MVP (Check if policy exists first to avoid error, or drop and recreate)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'partner_profiles' AND policyname = 'Allow public access to partner_profiles'
    ) THEN
        CREATE POLICY "Allow public access to partner_profiles" ON partner_profiles FOR ALL USING (true);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'relationship_profiles' AND policyname = 'Allow public access to relationship_profiles'
    ) THEN
        CREATE POLICY "Allow public access to relationship_profiles" ON relationship_profiles FOR ALL USING (true);
    END IF;
END
$$;

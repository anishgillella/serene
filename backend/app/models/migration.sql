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
    transcript_path TEXT, -- S3 URL or path (e.g., "s3://bucket/transcripts/relationship_id/conflict_id.json" or "transcripts/relationship_id/conflict_id.json")
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

-- Create mediator_sessions table for storing Luna mediator conversation history
CREATE TABLE IF NOT EXISTS mediator_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    session_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_ended_at TIMESTAMP WITH TIME ZONE,
    partner_id TEXT, -- Optional: "partner_a" or "partner_b" if known
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create mediator_messages table for storing individual messages in mediator sessions
CREATE TABLE IF NOT EXISTS mediator_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES mediator_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- "user" or "assistant" (Luna)
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_mediator_sessions_conflict ON mediator_sessions(conflict_id);
CREATE INDEX IF NOT EXISTS idx_mediator_sessions_started_at ON mediator_sessions(session_started_at DESC);
CREATE INDEX IF NOT EXISTS idx_mediator_messages_session ON mediator_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_mediator_messages_created_at ON mediator_messages(created_at ASC);

-- Create RLS policies
ALTER TABLE mediator_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE mediator_messages ENABLE ROW LEVEL SECURITY;

-- Create profiles table for storing profile PDF metadata
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    pdf_type TEXT NOT NULL, -- "boyfriend_profile", "girlfriend_profile", "handbook"
    partner_id TEXT, -- Optional: "partner_a" or "partner_b" for profile PDFs
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL, -- S3 URL or path (e.g., "s3://bucket/profiles/relationship_id/profile_id.pdf" or "profiles/relationship_id/profile_id.pdf")
    pdf_id UUID NOT NULL, -- Reference to Pinecone vector ID
    extracted_text_length INTEGER, -- Length of extracted text
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_relationship ON profiles(relationship_id);
CREATE INDEX IF NOT EXISTS idx_profiles_pdf_type ON profiles(pdf_type);
CREATE INDEX IF NOT EXISTS idx_profiles_uploaded_at ON profiles(uploaded_at DESC);

-- Create cycle_events table for tracking menstrual/cycle events (user-logged only)
CREATE TABLE IF NOT EXISTS cycle_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL, -- "partner_a" or "partner_b"
    event_type TEXT NOT NULL, -- "period_start", "period_end", "symptom_log", "mood_log"
    event_date DATE NOT NULL, -- The actual date of the event
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- When it was logged
    notes TEXT,
    cycle_day INTEGER, -- Day of cycle (1 = first day of period)
    symptoms TEXT[], -- Array of symptoms: ["cramps", "mood_swings", "headache"]
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for cycle_events
CREATE INDEX IF NOT EXISTS idx_cycle_events_partner ON cycle_events(partner_id);
CREATE INDEX IF NOT EXISTS idx_cycle_events_timestamp ON cycle_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_cycle_events_type ON cycle_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cycle_events_date ON cycle_events(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_cycle_events_relationship ON cycle_events(relationship_id);

-- Create memorable_dates table for anniversaries, birthdays, milestones
CREATE TABLE IF NOT EXISTS memorable_dates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- "anniversary", "birthday", "first_date", "engagement", "wedding", "milestone", "custom"
    title TEXT NOT NULL, -- "First Anniversary", "Elara's Birthday", "First Date"
    description TEXT, -- Optional description/notes
    event_date DATE NOT NULL, -- The date of the event
    is_recurring BOOLEAN DEFAULT true, -- Annual recurrence
    reminder_days INTEGER DEFAULT 7, -- Days before to remind
    color_tag TEXT DEFAULT '#f59e0b', -- UI color (gold default for anniversaries)
    partner_id TEXT, -- Optional: which partner it relates to (for birthdays)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for memorable_dates
CREATE INDEX IF NOT EXISTS idx_memorable_dates_relationship ON memorable_dates(relationship_id);
CREATE INDEX IF NOT EXISTS idx_memorable_dates_date ON memorable_dates(event_date);
CREATE INDEX IF NOT EXISTS idx_memorable_dates_type ON memorable_dates(event_type);
CREATE INDEX IF NOT EXISTS idx_memorable_dates_recurring ON memorable_dates(is_recurring);


-- Create intimacy_events table for tracking intimacy moments
CREATE TABLE IF NOT EXISTS intimacy_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    initiator_partner_id TEXT, -- "partner_a" or "partner_b"
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for intimacy_events
CREATE INDEX IF NOT EXISTS idx_intimacy_events_relationship ON intimacy_events(relationship_id);
CREATE INDEX IF NOT EXISTS idx_intimacy_events_timestamp ON intimacy_events(timestamp DESC);

-- Create conflict_analysis table for storing analysis results
CREATE TABLE IF NOT EXISTS conflict_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    analysis_path TEXT NOT NULL, -- S3 URL or path (e.g., "s3://bucket/analysis/relationship_id/conflict_id_analysis.json" or "analysis/relationship_id/conflict_id_analysis.json")
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for conflict_analysis
CREATE INDEX IF NOT EXISTS idx_conflict_analysis_conflict ON conflict_analysis(conflict_id);
CREATE INDEX IF NOT EXISTS idx_conflict_analysis_relationship ON conflict_analysis(relationship_id);
CREATE INDEX IF NOT EXISTS idx_conflict_analysis_analyzed_at ON conflict_analysis(analyzed_at DESC);

-- Create repair_plans table for storing repair plan results
CREATE TABLE IF NOT EXISTS repair_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_requesting TEXT NOT NULL, -- "partner_a" or "partner_b"
    plan_path TEXT NOT NULL, -- S3 URL or path (e.g., "s3://bucket/repair_plans/relationship_id/conflict_id_repair_partner_a.json" or "repair_plans/relationship_id/conflict_id_repair_partner_a.json")
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for repair_plans
CREATE INDEX IF NOT EXISTS idx_repair_plans_conflict ON repair_plans(conflict_id);
CREATE INDEX IF NOT EXISTS idx_repair_plans_relationship ON repair_plans(relationship_id);
CREATE INDEX IF NOT EXISTS idx_repair_plans_partner ON repair_plans(partner_requesting);
CREATE INDEX IF NOT EXISTS idx_repair_plans_generated_at ON repair_plans(generated_at DESC);

-- Create RLS policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE intimacy_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE conflict_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE repair_plans ENABLE ROW LEVEL SECURITY;

-- Allow public access for MVP (since we don't have auth yet)
CREATE POLICY "Allow public access to relationships" ON relationships FOR ALL USING (true);
CREATE POLICY "Allow public access to conflicts" ON conflicts FOR ALL USING (true);
CREATE POLICY "Allow public access to rant_messages" ON rant_messages FOR ALL USING (true);
CREATE POLICY "Allow public access to mediator_sessions" ON mediator_sessions FOR ALL USING (true);
CREATE POLICY "Allow public access to mediator_messages" ON mediator_messages FOR ALL USING (true);
CREATE POLICY "Allow public access to profiles" ON profiles FOR ALL USING (true);
CREATE POLICY "Allow public access to cycle_events" ON cycle_events FOR ALL USING (true);
CREATE POLICY "Allow public access to intimacy_events" ON intimacy_events FOR ALL USING (true);
CREATE POLICY "Allow public access to memorable_dates" ON memorable_dates FOR ALL USING (true);

-- Enable RLS on new tables
ALTER TABLE memorable_dates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to conflict_analysis" ON conflict_analysis FOR ALL USING (true);
CREATE POLICY "Allow public access to repair_plans" ON repair_plans FOR ALL USING (true);

-- Migration: Add sequence_number column to rant_messages table
-- This provides explicit ordering for transcript messages to preserve conversation flow

-- Add the column if it doesn't exist
ALTER TABLE rant_messages ADD COLUMN IF NOT EXISTS sequence_number INTEGER DEFAULT 0;

-- Create index for efficient ordering
CREATE INDEX IF NOT EXISTS idx_rant_messages_sequence ON rant_messages(conflict_id, sequence_number);

-- Optional: Update existing records to have sequence numbers based on created_at order
-- This fixes the ordering for any existing conflicts
WITH numbered AS (
    SELECT
        id,
        ROW_NUMBER() OVER (PARTITION BY conflict_id ORDER BY created_at) - 1 as new_seq
    FROM rant_messages
)
UPDATE rant_messages
SET sequence_number = numbered.new_seq
FROM numbered
WHERE rant_messages.id = numbered.id;

-- Verify the migration
SELECT 'Migration complete. Sample data:' as status;
SELECT conflict_id, partner_id, sequence_number, LEFT(content, 50) as content_preview
FROM rant_messages
ORDER BY conflict_id, sequence_number
LIMIT 10;

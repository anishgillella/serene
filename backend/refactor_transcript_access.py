#!/usr/bin/env python3
"""
Script to refactor remaining Pinecone transcript calls to PostgreSQL
"""
import re

# Read the file
with open('/Users/anishgillella/Desktop/Stuff/Projects/Convo Mediator/serene/backend/app/routes/post_fight.py', 'r') as f:
    content = f.read()

# Pattern 1: Simple transcript retrieval from Pinecone
pattern1 = re.compile(
    r'transcript_result = pinecone_service\.get_by_conflict_id\(\s*'
    r'conflict_id=conflict_id,\s*'
    r'namespace="transcripts"\s*\)',
    re.MULTILINE
)

# Replace with PostgreSQL call
replacement1 = 'transcript_data = db_service.get_conflict_transcript(conflict_id)'

# Apply replacement
content = pattern1.sub(replacement1, content)

# Pattern 2: Replace transcript_result.metadata access
content = re.sub(
    r'transcript_result\.metadata\.get\("transcript_text", ""\)',
    'transcript_data.get("transcript_text", "") if transcript_data else ""',
    content
)

#Pattern 3: Replace transcript_result checks
content = re.sub(
    r'if transcript_result and transcript_result\.metadata:',
    'if transcript_data:',
    content
)

# Write back
with open('/Users/anishgillella/Desktop/Stuff/Projects/Convo Mediator/serene/backend/app/routes/post_fight.py', 'w') as f:
    f.write(content)

print("✅ Refactoring complete!")
print("   - Replaced pinecone_service.get_by_conflict_id with db_service.get_conflict_transcript")
print("   - Updated metadata access patterns")
print("   - Updated conditional checks")

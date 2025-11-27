#!/bin/bash

# Reset and seed database script

echo "🔄 Resetting database and seeding fresh data..."
echo ""

# Step 1: Clean database
echo "Step 1: Cleaning database..."
python backend/sample_data/clean_database.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to clean database"
    exit 1
fi

# Step 2: Seed base data
echo "Step 2: Seeding base data..."
python backend/sample_data/seed_data.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to seed base data"
    exit 1
fi

# Step 3: Add rant messages (Optional now as seed_data does it, but keeping for completeness if needed)
# echo "Step 3: Adding rant messages..."
# python backend/sample_data/add_more_rants.py

# Step 4: Seed Pinecone
echo "Step 3: Seeding Pinecone..."
python backend/sample_data/seed_pinecone.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to seed Pinecone"
    exit 1
fi

# Step 5: Verify data
echo ""
echo "Step 4: Verifying seeded data..."
python backend/sample_data/check_seeded_data.py
python backend/sample_data/count_data.py

echo ""
echo "✅ Database reset and seeded successfully!"

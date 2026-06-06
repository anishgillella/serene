#!/usr/bin/env python3
"""
Bootstrap Moss indexes for Serene Luna voice agent.

Usage:
    cd backend && python scripts/create_moss_indexes.py

Requires MOSS_PROJECT_ID and MOSS_PROJECT_KEY in .env (repo root).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    from moss import DocumentInfo, MossClient
except ImportError:
    print("Install moss: pip install 'moss>=1.4'")
    sys.exit(1)

KNOWLEDGE_SEED = [
    {
        "id": "kb-four-horsemen",
        "text": "Q: What are the Four Horsemen in Gottman method? "
        "A: Criticism, contempt, defensiveness, and stonewalling. "
        "They predict relationship distress when they appear frequently during conflict.",
        "metadata": {"category": "gottman", "topic": "four-horsemen"},
    },
    {
        "id": "kb-repair-attempt",
        "text": "Q: What is a repair attempt? "
        "A: Any statement or action that de-escalates tension during conflict — "
        "humor, apology, affection, or taking responsibility. "
        "Success depends more on how the partner receives the repair than how it's delivered.",
        "metadata": {"category": "gottman", "topic": "repair"},
    },
    {
        "id": "kb-bids",
        "text": "Q: What are bids for connection? "
        "A: Small attempts to get attention, affection, or support. "
        "Turning toward bids builds trust; turning away erodes it over time.",
        "metadata": {"category": "gottman", "topic": "bids"},
    },
    {
        "id": "kb-soft-startup",
        "text": "Q: What is a soft startup? "
        "A: Raising a concern without blame — describe your feeling, "
        "the situation, and what you need. Avoid 'you always' or 'you never' language.",
        "metadata": {"category": "gottman", "topic": "communication"},
    },
    {
        "id": "kb-luna-role",
        "text": "Q: What is Luna's role in Serene? "
        "A: Luna is a warm, casual relationship mediator — like a trusted friend, not a therapist. "
        "She helps partners understand each other, find repair strategies, and see patterns in past conflicts.",
        "metadata": {"category": "serene", "topic": "luna"},
    },
]


async def main():
    project_id = os.getenv("MOSS_PROJECT_ID")
    project_key = os.getenv("MOSS_PROJECT_KEY")
    if not project_id or not project_key:
        print("Set MOSS_PROJECT_ID and MOSS_PROJECT_KEY in .env")
        sys.exit(1)

    knowledge_index = os.getenv("MOSS_KNOWLEDGE_INDEX", "serene-knowledge")
    memory_index = os.getenv("MOSS_MEMORY_INDEX", "serene-memory")
    transcripts_index = os.getenv("MOSS_TRANSCRIPTS_INDEX", "serene-transcripts")

    client = MossClient(project_id, project_key)

    knowledge_docs = [
        DocumentInfo(
            id=d["id"],
            text=d["text"],
            metadata={k: str(v) for k, v in d["metadata"].items()},
        )
        for d in KNOWLEDGE_SEED
    ]

    print(f"Creating knowledge index: {knowledge_index}")
    await client.create_index(knowledge_index, knowledge_docs)

    print(f"Creating memory index: {memory_index}")
    await client.create_index(
        memory_index,
        [
            DocumentInfo(
                id="seed-memory",
                text="Serene relationship memory index — stores durable facts per relationship.",
                metadata={"relationship_id": "seed", "category": "seed"},
            )
        ],
    )

    print(f"Creating transcripts index: {transcripts_index}")
    await client.create_index(
        transcripts_index,
        [
            DocumentInfo(
                id="seed-transcript",
                text="Serene conflict transcript index — stores chunked fight transcripts for semantic search.",
                metadata={"relationship_id": "seed", "conflict_id": "seed", "category": "seed"},
            )
        ],
    )

    print("Done. Indexes created:")
    print(json.dumps([knowledge_index, memory_index, transcripts_index], indent=2))


if __name__ == "__main__":
    asyncio.run(main())

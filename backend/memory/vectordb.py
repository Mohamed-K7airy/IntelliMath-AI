from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from pydantic import BaseModel
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    from supabase import create_client, Client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except (ImportError, Exception) as e:
    print(f"⚠️ Supabase init failed: {e}. Memory persistent features are disabled.")
    supabase = None
    Client = None


class EmbeddedMemory(BaseModel):
    user_id: str  # Supports Supabase UUIDs
    memory_text: str
    categories: List[str]
    date: str
    embedding: List[float]


class RetrievedMemory(BaseModel):
    point_id: str
    user_id: str
    memory_text: str
    categories: List[str]
    date: str
    score: float


async def create_memory_collection():
    """
    No-op for Supabase — the table and indexes are created via SQL in the Dashboard.
    Kept for interface compatibility with memory_manager.py.
    """
    print("Memory Collection prepared (Supabase — table already exists)")


async def insert_memories(memories: List[EmbeddedMemory]):
    """Insert one or more memories into the Supabase `memories` table."""
    if not supabase: return

    rows = [
        {
            "user_id": str(m.user_id),
            "memory_text": m.memory_text,
            "categories": m.categories,
            "date": m.date,
            "embedding": m.embedding,
        }
        for m in memories
    ]

    await asyncio.to_thread(
        lambda: supabase.table("memories").insert(rows).execute()
    )


async def search_memories(
    search_vector: List[float],
    user_id: str,
    categories: Optional[List[str]] = None,
):
    """
    Search for similar memories using the `match_memories` Postgres function.
    Categories filtering is done in Python after the RPC call for simplicity.
    """
    if not supabase: return []

    result = await asyncio.to_thread(
        lambda: supabase.rpc(
            "match_memories",
            {
                "query_embedding": search_vector,
                "match_user_id": str(user_id),
                "match_count": 5,  # fetch a few extra so we can filter by category
            },
        ).execute()
    )

    rows = result.data or []

    retrieved_memories = []
    for row in rows:
        row_categories = row.get("categories", []) or []

        # Optional category filter
        if categories and len(categories) > 0:
            if not any(cat in row_categories for cat in categories):
                continue

        retrieved_memories.append(
            RetrievedMemory(
                point_id=str(row["id"]),
                user_id=row["user_id"],
                memory_text=row["memory_text"],
                categories=row_categories,
                date=row.get("date", ""),
                score=row.get("similarity", 0.0),
            )
        )

    # Only return top 2 after filtering
    return retrieved_memories[:2]


async def delete_user_records(user_id):
    """Delete all memories for a given user."""
    if not supabase: return
    await asyncio.to_thread(
        lambda: supabase.table("memories")
        .delete()
        .eq("user_id", str(user_id))
        .execute()
    )


async def delete_records(point_ids):
    """Delete specific memory records by their UUIDs."""
    if not supabase: return
    for pid in point_ids:
        await asyncio.to_thread(
            lambda pid=pid: supabase.table("memories")
            .delete()
            .eq("id", pid)
            .execute()
        )


async def fetch_all_user_records(user_id):
    """Fetch all memories for a given user."""
    if not supabase: return []
    result = await asyncio.to_thread(
        lambda: supabase.table("memories")
        .select("id, user_id, memory_text, categories, date")
        .eq("user_id", str(user_id))
        .execute()
    )

    retrieved_memories = []
    for row in result.data or []:
        retrieved_memories.append(
            RetrievedMemory(
                point_id=str(row["id"]),
                user_id=row["user_id"],
                memory_text=row["memory_text"],
                categories=row.get("categories", []) or [],
                date=row.get("date", ""),
                score=1.0,
            )
        )
    return retrieved_memories


async def get_all_categories(user_id):
    """Get all unique categories across a user's memories."""
    if not supabase: return []
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table("memories")
            .select("categories")
            .eq("user_id", str(user_id))
            .execute()
        )

        unique_categories = set()
        for row in result.data or []:
            cats = row.get("categories", []) or []
            for cat in cats:
                unique_categories.add(cat)

        return list(unique_categories)
    except Exception:
        return []


def stringify_retrieved_point(retrieved_memory: RetrievedMemory):
    return f"""{retrieved_memory.memory_text} (Categories: {retrieved_memory.categories}) Relevance: {retrieved_memory.score:.2f}"""


if __name__ == "__main__":
    asyncio.run(create_memory_collection())

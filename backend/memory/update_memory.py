import json
import re
import os
from datetime import datetime
from groq import AsyncGroq
from .generate_embeddings import generate_embeddings
from .vectordb import (
    EmbeddedMemory,
    RetrievedMemory,
    delete_records,
    fetch_all_user_records,
    insert_memories,
    search_memories,
)

async def update_memories_agent(
    user_id: str, messages: list[dict], existing_memories: list[RetrievedMemory]
):
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("Error: No GROQ_API_KEY found.")
        return "Error"

    client = AsyncGroq(api_key=groq_api_key)

    # Format existing memories to pass to the agent
    mem_info = "\n".join([
        f"ID {idx}: {m.memory_text} (Categories: {', '.join(m.categories)})" 
        for idx, m in enumerate(existing_memories)
    ])

    # Pass the last 5 messages to understand context
    conv = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages[-5:]])

    prompt = f"""
You are a memory manager. Based on the conversation summary, decide how to update the long-term database to help the AI remember important context about the user's learning progress, past answers, and traits.

Existing memories:
{mem_info if mem_info else "None"}

Conversation:
{conv}

Actions meaning:
- ADD: add new memories if the user introduced new concepts, preferences, or mistakes.
- UPDATE: update an existing memory with richer or corrected information.
- DELETE: remove memories that are obsolete.

Respond ONLY with a JSON array of actions. Actions can be:
- {{"action": "add", "memory_text": "text format", "categories": ["category"]}}
- {{"action": "update", "memory_id": 0, "memory_text": "new text", "categories": ["category"]}}
- {{"action": "delete", "memory_id": 0}}

If no changes are needed, return an empty array [].
Respond ONLY in valid JSON. No markdown backticks, no explanations.
"""
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        reply = response.choices[0].message.content.strip()
        # ✅ FIX (S-15): Robust backtick stripping using regex
        reply = re.sub(r'^```(?:json)?\s*', '', reply)
        reply = re.sub(r'\s*```\s*$', '', reply)
            
        actions = json.loads(reply)
        
        if not actions:
            return "No action done"
            
        added_count = 0
        updated_count = 0
        deleted_count = 0
            
        for action in actions:
            act = action.get("action")
            if act == "add":
                text = action.get("memory_text")
                cats = action.get("categories", [])
                if text:
                    emb = await generate_embeddings([text])
                    await insert_memories([
                        EmbeddedMemory(
                            user_id=user_id,
                            memory_text=text,
                            categories=cats,
                            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            embedding=emb[0]
                        )
                    ])
                    added_count += 1
            elif act == "update":
                m_id = action.get("memory_id")
                text = action.get("memory_text")
                cats = action.get("categories", [])
                if m_id is not None and 0 <= m_id < len(existing_memories) and text:
                    point_id = existing_memories[m_id].point_id
                    await delete_records([point_id])
                    emb = await generate_embeddings([text])
                    await insert_memories([
                        EmbeddedMemory(
                            user_id=user_id,
                            memory_text=text,
                            categories=cats,
                            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            embedding=emb[0]
                        )
                    ])
                    updated_count += 1
            elif act == "delete":
                m_id = action.get("memory_id")
                if m_id is not None and 0 <= m_id < len(existing_memories):
                    point_id = existing_memories[m_id].point_id
                    await delete_records([point_id])
                    deleted_count += 1
                    
        return f"Added: {added_count}, Updated: {updated_count}, Deleted: {deleted_count}"
    except Exception as e:
        print(f"Error executing memory agent: {e}")
        return "Error"


async def update_memories(user_id: str, messages: list[dict]):
    try:
        latest_user_message = [x["content"] for x in messages if x["role"] == "user"][-1]
        embedding = (await generate_embeddings([latest_user_message]))[0]

        retrieved_memories = await search_memories(search_vector=embedding, user_id=user_id)

        response = await update_memories_agent(
            user_id=user_id, existing_memories=retrieved_memories, messages=messages
        )
        return response
    except Exception as e:
        print(f"Error updating memory in main wrapper: {e}")
        return "Error updating memory"

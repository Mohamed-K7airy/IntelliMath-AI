import asyncio
try:
    from .memory.vectordb import search_memories, get_all_categories, create_memory_collection, stringify_retrieved_point
    from .memory.update_memory import update_memories
    from .memory.generate_embeddings import generate_embeddings
except ImportError:
    try:
        from memory.vectordb import search_memories, get_all_categories, create_memory_collection, stringify_retrieved_point
        from memory.update_memory import update_memories
        from memory.generate_embeddings import generate_embeddings
    except ImportError:
        from backend.memory.vectordb import search_memories, get_all_categories, create_memory_collection, stringify_retrieved_point
        from backend.memory.update_memory import update_memories
        from backend.memory.generate_embeddings import generate_embeddings

class MemoryManager:
    """
    High-level interface for the IntelliMath-AI memory system.
    """
    
    def __init__(self):
        self.initialized = False

    async def ensure_initialized(self):
        if not self.initialized:
            await create_memory_collection()
            self.initialized = True

    async def get_context(self, user_id: str, query: str) -> str:
        """
        Fetch relevant memories for the user and return them as a formatted string.
        """
        if not user_id:
            return ""
            
        await self.ensure_initialized()
        
        try:
            # Generate embedding for the query
            embeddings = await generate_embeddings([query])
            if not embeddings:
                return ""
                
            search_vector = embeddings[0]
            
            # Search for similar memories
            memories = await search_memories(search_vector, user_id=user_id)
            
            if not memories:
                return ""
                
            context_str = "\n".join([f"- {m.memory_text}" for m in memories])
            return f"\nRelevant user context found in memory:\n{context_str}\n"
        except Exception as e:
            print(f"Error fetching memory context: {e}")
            return ""

    async def learn(self, user_id: str, messages: list):
        """
        Update user memory based on the latest interaction.
        Should be called asynchronously.
        """
        if not user_id or not messages:
            return
            
        await self.ensure_initialized()
        
        try:
            # We pass the last few messages to the extraction agent
            await update_memories(user_id=user_id, messages=messages)
        except Exception as e:
            print(f"Error updating memory: {e}")

    async def get_user_categories(self, user_id: str) -> list:
        await self.ensure_initialized()
        return await get_all_categories(user_id)

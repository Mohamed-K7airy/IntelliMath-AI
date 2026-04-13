import asyncio
import os
from huggingface_hub import AsyncInferenceClient
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# ✅ FIX (W-07): Reuse a single client instance instead of creating one per call
_hf_client = AsyncInferenceClient(api_key=HF_TOKEN) if HF_TOKEN else None

async def generate_embeddings(strings: list[str]):
    if not _hf_client:
        raise RuntimeError("HF_TOKEN is not configured. Cannot generate embeddings.")

    # Feature extraction automatically routes to the right HF backend
    result = await _hf_client.feature_extraction(
        strings, 
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Convert result to list of lists of floats
    if hasattr(result, 'tolist'):
        embeddings = result.tolist()
    else:
        embeddings = result
    
    # Ensure it's always a list of lists (if a single string was passed, it might be 1D)
    if len(embeddings) > 0 and not isinstance(embeddings[0], list):
        embeddings = [embeddings]
        
    return embeddings

if __name__ == "__main__":
    texts = [
        "Hello how are you",
        "I like Machine Learning"
    ]
    print(asyncio.run(generate_embeddings(texts)))

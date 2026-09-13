import os
import json
from dotenv import load_dotenv
from google import genai
from chunker import load_and_chunk_markdown

load_dotenv()
client = genai.Client()

MARKDOWN_DIR = "markdown"
INDEX_FILE = "index.json"
EMBEDDING_MODEL = "gemini-embedding-001"

def embed_batch(texts):
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
    return [item.values for item in result.embeddings]

def build_index():
    chunks = load_and_chunk_markdown(MARKDOWN_DIR)
    texts = [c["text"] for c in chunks]

    embeddings = embed_batch(texts)
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f)

    print("indexed", len(chunks), "chunks from", MARKDOWN_DIR)

if __name__ == "__main__":
    build_index()
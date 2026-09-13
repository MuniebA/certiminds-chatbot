import os

def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - overlap
    return chunks

def load_and_chunk_markdown(markdown_dir):
    all_chunks = []
    for filename in os.listdir(markdown_dir):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(markdown_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        for i, chunk in enumerate(chunk_text(text)):
            all_chunks.append({
                "id": f"{filename}_{i}",
                "source": filename,
                "text": chunk
            })
    return all_chunks
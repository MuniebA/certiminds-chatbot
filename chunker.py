import os

BASE_URL = "https://certiminds.com"

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

def filename_to_url(filename):
    # reverses the crawler's filename logic to recover the real page url
    name = filename.replace(".md", "").replace(".html", "")
    if name == "home":
        return BASE_URL + "/"
    path = name.replace("_", "/")
    return f"{BASE_URL}/{path}"

def load_and_chunk_markdown(markdown_dir):
    all_chunks = []
    for filename in os.listdir(markdown_dir):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(markdown_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        url = filename_to_url(filename)
        for i, chunk in enumerate(chunk_text(text)):
            all_chunks.append({
                "id": f"{filename}_{i}",
                "source": filename,
                "url": url,
                "text": chunk
            })
    return all_chunks
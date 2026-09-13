import json
from chunker import filename_to_url

INDEX_FILE = "index.json"

def migrate():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    for chunk in chunks:
        if "url" not in chunk:
            chunk["url"] = filename_to_url(chunk["source"])

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f)

    print("added url field to", len(chunks), "chunks")

if __name__ == "__main__":
    migrate()
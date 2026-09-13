from bs4 import BeautifulSoup
from markdownify import markdownify as md
import os

INPUT_DIR = "pages"
OUTPUT_DIR = "markdown"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# tags that are noise for a rag index, not actual page content
STRIP_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"]

for filename in os.listdir(INPUT_DIR):
    if not filename.endswith(".html"):
        continue

    filepath = os.path.join(INPUT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # prefer <main> if it exists, otherwise fall back to whole body
    main_content = soup.find("main") or soup.body or soup

    markdown_text = md(str(main_content), heading_style="ATX")

    # collapse repeated blank lines left over after stripping tags
    lines = [line.rstrip() for line in markdown_text.splitlines()]
    cleaned_lines = []
    for line in lines:
        if line == "" and cleaned_lines and cleaned_lines[-1] == "":
            continue
        cleaned_lines.append(line)
    cleaned_markdown = "\n".join(cleaned_lines).strip()

    output_filename = filename.replace(".html", ".md")
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_markdown)

    print("converted", filename, "->", output_filename)

print("done")
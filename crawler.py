import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import os
import time

BASE_URL = "https://certiminds.com/"
DOMAIN = urlparse(BASE_URL).netloc
OUTPUT_DIR = "pages"
LINK_TABLE = "link_table.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

visited = set()
queue = [BASE_URL]
link_rows = []

def normalize(base, href):
    # resolve relative hrefs against the real base url, not a local file path
    resolved = urljoin(base, href)
    # strip fragments and trailing slashes for dedupe
    resolved = resolved.split("#")[0].rstrip("/")
    return resolved

# use normalize on the seed url as well, not the raw string
queue = [normalize(BASE_URL, BASE_URL)]

# in is_same_domain, also reject cloudflare's email obfuscation path
def is_same_domain(url):
    parsed = urlparse(url)
    if "/cdn-cgi/" in parsed.path:
        return False
    return parsed.netloc == DOMAIN

def safe_filename(url):
    path = urlparse(url).path.strip("/") or "home"
    return path.replace("/", "_") + ".html"

while queue:
    url = queue.pop(0)
    if url in visited:
        continue
    visited.add(url)

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("failed to fetch", url, e)
        continue

    filename = safe_filename(url)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    found_links = []
    for a in soup.find_all("a", href=True):
        link = normalize(url, a["href"])
        found_links.append(link)
        if is_same_domain(link) and link not in visited and link not in queue:
            queue.append(link)

    link_rows.append({"page": url, "saved_as": filename, "links_found": len(found_links)})
    print("fetched", url, "-> found", len(found_links), "links")
    time.sleep(0.5)

with open(LINK_TABLE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["page", "saved_as", "links_found"])
    writer.writeheader()
    writer.writerows(link_rows)

print("done. pages visited:", len(visited))
import json
import os
import re

CACHE_FILE = "answer_cache.json"

def normalize_question(question):
    text = question.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_cached_answer(question, cache):
    key = normalize_question(question)
    return cache.get(key)

def store_answer(question, answer, cache):
    key = normalize_question(question)
    cache[key] = answer
    save_cache(cache)
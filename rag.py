import json
import time
import re
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
from cache import load_cache, get_cached_answer, store_answer

load_dotenv()
client = genai.Client()

INDEX_FILE = "index.json"
EMBEDDING_MODEL = "gemini-embedding-001"
# CHAT_MODEL = "gemini-3.5-flash"
# LITE_MODEL = "gemini-flash-lite-latest"

CHAT_MODEL = "gemini-flash-lite-latest"
LITE_MODEL = "gemini-flash-lite-latest"

RELEVANCE_THRESHOLD = 0.35
MAX_CONTEXT_CHUNKS = 5

def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def embed_query(query):
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=query)
    return result.embeddings[0].values

def retrieve_candidates(query, index, top_n=10):
    query_embedding = embed_query(query)
    scored = []
    for chunk in index:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]

def filter_relevant(scored_chunks, threshold=RELEVANCE_THRESHOLD, max_k=MAX_CONTEXT_CHUNKS):
    # dynamic k: keep only chunks above the relevance threshold, capped at max_k
    relevant = [chunk for score, chunk in scored_chunks if score >= threshold]
    return relevant[:max_k]

def get_retry_delay(error, default=30):
    match = re.search(r"retry in ([\d.]+)s", str(error))
    if match:
        return float(match.group(1)) + 1
    return default

def call_with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except errors.ClientError as e:
            if getattr(e, "code", None) != 429 or attempt == max_retries - 1:
                raise
            wait = get_retry_delay(e)
            print("rate limited, waiting", wait, "seconds")
            time.sleep(wait)
        except errors.ServerError as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 * (2 ** attempt)
            print("model overloaded, retrying in", wait, "seconds")
            time.sleep(wait)

def check_intent(query):
    prompt = (
        "You are checking if a user question can be answered using a company website's content. "
        "Reply with exactly YES if the question is clear and specific enough to search for. "
        "Reply with exactly NO if the question is vague, ambiguous, or not really a question. "
        f"Question: {query}"
    )
    response = call_with_retry(lambda: client.models.generate_content(
        model=LITE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0)
    ))
    answer = response.text.strip().upper()
    return answer.startswith("YES")

def generate_answer(query, context_chunks):
    context_text = "\n\n".join(c["text"] for c in context_chunks)
    system_prompt = (
        "You are a chatbot that answers questions about CertiMinds using only the provided context. "
        "The context is written in English. Respond in the same language the user asked their question in "
        "(for example, answer in Arabic if the question was asked in Arabic), translating the relevant "
        "information from the context accurately. "
        "If the answer is not present in the context, say clearly, in the user's language, that the "
        "information is not available on the website. Do not use any outside knowledge."
    )
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0)
    )
    return response.text.strip()

def guardrail_check(answer, context_chunks):
    context_text = "\n\n".join(c["text"] for c in context_chunks)
    prompt = (
        "Context:\n" + context_text + "\n\n"
        "Answer given to the user:\n" + answer + "\n\n"
        "Does the answer rely only on facts present in the context above, "
        "with no invented details? Reply with exactly YES or NO."
    )
    response = client.models.generate_content(
        model=LITE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0)
    )
    return response.text.strip().upper().startswith("YES")

def answer_query(query, index):
    cache = load_cache()
    cached = get_cached_answer(query, cache)
    if cached is not None:
        return cached

    if not check_intent(query):
        return "Could you rephrase or be more specific about your question? / يرجى إعادة صياغة سؤالك أو توضيحه أكثر"

    scored_chunks = retrieve_candidates(query, index)
    relevant_chunks = filter_relevant(scored_chunks)

    if not relevant_chunks:
        return "I could not find information about that on the CertiMinds website. / لم أتمكن من العثور على هذه المعلومة على موقع CertiMinds"

    answer = generate_answer(query, relevant_chunks)

    if not guardrail_check(answer, relevant_chunks):
        return "I could not find reliable information about that on the CertiMinds website. / لم أتمكن من العثور على معلومة موثوقة حول هذا على موقع CertiMinds"

    store_answer(query, answer, cache)
    return answer
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

CHAT_MODEL = "gemini-flash-lite-latest"
LITE_MODEL = "gemini-flash-lite-latest"

RELEVANCE_THRESHOLD = 0.35
MAX_CONTEXT_CHUNKS = 5

INITIAL_SUGGESTIONS = [
    "What does CertiMinds do?",
    "Tell me about the Launchpad program",
    "How can I build a team with CertiMinds?",
    "How do I contact CertiMinds?"
]

def clarification_message():
    return "I'd be happy to help. Could you clarify your question, or pick one of the suggestions below?"

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
    context_parts = []
    for c in context_chunks:
        url = c.get("url", "")
        context_parts.append(f"[Page: {url}]\n{c['text']}")
    context_text = "\n\n".join(context_parts)

    system_prompt = (
        "You are the official CertiMinds website assistant. Answer the user's question "
        "naturally and professionally, as CertiMinds itself would, using only the information "
        "given to you below. "
        "Never mention 'the context', 'the provided text', 'the website says', or similar "
        "meta-references to your source material. Just state the information directly, as fact. "
        "Respond in the same language the user asked their question in. "
        "Each piece of information below is labeled with the full page URL it came from, like "
        "[Page: https://certiminds.com/contact]. When your answer would naturally point the user "
        "to a specific page (booking a call, contacting, applying, viewing a program page), include "
        "that exact full URL directly in your answer as plain text, for example: "
        "'You can book a call here: https://certiminds.com/contact'. "
        "Never output a relative path like /contact - always use the full URL exactly as labeled. "
        "Only include a URL when it is genuinely relevant to the answer, not in every response. "
        "Format your answer for readability: keep paragraphs short (2-3 sentences). "
        "If your answer involves multiple steps or items, put each one on its own separate line, "
        "starting with a number and a period (like '1. Register your interest') or a dash, never "
        "crammed together in a single paragraph. Use **bold** only for short key terms. "
        "If the information is not available, say so clearly and professionally, without "
        "referencing 'the context' - for example: 'That information isn't available right now, "
        "but you can reach out to our team directly for details.' "
        "Do not use any outside knowledge beyond what is given below."
    )
    user_prompt = f"Information:\n{context_text}\n\nQuestion: {query}"

    response = call_with_retry(lambda: client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0)
    ))
    return response.text.strip()

def guardrail_check(answer, context_chunks):
    context_text = "\n\n".join(c["text"] for c in context_chunks)
    prompt = (
        "Context:\n" + context_text + "\n\n"
        "Answer given to the user:\n" + answer + "\n\n"
        "Does the answer rely only on facts present in the context above, "
        "with no invented details? Reply with exactly YES or NO."
    )
    response = call_with_retry(lambda: client.models.generate_content(
        model=LITE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0)
    ))
    return response.text.strip().upper().startswith("YES")

def answer_query(query, index):
    cache = load_cache()
    cached = get_cached_answer(query, cache)
    if cached is not None:
        return cached

    if not check_intent(query):
        return clarification_message()

    scored_chunks = retrieve_candidates(query, index)
    relevant_chunks = filter_relevant(scored_chunks)

    if not relevant_chunks:
        return "That information isn't available on our website right now, but feel free to reach out to our team directly for more details."

    answer = generate_answer(query, relevant_chunks)

    if not guardrail_check(answer, relevant_chunks):
        return "I couldn't find a reliable answer to that. Please contact our team directly for accurate information."

    store_answer(query, answer, cache)
    return answer

def generate_suggestions(chat_history):
    if not chat_history:
        return INITIAL_SUGGESTIONS

    history_text = "\n".join(f"{turn['role']}: {turn['text']}" for turn in chat_history[-6:])
    prompt = (
        "Based on this conversation with a company website assistant for CertiMinds "
        "(a technology talent consultancy in Qatar with programs like Launchpad, team building, "
        "and career building), suggest exactly 3 short, natural follow-up questions the user "
        "might want to ask next. Do not repeat questions already asked. Keep each under 10 words. "
        "Respond in the same language the user has been using in the conversation. "
        "Return only the 3 questions, one per line, no numbering, no extra text.\n\n"
        f"Conversation:\n{history_text}"
    )
    try:
        response = call_with_retry(lambda: client.models.generate_content(
            model=LITE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        ))
        lines = [line.strip("-* ").strip() for line in response.text.strip().splitlines() if line.strip()]
        return lines[:3] if lines else INITIAL_SUGGESTIONS
    except Exception:
        return INITIAL_SUGGESTIONS
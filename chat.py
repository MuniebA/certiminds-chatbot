from rag import load_index, answer_query
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def main():
    index = load_index()
    print("CertiMinds chatbot. Type exit to quit.")
    while True:
        query = input("You: ").strip()
        if query.lower() == "exit":
            break
        answer = answer_query(query, index)
        print("Bot:", answer)

if __name__ == "__main__":
    main()
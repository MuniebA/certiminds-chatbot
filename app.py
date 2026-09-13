import os
from flask import Flask, render_template, request, jsonify, session
from rag import load_index, answer_query, generate_suggestions, INITIAL_SUGGESTIONS

app = Flask(__name__)
app.secret_key = os.urandom(24)
index = load_index()

@app.route("/")
def home():
    session["history"] = []
    return render_template("index.html", suggestions=INITIAL_SUGGESTIONS)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()
    if not question:
        return jsonify({"answer": "Please type a question.", "suggestions": INITIAL_SUGGESTIONS})

    answer = answer_query(question, index)

    history = session.get("history", [])
    history.append({"role": "user", "text": question})
    history.append({"role": "assistant", "text": answer})
    history = history[-10:]
    session["history"] = history

    suggestions = generate_suggestions(history)

    return jsonify({"answer": answer, "suggestions": suggestions})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
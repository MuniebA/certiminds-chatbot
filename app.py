from flask import Flask, render_template, request, jsonify
from rag import load_index, answer_query

app = Flask(__name__)
index = load_index()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()
    if not question:
        return jsonify({"answer": "Please type a question."})
    answer = answer_query(question, index)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
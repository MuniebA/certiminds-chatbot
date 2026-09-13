const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.className = "message " + sender;
    div.textContent = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function renderSuggestions(suggestions) {
    const container = document.getElementById("suggestions");
    container.innerHTML = "";
    suggestions.forEach(function(question) {
        const btn = document.createElement("button");
        btn.className = "suggestion-btn";
        btn.textContent = question;
        btn.onclick = function() { askSuggestion(btn); };
        container.appendChild(btn);
    });
}

function askSuggestion(button) {
    userInput.value = button.textContent;
    sendMessage();
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage(message, "user");
    userInput.value = "";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        addMessage(data.answer, "bot");
        if (data.suggestions) {
            renderSuggestions(data.suggestions);
        }
    } catch (error) {
        addMessage("Something went wrong. Please try again.", "bot");
    }
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", function(event) {
    if (event.key === "Enter") sendMessage();
});
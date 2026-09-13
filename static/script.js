const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function linkify(text) {
    const urlRegex = /(https?:\/\/[^\s<]+)/g;
    return text.replace(urlRegex, function(url) {
        const cleanUrl = url.replace(/[.,)]+$/, "");
        return '<a href="' + cleanUrl + '" target="_blank" rel="noopener noreferrer">' + cleanUrl + '</a>';
    });
}

function formatMessage(text) {
    const escaped = escapeHtml(text);
    const linked = linkify(escaped);
    const lines = linked.split("\n");

    let html = "";
    let inList = null;

    function closeList() {
        if (inList) {
            html += "</" + inList + ">";
            inList = null;
        }
    }

    lines.forEach(function(line) {
        const trimmed = line.trim();
        if (trimmed === "") {
            closeList();
            return;
        }

        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
        const bulletMatch = trimmed.match(/^[-*]\s+(.*)/);

        if (numberedMatch) {
            if (inList !== "ol") { closeList(); html += "<ol>"; inList = "ol"; }
            html += "<li>" + numberedMatch[2] + "</li>";
        } else if (bulletMatch) {
            if (inList !== "ul") { closeList(); html += "<ul>"; inList = "ul"; }
            html += "<li>" + bulletMatch[1] + "</li>";
        } else {
            closeList();
            html += "<p>" + trimmed + "</p>";
        }
    });
    closeList();

    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    return html;
}

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.className = "message " + sender;
    if (sender === "bot") {
        div.innerHTML = formatMessage(text);
    } else {
        div.textContent = text;
    }
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
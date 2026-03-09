// ===== FreelanceAI Chat Application =====

let currentExtractedData = {};

// ===== Web Speech API Setup =====
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;
let synth = window.speechSynthesis;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        isListening = true;
        const btn = document.getElementById('voice-btn');
        if (btn) btn.classList.add('listening');
        document.getElementById('user-input').placeholder = "Listening...";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById('user-input');
        input.value += (input.value ? ' ' : '') + transcript;
        sendMessage();
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        stopListening();
    };

    recognition.onend = () => {
        stopListening();
    };
}

function toggleVoiceInput() {
    if (!SpeechRecognition) {
        alert("Voice recognition is not supported in your browser.");
        return;
    }
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function stopListening() {
    isListening = false;
    const btn = document.getElementById('voice-btn');
    if (btn) btn.classList.remove('listening');
    document.getElementById('user-input').placeholder = "Type or speak your message...";
}

function speakText(text) {
    if (!synth || !text) return;

    // Stop any current speech
    synth.cancel();

    // Strip emojis and simple markdown for speech
    const cleanText = text
        .replace(/^[#*-]+\s*/gm, '') // Remove list bullets/headers
        .replace(/[*_~`]+/g, '') // Remove bold/italic/code markers
        .replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '') // Remove emojis
        .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'en-US';
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    synth.speak(utterance);
}

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    fetchMetrics();
    setInterval(fetchMetrics, 30000);
    autoResizeTextarea();
    handleQueryParams();
});

function handleQueryParams() {
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get('project_id');
    const action = params.get('action');

    if (projectId) {
        currentExtractedData.project_id = parseInt(projectId);
    }

    if (action === 'invoice' && projectId) {
        quickAction(`I need to generate an invoice for project ID ${projectId}`);
    } else if (action === 'email' && projectId) {
        quickAction(`I need to send an email for project ID ${projectId}`);
    }
}

// ===== Sidebar Toggle =====
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth <= 768) {
        sidebar.classList.toggle('open');
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

// ===== Fetch Dashboard Metrics =====
async function fetchMetrics() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('outstanding-revenue').textContent = `$${(data.outstanding_revenue || 0).toFixed(2)}`;
        document.getElementById('unpaid-invoices').textContent = data.unpaid_invoices || 0;
        document.getElementById('active-projects').textContent = data.active_projects || 0;
    } catch (e) {
        console.log('Metrics fetch skipped:', e);
    }
}

// ===== Quick Action =====
function quickAction(text) {
    document.getElementById('user-input').value = text;
    sendMessage();
}

// ===== Auto-resize Textarea =====
function autoResizeTextarea() {
    const textarea = document.getElementById('user-input');
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });
}

// ===== Handle Enter Key =====
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// ===== Send Message =====
async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message) return;

    // Remove welcome message if present
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    appendMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    showTypingIndicator();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                action: null,
                extracted_data: currentExtractedData.project_id ? currentExtractedData : null
            })
        });

        removeTypingIndicator();

        if (!res.ok) {
            appendMessage('bot', '❌ Server error. Please try again.');
            return;
        }

        const data = await res.json();
        currentExtractedData = data.extracted_data || {};

        // Build response with actions
        appendMessage('bot', data.response || 'I didn\'t understand that.', data.actions, data.download_url, data.download_label);

        // Refresh metrics
        fetchMetrics();

    } catch (err) {
        removeTypingIndicator();
        appendMessage('bot', '❌ Connection error. Is the server running?');
    }
}

// ===== Execute Action =====
async function executeAction(action) {
    showTypingIndicator();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: '',
                action: action,
                extracted_data: currentExtractedData
            })
        });

        removeTypingIndicator();

        if (!res.ok) {
            appendMessage('bot', '❌ Action failed. Please try again.');
            return;
        }

        const data = await res.json();
        appendMessage('bot', data.response || 'Action completed.', null, data.download_url, data.download_label);
        fetchMetrics();

    } catch (err) {
        removeTypingIndicator();
        appendMessage('bot', '❌ Connection error during action.');
    }
}

// ===== Append Message to Chat =====
function appendMessage(role, text, actions, downloadUrl, downloadLabel) {
    if (role === 'bot') {
        speakText(text);
    }

    const container = document.getElementById('chat-container');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'Y' : 'AI';

    const content = document.createElement('div');
    content.className = 'message-content';

    // Render markdown for bot messages
    if (role === 'bot') {
        try {
            if (typeof marked !== 'undefined' && marked.parse) {
                content.innerHTML = marked.parse(text);
            } else {
                content.innerHTML = text.replace(/\n/g, '<br>');
            }
        } catch (e) {
            content.innerHTML = text.replace(/\n/g, '<br>');
        }
    } else {
        content.textContent = text;
    }

    // Add action buttons
    if (actions && actions.length > 0) {
        const btnContainer = document.createElement('div');
        btnContainer.className = 'action-buttons';
        actions.forEach(a => {
            const btn = document.createElement('button');
            btn.className = 'action-btn';
            btn.textContent = a.label;
            btn.onclick = () => executeAction(a.action);
            btnContainer.appendChild(btn);
        });
        content.appendChild(btnContainer);
    }

    // Add download button
    if (downloadUrl && downloadLabel) {
        const btnContainer = content.querySelector('.action-buttons') || document.createElement('div');
        if (!btnContainer.classList.contains('action-buttons')) {
            btnContainer.className = 'action-buttons';
            content.appendChild(btnContainer);
        }
        const dlBtn = document.createElement('a');
        dlBtn.className = 'action-btn download';
        dlBtn.textContent = downloadLabel;
        dlBtn.href = downloadUrl;
        dlBtn.target = '_blank';
        dlBtn.style.textDecoration = 'none';
        btnContainer.appendChild(dlBtn);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    container.appendChild(messageDiv);

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// ===== Typing Indicator =====
function showTypingIndicator() {
    const container = document.getElementById('chat-container');
    const existing = container.querySelector('.typing-indicator');
    if (existing) return;

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = `
        <div class="message-avatar" style="background: var(--accent-gradient); color: white;">AI</div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.querySelector('.typing-indicator');
    if (indicator) indicator.remove();
}

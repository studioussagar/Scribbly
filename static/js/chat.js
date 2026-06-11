document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const chatForm = document.getElementById('chat-form');
    
    if(!chatMessages || !messageInput || !chatForm) return; // not on chat page

    const chatData = document.getElementById('chat-data');
    const currentUsername = chatData.dataset.username;
    const conversationId = chatData.dataset.conversationId;
    
    // Auto-scroll logic to snap users to the bottom frame effortlessly
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    scrollToBottom();
    
    // Auto-resize textarea scaling organically based on content sizes
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
    
    function appendMessage(msg) {
        const isOutgoing = msg.sender === currentUsername;
        const bubbleClass = isOutgoing ? 'outgoing' : 'incoming';
        const checkmarks = isOutgoing ? '<span class="message-status read">✓✓</span>' : '';
        
        // Block raw XSS exploits via browser-native DOM stripping mechanisms
        const tempDiv = document.createElement('div');
        tempDiv.innerText = msg.message || msg.text;
        const safeText = tempDiv.innerHTML.replace(/\n/g, '<br>');
        
        const html = `
            <div class="message-bubble ${bubbleClass} new" data-id="${msg.id}">
                ${safeText}
                <div class="message-meta">
                    <span class="message-time">${msg.created_at}</span>
                    ${checkmarks}
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    // Connect to WebSocket dynamically across either ws:// or wss:// depending on environment setup
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws/chat/' + conversationId + '/';
    console.log("Attempting WebSocket Connection to:", wsUrl);
    
    // Globally defined so you can inspect it in the browser console!
    window.chatSocket = new WebSocket(wsUrl);

    window.chatSocket.onopen = function(e) {
        console.log("WebSocket Connection Successfully Established! chatSocket is now fully initialized.");
    };

    // Actively parse real-time incoming messages
    window.chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        // Only append explicitly if not already injected through local optimistic cache overlaps
        if (!document.querySelector(`.message-bubble[data-id="${data.id}"]`)) {
            let isAtBottom = (chatMessages.scrollHeight - chatMessages.scrollTop) <= (chatMessages.clientHeight + 100);
            appendMessage(data);
            if (isAtBottom || data.sender === currentUsername) {
                scrollToBottom();
            }
        }
    };

    window.chatSocket.onerror = function(e) {
        console.error("WebSocket encountered an error during connection. Daphne/ASGI might not be running properly. Validate with terminal logs.");
    };

    window.chatSocket.onclose = function(e) {
        console.error('Chat generic websocket socket terminated unexpectedly');
    };

    // Keyboard 'Enter' listeners acting as explicit form sends
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim()) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });
    
    // Native WebSocket asynchronous string form transmissions
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (!text) return;
        
        // Empties the input UI optimistically resolving UX queues instantly
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Launch standard message mapping immediately to the central router scope
        if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {
            window.chatSocket.send(JSON.stringify({
                'message': text
            }));
        } else {
            console.error("Failed to send: WebSocket is currently closed or uninitialized!");
        }
    });
    
    // Active typing UX focus placement
    messageInput.focus();
});

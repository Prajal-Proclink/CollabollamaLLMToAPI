const Priority = Object.freeze({
    ACTIVE: 1,
    COMPLETED: 2,
    ERROR: 3
});

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatBody = document.getElementById('chatBody');
const welcomeScreen = document.getElementById('welcomeScreen');
const historyList = document.getElementById('historyList');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const newChatBtn = document.getElementById('newChatBtn');
const suggestionDropdown = document.getElementById('suggestionDropdown');
const incognitoIcon = document.getElementById('incognitoIcon');
const tempChatPill = document.getElementById('tempChatPill');
const hamburgerBtn = document.getElementById('hamburgerBtn');
const drawerOverlay = document.getElementById('drawerOverlay');
const sidebar = document.getElementById('sidebar');
const splitDropdownBtn = document.getElementById('splitDropdownBtn');
const splitDropdownMenu = document.getElementById('splitDropdownMenu');
const tempChatToggle = document.getElementById('tempChatToggle');

let currentAbortController = null;
let currentInterval = null;
let isTemporaryChat = false;

let currentHistoryPage = 1;
const historyLimit = 10;
let totalHistoryRecords = 0;
let currentPromptId = null;

function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function showWelcomeScreen(isTemp = false) {
    chatBody.innerHTML = '';

    const welcome = document.createElement('div');
    welcome.className = 'welcome-screen';
    welcome.id = 'welcomeScreen';

    if (isTemp) {
        welcome.innerHTML = `
            <h1 class="welcome-heading">Temporary chat</h1>
            <p class="welcome-subtext">This chat won't be saved or create memories. It follows your organization's retention policy, and may still be accessible to your admin.</p>
        `;
    } else {
        welcome.innerHTML = `
            <h1 class="welcome-heading">What can I help you with?</h1>
        `;
    }
    chatBody.appendChild(welcome);

    // Toggle incognito icon and temp chat pill visibility
    if (incognitoIcon) incognitoIcon.style.display = isTemp ? 'flex' : 'none';
    if (tempChatPill) tempChatPill.style.display = isTemp ? 'inline-flex' : 'none';
}

function resetChatSession(isTemp = false) {
    if (currentAbortController) currentAbortController.abort();
    if (currentInterval) clearInterval(currentInterval);

    document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));

    isTemporaryChat = isTemp;
    currentPromptId = null;

    showWelcomeScreen(isTemp);
    updateTempToggleState();
}

newChatBtn.addEventListener('click', () => resetChatSession(false));

// Compose button starts a new chat (bind all instances)
document.querySelectorAll('.split-btn-primary').forEach(btn => {
    btn.addEventListener('click', () => resetChatSession(false));
});

// --- Mobile Drawer Logic ---

function openDrawer() {
    if (sidebar) sidebar.classList.add('open');
    if (drawerOverlay) drawerOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeDrawer() {
    if (sidebar) sidebar.classList.remove('open');
    if (drawerOverlay) drawerOverlay.classList.remove('open');
    document.body.style.overflow = '';
}

if (hamburgerBtn) {
    hamburgerBtn.addEventListener('click', openDrawer);
}

if (drawerOverlay) {
    drawerOverlay.addEventListener('click', closeDrawer);
}

// Close drawer when a nav item is clicked (on mobile)
document.querySelectorAll('.nav-item, .chat-item').forEach(item => {
    item.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            closeDrawer();
        }
    });
});

// --- Split Button Dropdown Logic ---

function openSplitDropdown() {
    if (splitDropdownMenu) splitDropdownMenu.classList.add('open');
    updateTempToggleState();
}

function closeSplitDropdown() {
    if (splitDropdownMenu) splitDropdownMenu.classList.remove('open');
}

function updateTempToggleState() {
    if (tempChatToggle) {
        tempChatToggle.classList.toggle('active', isTemporaryChat);
    }
}

if (splitDropdownBtn) {
    splitDropdownBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (splitDropdownMenu.classList.contains('open')) {
            closeSplitDropdown();
        } else {
            openSplitDropdown();
        }
    });
}

if (tempChatToggle) {
    tempChatToggle.addEventListener('click', () => {
        closeSplitDropdown();
        resetChatSession(!isTemporaryChat);
    });
}

// Close split dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (splitDropdownMenu && !splitDropdownMenu.contains(e.target) && !splitDropdownBtn.contains(e.target)) {
        closeSplitDropdown();
    }
});

// --- Suggestion Dropdown Logic ---

function openDropdown() {
    if (suggestionDropdown) suggestionDropdown.classList.add('open');
}

function closeDropdown() {
    if (suggestionDropdown) suggestionDropdown.classList.remove('open');
}

userInput.addEventListener('focus', () => {
    if (userInput.value.trim().length > 0) {
        openDropdown();
    }
});

userInput.addEventListener('input', () => {
    if (userInput.value.trim().length > 0) {
        openDropdown();
    } else {
        closeDropdown();
    }
});

userInput.addEventListener('blur', () => {
    setTimeout(closeDropdown, 150);
});

// Dropdown row clicks fill the input
document.querySelectorAll('.suggestion-row').forEach(row => {
    row.addEventListener('mousedown', (e) => {
        e.preventDefault();
        const text = row.querySelector('.suggestion-text, .suggestion-code, .suggestion-label');
        if (text) {
            userInput.value = text.textContent;
            userInput.focus();
        }
        closeDropdown();
    });
});

// Close kebab and dropdown on outside click
document.addEventListener('click', (e) => {
    const portal = document.getElementById('kebab-portal');
    if (portal && !portal.contains(e.target)) {
        portal.classList.remove('open');
    }
});

function appendMessage(text, isUser, isLoader = false) {
    const currentWelcome = document.getElementById('welcomeScreen');
    if (currentWelcome && chatBody.contains(currentWelcome)) {
        currentWelcome.remove();
    }

    const messageRow = document.createElement('div');
    messageRow.className = `message-row ${isUser ? 'user' : 'bot'}`;

    const container = document.createElement('div');
    container.className = 'message-container';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    let stopBtn = null;

    if (isLoader) {
        bubble.innerHTML = `
            <div class="dots-loader-container">
                <div class="dots-loader">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <button class="stop-btn" type="button" title="Stop generation">
                    <svg viewBox="0 0 24 24"><path d="M6 19h12V5H6v14z"/></svg>
                </button>
            </div>
        `;
        stopBtn = bubble.querySelector('.stop-btn');
    } else {
        bubble.innerText = text;
    }

    const meta = document.createElement('span');
    meta.className = 'msg-meta';
    meta.innerText = formatTime();
    bubble.appendChild(meta);

    container.appendChild(bubble);

    if (isUser && !isLoader) {
        const editBtn = document.createElement('button');
        editBtn.className = 'edit-btn';
        editBtn.type = 'button';
        editBtn.innerHTML = `
            <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
            Edit
        `;
        editBtn.addEventListener('click', () => {
            userInput.value = text;
            userInput.focus();
        });
        container.appendChild(editBtn);
    }

    messageRow.appendChild(container);
    chatBody.appendChild(messageRow);
    chatBody.scrollTop = chatBody.scrollHeight;

    return { bubble, stopBtn };
}

function getKebabPortal() {
    let menu = document.getElementById('kebab-portal');
    if (!menu) {
        menu = document.createElement('div');
        menu.id = 'kebab-portal';
        menu.className = 'kebab-menu';
        menu.setAttribute('role', 'menu');
        menu.innerHTML = `
            <button class="kebab-menu-item rename-btn" type="button" role="menuitem">
                <svg viewBox="0 0 24 24" width="14" height="14"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                Rename
            </button>
            <button class="kebab-menu-item delete-btn" type="button" role="menuitem">
                <svg viewBox="0 0 24 24" width="14" height="14"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                Delete
            </button>
        `;
        document.body.appendChild(menu);
    }
    return menu;
}

function addHistoryItemToSidebar(item, prepend = true) {
    const card = document.createElement('button');
    card.className = 'chat-item';
    card.dataset.idPrompt = item.idPrompt;

    card.innerHTML = `
        <span class="chat-item-text">${escapeHTML(item.prompts)}</span>
        <div class="chat-item-kebab">
            <span></span><span></span><span></span>
        </div>
    `;

    const kebabBtn = card.querySelector('.chat-item-kebab');

    kebabBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const menu = getKebabPortal();

        if (menu.dataset.activeCard === card.dataset.idPrompt && menu.classList.contains('open')) {
            menu.classList.remove('open');
            return;
        }

        menu.querySelector('.rename-btn').onclick = async (ev) => {
            ev.stopPropagation();
            menu.classList.remove('open');

            const promptEl = card.querySelector('.chat-item-text');
            const currentText = promptEl.textContent;
            const newName = prompt('Rename conversation:', currentText);

            if (newName && newName.trim() && newName.trim() !== currentText) {
                promptEl.textContent = newName.trim();
                item.prompts = newName.trim();

                try {
                    const res = await fetch('/update-promps', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            idPrompt: card.dataset.idPrompt,
                            prompts: newName.trim()
                        })
                    });
                    if (!res.ok) throw new Error(`Server error: ${res.status}`);
                } catch (err) {
                    alert(`Failed to update conversation: ${err.message}`);
                }
            }
        };

        menu.querySelector('.delete-btn').onclick = async (ev) => {
            ev.stopPropagation();
            menu.classList.remove('open');
            if (!confirm('Delete this conversation from the sidebar?')) return;

            try {
                const res = await fetch('/delete-prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idPrompt: item.idPrompt, isDeleted: 1 })
                });
                if (!res.ok) throw new Error(`Server error: ${res.status}`);
                card.remove();
            } catch (err) {
                alert(`Failed to delete conversation: ${err.message}`);
            }
        };

        const rect = kebabBtn.getBoundingClientRect();
        menu.style.top = `${rect.bottom + window.scrollY + 4}px`;
        menu.style.left = `${rect.left + window.scrollX}px`;
        menu.dataset.activeCard = card.dataset.idPrompt;
        menu.classList.add('open');
    });

    card.addEventListener('click', async () => {
        isTemporaryChat = false;

        document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        if (currentAbortController) currentAbortController.abort();
        if (currentInterval) clearInterval(currentInterval);

        currentPromptId = item.idPrompt;
        chatBody.innerHTML = '';

        currentAbortController = new AbortController();
        const { signal } = currentAbortController;

        try {
            const res = await fetch(`/get-conversation-messages?idPrompt=${item.idPrompt}&conversationState=0`, { signal });
            if (!res.ok) {
                appendMessage('Error loading conversation history.', false);
                return;
            }
            const resData = await res.json();

            if (resData.status !== 'success' || !Array.isArray(resData.data) || resData.data.length === 0) {
                appendMessage(item.prompts, true);
                const { bubble: botBubble, stopBtn } = appendMessage('', false, true);
                if (stopBtn) {
                    stopBtn.addEventListener('click', () => {
                        if (currentAbortController) currentAbortController.abort();
                        if (currentInterval) clearInterval(currentInterval);
                        botBubble.innerHTML = `<span class="error-message">Request stopped.</span>`;
                        const meta = document.createElement('span');
                        meta.className = 'msg-meta';
                        meta.innerText = formatTime();
                        botBubble.appendChild(meta);
                    });
                }
                pollConversationStatus(item.idPrompt, botBubble, signal);
                return;
            }

            const rows = resData.data;
            let lastBotBubble = null;
            let lastRowPending = false;

            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const userText = row.conversation || '';
                const botText = row.conversationResponce || '';
                const state = row.conversationState;

                if (userText.trim()) {
                    appendMessage(userText, true);
                }

                if (state === Priority.COMPLETED && botText.trim()) {
                    appendMessage(botText, false);
                    lastRowPending = false;
                } else {
                    const { bubble: botBubble, stopBtn } = appendMessage('', false, true);
                    lastBotBubble = botBubble;
                    lastRowPending = true;

                    if (stopBtn) {
                        stopBtn.addEventListener('click', () => {
                            if (currentAbortController) currentAbortController.abort();
                            if (currentInterval) clearInterval(currentInterval);
                            botBubble.innerHTML = `<span class="error-message">Request stopped.</span>`;
                            const meta = document.createElement('span');
                            meta.className = 'msg-meta';
                            meta.innerText = formatTime();
                            botBubble.appendChild(meta);
                        });
                    }
                }
            }

            if (lastRowPending && lastBotBubble) {
                pollConversationStatus(item.idPrompt, lastBotBubble, signal);
            }

        } catch (err) {
            if (err.name === 'AbortError') return;
            appendMessage(`Error: ${err.message}`, false);
        }
    });

    if (prepend) {
        historyList.prepend(card);
    } else {
        historyList.appendChild(card);
    }
}

async function loadHistory(page = 1) {
    try {
        const response = await fetch(`/chat-history?page=${page}&limit=${historyLimit}&promptType=1`);
        if (!response.ok) return;
        const res = await response.json();
        if (res.status === 'success' && res.data) {
            totalHistoryRecords = res.total;
            res.data.forEach(item => {
                if (!document.querySelector(`.chat-item[data-id-prompt="${item.idPrompt}"]`)) {
                    addHistoryItemToSidebar(item, false);
                }
            });

            const loadedCount = document.querySelectorAll('.chat-item').length;
            loadMoreBtn.style.display = loadedCount >= totalHistoryRecords ? 'none' : 'block';
        }
    } catch (err) {
        console.error('Failed to load chat history:', err);
    }
}

loadMoreBtn.addEventListener('click', () => {
    currentHistoryPage++;
    loadHistory(currentHistoryPage);
});

loadHistory(1);

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const promptText = userInput.value.trim();
    if (!promptText) return;

    userInput.value = '';

    if (currentAbortController) currentAbortController.abort();
    if (currentInterval) clearInterval(currentInterval);

    appendMessage(promptText, true);

    currentAbortController = new AbortController();
    const { signal } = currentAbortController;

    const { bubble: botBubble, stopBtn } = appendMessage('', false, true);

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            if (currentAbortController) currentAbortController.abort();
            if (currentInterval) clearInterval(currentInterval);
            botBubble.innerHTML = `<span class="error-message">Request stopped.</span>`;
            const meta = document.createElement('span');
            meta.className = 'msg-meta';
            meta.innerText = formatTime();
            botBubble.appendChild(meta);
        });
    }

    try {
        if (!currentPromptId) {
            const response = await fetch('/add-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompts: promptText, promptType: isTemporaryChat ? 2 : 1 }),
                signal: signal
            });

            if (!response.ok) throw new Error('Failed to register prompt');
            const result = await response.json();
            currentPromptId = result.idPrompt;

            if (!isTemporaryChat) {
                const newItem = {
                    idPrompt: currentPromptId,
                    prompts: promptText,
                    promptType: 1,
                    promptdate: new Date().toISOString(),
                    prompsResponce: null
                };
                addHistoryItemToSidebar(newItem, true);
            }
        }

        const response2 = await fetch('/add-conversation-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation: promptText, idPrompt: currentPromptId }),
            signal: signal
        });

        if (!response2.ok) throw new Error('Failed to register conversation message');

        pollConversationStatus(currentPromptId, botBubble, signal);

    } catch (err) {
        if (err.name === 'AbortError') return;

        botBubble.innerHTML = `<span class="error-message">Error: ${err.message}</span>`;
        const meta = document.createElement('span');
        meta.className = 'msg-meta';
        meta.innerText = formatTime();
        botBubble.appendChild(meta);
    }
});

async function pollConversationStatus(idPrompt, botBubble, signal) {
    const maxAttempts = 90;
    let attempts = 0;

    try {
        const checkRes = await fetch('/chat-process');
        if (!checkRes.ok) {
            botBubble.innerHTML = `<span class="error-message">Process server not responding.</span>`;
            const meta = document.createElement('span');
            meta.className = 'msg-meta';
            meta.innerText = formatTime();
            botBubble.appendChild(meta);
            return;
        }
    } catch (err) {
        botBubble.innerHTML = `<span class="error-message">Cannot reach process server.</span>`;
        const meta = document.createElement('span');
        meta.className = 'msg-meta';
        meta.innerText = formatTime();
        botBubble.appendChild(meta);
        return;
    }

    currentInterval = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            clearInterval(currentInterval);
            botBubble.innerHTML = `<span class="error-message">Error: Request timed out.</span>`;
            const meta = document.createElement('span');
            meta.className = 'msg-meta';
            meta.innerText = formatTime();
            botBubble.appendChild(meta);
            return;
        }

        try {
            const response = await fetch(`/get-conversation-messages?idPrompt=${idPrompt}`, { signal });
            if (!response.ok) {
                if (response.status === 404) {
                    clearInterval(currentInterval);
                    throw new Error('Prompt status record not found.');
                }
                return;
            }

            const data = await response.json();

            if (data.status === 'success' && data.data && data.data.length > 0) {
                const latestConversation = data.data[data.data.length - 1];
                const state = latestConversation.conversationState;
                const reply = latestConversation.conversationResponce;

                if (state === 2 || (reply && reply.trim() !== '')) {
                    clearInterval(currentInterval);
                    botBubble.innerHTML = '';
                    botBubble.innerText = reply;

                    const meta = document.createElement('span');
                    meta.className = 'msg-meta';
                    meta.innerText = formatTime();
                    botBubble.appendChild(meta);
                }
            }
        } catch (err) {
            if (err.name === 'AbortError') return;
            clearInterval(currentInterval);
            botBubble.innerHTML = `<span class="error-message">Error: ${err.message}</span>`;
            const meta = document.createElement('span');
            meta.className = 'msg-meta';
            meta.innerText = formatTime();
            botBubble.appendChild(meta);
        }
    }, 1500);
}

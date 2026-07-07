        // Mirror of Python Priority enum
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
        const tempChatBtn = document.getElementById('tempChatBtn');

        let currentAbortController = null;
        let currentInterval = null;
        let isTemporaryChat = false;

        let currentHistoryPage = 1;
        const historyLimit = 10;
        let totalHistoryRecords = 0;
        let currentPromptId = null; // Persists idPrompt so /add-prompt is skipped on re-submit

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
            welcome.className = 'welcome-container';
            welcome.id = 'welcomeScreen';
            
            if (isTemp) {
                welcome.innerHTML = `
                    <div class="welcome-icon">🔒</div>
                    <h2 class="welcome-title">Temporary Chat Mode</h2>
                    <p class="welcome-desc">Prompts entered in this mode will be processed normally but <strong>will not be saved to your sidebar history list</strong> on the frontend.</p>
                `;
            } else {
                welcome.innerHTML = `
                    <div class="welcome-icon">🦙</div>
                    <h2 class="welcome-title">Welcome to CollabOllama</h2>
                    <p class="welcome-desc">Enter your prompt below. The system will dispatch it to the scheduler queue, register it via <strong>add-prompt</strong>, and continuously monitor status responses.</p>
                `;
            }
            chatBody.appendChild(welcome);
        }

        function resetChatSession(isTemp = false) {
            // Cancel active polling/requests
            if (currentAbortController) currentAbortController.abort();
            if (currentInterval) clearInterval(currentInterval);

            // Deselect selected cards in sidebar
            document.querySelectorAll('.history-item').forEach(c => c.style.borderColor = 'var(--border-color)');

            // Reset flags
            isTemporaryChat = isTemp;
            currentPromptId = null; // Clear stored prompt ID for the new session
            if (isTemp) {
                tempChatBtn.classList.add('active');
            } else {
                tempChatBtn.classList.remove('active');
            }

            // Show appropriate welcome screen
            showWelcomeScreen(isTemp);
        }

        newChatBtn.addEventListener('click', () => resetChatSession(false));
        tempChatBtn.addEventListener('click', () => resetChatSession(true));

        // Close any open kebab menus when clicking elsewhere on the page
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

            // Add Edit button for user messages
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

        // --- Kebab portal: single shared floating menu appended to <body> ---
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

        // Add history item card to sidebar list
        function addHistoryItemToSidebar(item, prepend = true) {
            const card = document.createElement('div');
            card.className = 'history-item';
            card.dataset.idPrompt = item.idPrompt;
            
            let dateStr = '';
            if (item.promptdate) {
                try {
                    const d = new Date(item.promptdate);
                    dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                } catch(e) {
                    dateStr = item.promptdate;
                }
            }

            card.innerHTML = `
                <div class="history-item-body">
                    <div class="history-item-prompt">${escapeHTML(item.prompts)}</div>
                    <div class="history-item-meta"></div>
                </div>
                <div class="history-item-actions">
                    <button class="kebab-btn" type="button" title="More options" aria-label="More options">
                        <span></span><span></span><span></span>
                    </button>
                </div>
            `;

            // --- Kebab menu wiring (portal approach) ---
            const kebabBtn = card.querySelector('.kebab-btn');

            kebabBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const menu = getKebabPortal();

                // If already open for this button, close it
                if (menu.dataset.activeCard === card.dataset.idPrompt && menu.classList.contains('open')) {
                    menu.classList.remove('open');
                    return;
                }

                // Bind rename/delete to this card's context
                menu.querySelector('.rename-btn').onclick = (ev) => {
                    ev.stopPropagation();
                    menu.classList.remove('open');
                    const promptEl = card.querySelector('.history-item-prompt');
                    const currentText = promptEl.textContent;
                    const newName = prompt('Rename conversation:', currentText);
                    if (newName && newName.trim() && newName.trim() !== currentText) {
                        promptEl.textContent = newName.trim();
                        item.prompts = newName.trim();
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

                // Position the portal next to the kebab button
                const rect = kebabBtn.getBoundingClientRect();
                menu.style.top  = `${rect.bottom + window.scrollY + 4}px`;
                menu.style.left = `${rect.right  + window.scrollX + 4}px`;
                menu.dataset.activeCard = card.dataset.idPrompt;
                menu.classList.add('open');
            });

            card.addEventListener('click', async () => {

                // Remove active classes from Temp Chat mode when viewing persistent history
                isTemporaryChat = false;
                tempChatBtn.classList.remove('active');

                // Deselect other cards, highlight selected
                document.querySelectorAll('.history-item').forEach(c => c.style.borderColor = 'var(--border-color)');
                card.style.borderColor = 'var(--accent-purple)';

                // Cancel any active polling/request
                if (currentAbortController) currentAbortController.abort();
                if (currentInterval) clearInterval(currentInterval);

                // Set idPrompt context so re-submissions append to this session
                currentPromptId = item.idPrompt;

                // Clear main chat area
                chatBody.innerHTML = '';

                currentAbortController = new AbortController();
                const { signal } = currentAbortController;

                try {
                    // Fetch ALL conversation rows for this idPrompt (conversationState=0 = all)
                    const res = await fetch(`/get-conversation-messages?idPrompt=${item.idPrompt}&conversationState=0`, { signal });
                    if (!res.ok) {
                        appendMessage('Error loading conversation history.', false);
                        return;
                    }
                    const resData = await res.json();

                    if (resData.status !== 'success' || !Array.isArray(resData.data) || resData.data.length === 0) {
                        // No conversation records yet — show the prompt and a pending loader
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

                    // Render each conversation exchange as chat bubbles
                    let lastBotBubble = null;
                    let lastRowPending = false;

                    for (let i = 0; i < rows.length; i++) {
                        const row = rows[i];
                        const userText = row.conversation || '';
                        const botText = row.conversationResponce || '';
                        const state = row.conversationState; // 1=active/pending, 2=completed

                        // User bubble
                        if (userText.trim()) {
                            appendMessage(userText, true);
                        }

                        if (state === Priority.COMPLETED && botText.trim()) {
                            // Completed — render the bot reply inline (no loader)
                            appendMessage(botText, false);
                            lastRowPending = false;
                        } else {
                            // Still pending — show loader for this message
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

                    // If last row is still pending, start polling for its response
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

        // Fetch paginated history from API
        async function loadHistory(page = 1) {
            try {
                const response = await fetch(`/chat-history?page=${page}&limit=${historyLimit}&promptType=1`);
                if (!response.ok) return;
                const res = await response.json();
                if (res.status === 'success' && res.data) {
                    totalHistoryRecords = res.total;
                    res.data.forEach(item => {
                        if (!document.querySelector(`.history-item[data-prompt-id="${item.idPrompt}"]`)) {
                            addHistoryItemToSidebar(item, false);
                        }
                    });
                    
                    const loadedCount = document.querySelectorAll('.history-item').length;
                    if (loadedCount >= totalHistoryRecords) {
                        loadMoreBtn.style.display = 'none';
                    } else {
                        loadMoreBtn.style.display = 'block';
                    }
                }
            } catch (err) {
                console.error('Failed to load chat history:', err);
            }
        }

        loadMoreBtn.addEventListener('click', () => {
            currentHistoryPage++;
            loadHistory(currentHistoryPage);
        });

        // Initialize Chat History on load
        loadHistory(1);

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = userInput.value.trim();
            if (!promptText) return;

            userInput.value = '';

            // Cancel any active request
            if (currentAbortController) {
                currentAbortController.abort();
            }
            if (currentInterval) {
                clearInterval(currentInterval);
            }

            appendMessage(promptText, true);

            // Create a new AbortController
            currentAbortController = new AbortController();
            const { signal } = currentAbortController;

            // Create loading response bubble for bot
            const { bubble: botBubble, stopBtn } = appendMessage('', false, true);

            // Attach Stop click handler
            if (stopBtn) {
                stopBtn.addEventListener('click', () => {
                    if (currentAbortController) {
                        currentAbortController.abort();
                    }
                    if (currentInterval) {
                        clearInterval(currentInterval);
                    }
                    botBubble.innerHTML = `<span class="error-message">Request stopped.</span>`;
                    const meta = document.createElement('span');
                    meta.className = 'msg-meta';
                    meta.innerText = formatTime();
                    botBubble.appendChild(meta);
                });
            }

            try {
                // 1. Call add-prompt only if no prompt ID is stored for this session
                if (!currentPromptId) {
                    const response = await fetch('/add-prompt', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ prompts: promptText, promptType: isTemporaryChat ? 2 : 1 }),
                        signal: signal
                    });

                    if (!response.ok) {
                        throw new Error('Failed to register prompt');
                    }
                    const result = await response.json();
                    currentPromptId = result.idPrompt; // Store for reuse

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
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ conversation: promptText, idPrompt: currentPromptId }),
                    signal: signal
                });

                if (!response2.ok) {
                    throw new Error('Failed to register conversation message');
                }

                // Prepend new prompt item to sidebar history list if NOT in temporary mode

                // 2. Poll conversation status until response is ready
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

        async function pollPromptStatus(idPrompt, botBubble, signal) {
            const maxAttempts = 90; // 2+ minutes max
            let attempts = 0;

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
                    const response = await fetch(`/get-prompt-status?idPrompt=${idPrompt}`, { signal });
                    if (!response.ok) {
                        if (response.status === 404) {
                            clearInterval(currentInterval);
                            throw new Error('Prompt status record not found.');
                        }
                        return;
                    }

                    const data = await response.json();
                    if (data.status === 'success' && data.data) {
                        const state = data.data.promptType;
                        const reply = data.data.prompsResponce;

                        // promptType 2 indicates completed
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
        async function pollConversationStatus(idPrompt, botBubble, signal) {
            const maxAttempts = 90; // 2+ minutes max
            let attempts = 0;

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
                    const response = await fetch(`/get-conversation-messages?idPrompt=${idPrompt}&conversationState=${Priority.COMPLETED}`, { signal });
                    if (!response.ok) {
                        if (response.status === 404) {
                            clearInterval(currentInterval);
                            throw new Error('Prompt status record not found.');
                        }
                        return;
                    }

                    const data = await response.json();
                    if (data.status === 'success' && data.data) {
                        const state = data.data.promptType;
                        const reply = data.data.prompsResponce;

                        // promptType 2 indicates completed
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
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
                <div class="history-item-prompt">${escapeHTML(item.prompts)}</div>
                <div class="history-item-meta">
                    
                </div>
            `;
            
            card.addEventListener('click', async () => {
                // Remove active classes from Temp Chat mode when viewing persistent history
                isTemporaryChat = false;
                tempChatBtn.classList.remove('active');

                // Deselect other cards
                document.querySelectorAll('.history-item').forEach(c => c.style.borderColor = 'var(--border-color)');
                card.style.borderColor = 'var(--accent-purple)';
                
                // Clear main chat area
                chatBody.innerHTML = '';
                
                // Load clicked item details
                appendMessage(item.prompts, true);
                
                const { bubble: botBubble, stopBtn } = appendMessage('', false, true);
                
                // Cancel existing request
                if (currentAbortController) currentAbortController.abort();
                if (currentInterval) clearInterval(currentInterval);
                
                currentAbortController = new AbortController();
                const { signal } = currentAbortController;
                
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
                
                // Retrieve response status from DB
                try {
                    const res = await fetch(`/get-prompt-status?idPrompt=${item.idPrompt}`, { signal });
                    if (!res.ok) {
                        botBubble.innerHTML = `<span class="error-message">Error fetching response status.</span>`;
                        return;
                    }
                    const resData = await res.json();
                    if (resData.status === 'success' && resData.data) {
                        const state = resData.data.processState;
                        const reply = resData.data.prompsResponce;
                        
                        if (state === 2 || (reply && reply.trim() !== '')) {
                            botBubble.innerHTML = '';
                            botBubble.innerText = reply;
                            const meta = document.createElement('span');
                            meta.className = 'msg-meta';
                            meta.innerText = formatTime();
                            botBubble.appendChild(meta);
                        } else {
                            // Resume polling
                            pollConversationStatus(item.idPrompt, botBubble, signal);
                        }
                    }
                } catch (err) {
                    if (err.name === 'AbortError') return;
                    botBubble.innerHTML = `<span class="error-message">Error: ${err.message}</span>`;
                    const meta = document.createElement('span');
                    meta.className = 'msg-meta';
                    meta.innerText = formatTime();
                    botBubble.appendChild(meta);
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
                const response = await fetch(`/chat-history?page=${page}&limit=${historyLimit}`);
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
                // 1. Call add-prompt endpoint
                const response = await fetch('/add-prompt', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ prompts: promptText }),
                    signal: signal
                });

                if (!response.ok) {
                    throw new Error('Failed to register prompt');
                }
                const result = await response.json();
                const idPrompt = result.idPrompt;
                const response2 = await fetch('/add-conversation-message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ conversation: promptText ,idPrompt: idPrompt }),
                    signal: signal
                });

                if (!response2.ok) {
                    throw new Error('Failed to register prompt');
                }
                

                // Prepend new prompt item to sidebar history list if NOT in temporary mode
                if (!isTemporaryChat) {
                    const newItem = {
                        idPrompt: idPrompt,
                        prompts: promptText,
                        processState: 1,
                        promptdate: new Date().toISOString(),
                        prompsResponce: null
                    };
                    addHistoryItemToSidebar(newItem, true);
                }

                // 2. Poll prompt status until response is ready
                pollPromptStatus(idPrompt, botBubble, signal);

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
                        const state = data.data.processState;
                        const reply = data.data.prompsResponce;

                        // processState 2 indicates completed
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
                    const response = await fetch(`/get-conversation-messages?idPrompt=${idPrompt}&conversationState=2`, { signal });
                    if (!response.ok) {
                        if (response.status === 404) {
                            clearInterval(currentInterval);
                            throw new Error('Prompt status record not found.');
                        }
                        return;
                    }

                    const data = await response.json();
                    if (data.status === 'success' && data.data) {
                        const state = data.data.processState;
                        const reply = data.data.prompsResponce;

                        // processState 2 indicates completed
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
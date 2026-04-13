// ============================================================
// Chat — Messages, Streaming, Actions (Edit / Regenerate / Copy)
// ============================================================

import { generateUUID, nowTimeLabel, autoResize, scrollToBottom, appState } from './helpers.js';
import { formatMessage } from './markdown.js';
import { imageState, removeImagePreview, setImageUploadUI } from './imageUpload.js';
import { escapeAttr } from './helpers.js';  // ✅ FIX (C-03): import for URL sanitization

// ── References set by initChat ────────────────────────────────
let _chatMessages, _chatInterface, _heroSection, _searchInput;
let _saveMessageFn = null; // set externally by app.js
let _fetchHistoryFn = null;

export function setChatCallbacks({ saveMessage, fetchHistory }) {
    _saveMessageFn = saveMessage;
    _fetchHistoryFn = fetchHistory;
}

// ── Add a message bubble to the chat ──────────────────────────
export function addMessage(text, sender, imageUrl = null, isError = false, opts = {}) {
    if (!_chatMessages) _chatMessages = document.getElementById('chat-messages');

    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', `${sender}-message`);
    if (isError) msgDiv.classList.add('error-message');
    if (imageUrl) msgDiv.classList.add('has-image');

    const messageId = opts.messageId || generateUUID();
    msgDiv.dataset.messageId = messageId;
    msgDiv.dataset.sender = sender;
    msgDiv.dataset.ts = opts.ts || new Date().toISOString();
    if (opts.replyToUserId) msgDiv.dataset.replyToUserId = opts.replyToUserId;
    if (opts.userPrompt) msgDiv.dataset.userPrompt = opts.userPrompt;

    if (sender === 'ai') {
        msgDiv.innerHTML = `
            <div class="message-avatar">
                <img src="logo.png" alt="AI">
            </div>
            <div class="message-content">
                <div class="ai-name">Sphinx-SCA</div>
                <div class="text-body">${text || ''}</div>
                <div class="message-actions">
                    <button class="action-btn" data-action="copy" title="Copy">
                        <span class="material-symbols-outlined">content_copy</span>
                    </button>
                    <button class="action-btn" data-action="regenerate" title="Regenerate">
                        <span class="material-symbols-outlined">refresh</span>
                    </button>
                    <button class="action-btn" data-action="like" title="Like">
                        <span class="material-symbols-outlined">thumb_up_off_alt</span>
                    </button>
                    <button class="action-btn" data-action="dislike" title="Dislike">
                        <span class="material-symbols-outlined">thumb_down_off_alt</span>
                    </button>
                </div>
            </div>
        `;
    } else {
        const userName = document.querySelector('#nav-user-avatar img')?.alt || 'User';
        msgDiv.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: flex-end; width: 100%;">
                <div class="message-content" style="max-width: 100%;">
                    ${imageUrl ? `<img src="${escapeAttr(imageUrl)}" class="message-image" data-action="zoom-media" alt="Uploaded image">` : ''}
                    ${text && text !== '📷 Image Message' ? `<div class="text-body">${text}</div>` : ''}
                </div>
                <div class="message-actions-inline" style="display: flex; gap: 4px; align-items: center; margin-top: 6px; margin-right: 4px;">
                    <span class="message-time" data-role="time">${opts.timeLabel || nowTimeLabel()}</span>
                    <button class="inline-action" data-action="resend-user" title="Resend" style="border:none; padding:4px;">
                        <span class="material-symbols-outlined" style="font-size:16px;">refresh</span>
                    </button>
                    <button class="inline-action" data-action="edit-user" title="Edit" style="border:none; padding:4px;">
                        <span class="material-symbols-outlined" style="font-size:16px;">edit</span>
                    </button>
                    <button class="inline-action" data-action="copy-user" title="Copy" style="border:none; padding:4px;">
                        <span class="material-symbols-outlined" style="font-size:16px;">content_copy</span>
                    </button>
                </div>
            </div>
            <div class="message-avatar">
                <img src="user.png" alt="${userName}">
            </div>
        `;
    }

    _chatMessages.appendChild(msgDiv);
    scrollToBottom(_chatInterface || document.getElementById('chat-interface'));

    const body = msgDiv.querySelector('.text-body');
    if (text && sender === 'ai' && body) {
        body.innerHTML = formatMessage(text);
    } else if (text && sender === 'user' && body) {
        body.textContent = text;
    }

    return msgDiv;
}

// ── The core Send / Stream handler ────────────────────────────
export async function handleSend() {
    if (appState.isStreaming) return;

    const chatInput = document.getElementById('chat-search-input');
    if (!_searchInput) _searchInput = document.getElementById('main-search-input');
    const activeInput = appState.isChatActive && chatInput ? chatInput : _searchInput;
    const msg = activeInput?.value || '';
    if (!msg.trim() && !imageState.file) return;

    let finalMsg = msg || 'Solve this math problem from the image.';
    let attachedImageForChat = null;
    let attachedImageForBackend = null;

    if (imageState.file) {
        if (imageState.isPreparing) {
            setImageUploadUI({ visible: true, loading: true, progress: 0, text: 'Uploading…' });
            while (imageState.isPreparing) {
                await new Promise((r) => setTimeout(r, 40));
            }
        }
        attachedImageForChat = imageState.objectUrl || document.getElementById('image-preview-thumbnail')?.src;
        attachedImageForBackend = imageState.dataUrl;
    }

    // ── Transition to chat mode ──
    if (!appState.isChatActive) {
        if (!_heroSection) _heroSection = document.querySelector('.hero');
        if (!_chatInterface) _chatInterface = document.getElementById('chat-interface');

        appState.isChatActive = true;
        _heroSection?.classList.add('animate-out');
        await new Promise((r) => setTimeout(r, 400));
        if (_heroSection) _heroSection.style.display = 'none';
        if (_chatInterface) _chatInterface.style.display = 'flex';
        const floatingWrapper = document.getElementById('floating-search-wrapper');
        if (floatingWrapper) floatingWrapper.style.display = 'flex';
        document.querySelectorAll('.chat-attach-hide').forEach((el) => el.classList.add('chat-attach-btn-hidden'));
    }

    const sendBtn = document.getElementById('main-send-btn');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const activeSendBtn = appState.isChatActive ? chatSendBtn || sendBtn : sendBtn;
    const sendBtnIcon = activeSendBtn?.querySelector('.send-icon');

    const API_URL =
        typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL
            ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '')
            : '';

    appState.isStreaming = true;
    if (sendBtn) sendBtn.disabled = true;
    if (chatSendBtn) chatSendBtn.disabled = true;
    if (sendBtnIcon) sendBtnIcon.textContent = 'pending';

    // ── Add User Message ──
    const userMsgEl = addMessage(msg, 'user', attachedImageForChat);
    try {
        if (_saveMessageFn) await _saveMessageFn(msg || '', 'user', attachedImageForBackend || attachedImageForChat);
    } catch (e) {
        console.warn('Could not save to Supabase history:', e);
    }

    if (activeInput) { activeInput.value = ''; autoResize(activeInput); }
    removeImagePreview();

    // ── Stream from backend ──
    try {
        if (!_chatMessages) _chatMessages = document.getElementById('chat-messages');
        if (!_chatInterface) _chatInterface = document.getElementById('chat-interface');

        const historyForBackend = [];
        const messageElements = _chatMessages.querySelectorAll('.message');
        const recentMsgs = Array.from(messageElements).slice(-10);
        recentMsgs.forEach((el) => {
            const isUser = el.classList.contains('user-message');
            const text = el.querySelector('.text-body')?.textContent;
            if (text) {
                historyForBackend.push({ role: isUser ? 'user' : 'assistant', content: text });
            }
        });

        const aiMsgDiv = addMessage('', 'ai', null, false, {
            replyToUserId: userMsgEl?.dataset?.messageId,
            userPrompt: finalMsg,
        });
        const aiTextDiv = aiMsgDiv.querySelector('.text-body');
        let fullAiResponse = '';

        // Skeleton loader
        if (aiTextDiv) {
            aiTextDiv.innerHTML = `
                <div class="stream-skeleton" data-role="skeleton">
                    <div class="skeleton skeleton-line" style="width:70%"></div>
                    <div class="skeleton skeleton-line"></div>
                    <div class="skeleton skeleton-line" style="width:45%"></div>
                </div>`;
        }

        const response = await fetch(`${API_URL}/solve_stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: finalMsg,
                user_id: appState.currentUserId,
                history: historyForBackend,
                mode: appState.currentMode,
                image_data: attachedImageForBackend,
            }),
        });

        if (!response.ok) throw new Error(`Server Error: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let gotFirstToken = false;

        const renderStreamingText = () => {
            if (!aiTextDiv) return;
            const cursor = '<span class="typing-cursor" aria-hidden="true"></span>';
            aiTextDiv.innerHTML = formatMessage(fullAiResponse) + cursor;
            scrollToBottom(_chatInterface, false);
        };

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buffer.indexOf('\n')) !== -1) {
                const line = buffer.slice(0, idx).trimEnd();
                buffer = buffer.slice(idx + 1);
                if (!line.startsWith('data:')) continue;

                const dataStr = line.replace(/^data:\s*/, '').trim();
                if (!dataStr || dataStr === '[DONE]') continue;

                try {
                    const data = JSON.parse(dataStr);
                    if (data && typeof data.content === 'string' && data.content.length) {
                        if (!gotFirstToken) {
                            gotFirstToken = true;
                            const sk = aiTextDiv?.querySelector('[data-role="skeleton"]');
                            if (sk) sk.remove();
                        }
                        fullAiResponse += data.content;
                        renderStreamingText();
                    }
                } catch { /* partial JSON, ignore */ }
            }
        }

        // ── Stream complete ──
        appState.isStreaming = false;
        if (sendBtn) sendBtn.disabled = false;
        if (chatSendBtn) chatSendBtn.disabled = false;
        if (sendBtnIcon) sendBtnIcon.textContent = 'arrow_upward';

        // Final render (no cursor)
        if (aiTextDiv) aiTextDiv.innerHTML = formatMessage(fullAiResponse || '');

        if (fullAiResponse) {
            try { if (_saveMessageFn) await _saveMessageFn(fullAiResponse, 'ai'); } catch { /* ignore */ }
            try { if (_fetchHistoryFn) _fetchHistoryFn(); } catch { /* ignore */ }
        }
    } catch (error) {
        console.error('Streaming error:', error);
        appState.isStreaming = false;
        if (sendBtn) sendBtn.disabled = false;
        if (chatSendBtn) chatSendBtn.disabled = false;
        if (sendBtnIcon) sendBtnIcon.textContent = 'arrow_upward';

        const errMsg = addMessage(
            `❌ Connection Failed: ${error.message}\n\nTip: Click Retry to try again.`,
            'ai', null, true,
            { replyToUserId: userMsgEl?.dataset?.messageId, userPrompt: finalMsg }
        );
        // Add retry button
        const errBody = errMsg.querySelector('.text-body');
        if (errBody) {
            const retryBtn = document.createElement('button');
            retryBtn.className = 'error-retry-btn';
            retryBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px">refresh</span> Retry';
            retryBtn.addEventListener('click', () => {
                errMsg.remove();
                const ci = document.getElementById('chat-search-input');
                if (ci) ci.value = finalMsg;
                handleSend();
            });
            errBody.appendChild(retryBtn);
        }
    }
}

// ── Message Action Handlers (delegated) ───────────────────────
export function bindMessageActions() {
    if (!_chatMessages) _chatMessages = document.getElementById('chat-messages');
    if (!_chatMessages) return;

    _chatMessages.addEventListener('click', (e) => {
        // AI message action buttons
        const actionBtn = e.target.closest('.action-btn');
        if (actionBtn) {
            handleAiAction(actionBtn);
            return;
        }

        // User message inline actions
        const inlineBtn = e.target.closest('.inline-action');
        if (inlineBtn) {
            handleUserAction(inlineBtn);
            return;
        }

        // Code copy button
        const copyBtn = e.target.closest('.code-copy-btn');
        if (copyBtn) {
            handleCodeCopy(copyBtn);
            return;
        }
    });
}

function handleAiAction(btn) {
    const action = btn.dataset.action;
    const msgEl = btn.closest('.message');
    const msgContent = btn.closest('.message-content');

    if (action === 'copy') {
        const text = msgContent?.querySelector('.text-body')?.innerText;
        if (text) {
            navigator.clipboard.writeText(text).then(() => {
                btn.classList.add('copied');
                const icon = btn.querySelector('.material-symbols-outlined');
                if (icon) icon.textContent = 'check';
                setTimeout(() => {
                    btn.classList.remove('copied');
                    if (icon) icon.textContent = 'content_copy';
                }, 1500);
            });
        }
    } else if (action === 'regenerate') {
        // FIX: Find the SPECIFIC user message that triggered this AI response
        // via the data-reply-to-user-id attribute
        const linkedUserId = msgEl?.dataset?.replyToUserId;
        let prompt = null;

        if (linkedUserId) {
            // Find the user message element with this messageId
            const userMsgEl = _chatMessages.querySelector(`.user-message[data-message-id="${linkedUserId}"]`);
            prompt = userMsgEl?.querySelector('.text-body')?.innerText;
        }

        // Also check if the AI message stores the original prompt
        if (!prompt && msgEl?.dataset?.userPrompt) {
            prompt = msgEl.dataset.userPrompt;
        }

        // Fallback: last user message
        if (!prompt) {
            const userMessages = _chatMessages.querySelectorAll('.user-message');
            prompt = userMessages[userMessages.length - 1]?.querySelector('.text-body')?.innerText;
        }

        if (prompt) {
            // Remove the current AI response
            msgEl.remove();
            const ci = document.getElementById('chat-search-input');
            if (ci) ci.value = prompt;
            handleSend();
        }
    } else if (action === 'like') {
        btn.classList.toggle('liked');
        const icon = btn.querySelector('.material-symbols-outlined');
        if (icon) icon.textContent = btn.classList.contains('liked') ? 'thumb_up' : 'thumb_up_off_alt';
        const dislikeBtn = btn.parentElement?.querySelector('[data-action="dislike"]');
        if (dislikeBtn?.classList.contains('disliked')) {
            dislikeBtn.classList.remove('disliked');
            const di = dislikeBtn.querySelector('.material-symbols-outlined');
            if (di) di.textContent = 'thumb_down_off_alt';
        }
    } else if (action === 'dislike') {
        btn.classList.toggle('disliked');
        const icon = btn.querySelector('.material-symbols-outlined');
        if (icon) icon.textContent = btn.classList.contains('disliked') ? 'thumb_down' : 'thumb_down_off_alt';
        const likeBtn = btn.parentElement?.querySelector('[data-action="like"]');
        if (likeBtn?.classList.contains('liked')) {
            likeBtn.classList.remove('liked');
            const li = likeBtn.querySelector('.material-symbols-outlined');
            if (li) li.textContent = 'thumb_up_off_alt';
        }
    }
}

function handleUserAction(btn) {
    const action = btn.dataset.action;
    const msgEl = btn.closest('.message');
    const msgContent = msgEl?.querySelector('.message-content');

    if (action === 'edit-user') {
        // ── EDIT: Convert message to editable textarea ──
        const textBody = msgContent?.querySelector('.text-body');
        const actionsInline = msgContent?.querySelector('.message-actions-inline');
        if (!textBody) return;

        const originalText = textBody.textContent;
        const editContainer = document.createElement('div');
        editContainer.className = 'user-edit-container';
        editContainer.innerHTML = `
            <textarea class="user-edit-box" style="width: 100%; min-width: 250px; min-height: 80px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 8px; padding: 12px; font-family: inherit; font-size: 14px; outline: none; resize: vertical; margin-bottom: 8px;">${originalText}</textarea>
            <div class="user-edit-actions" style="display: flex; gap: 8px; justify-content: flex-end;">
                <button class="edit-cancel-btn" type="button" style="padding: 6px 12px; background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); border-radius: 6px; cursor: pointer; transition: all 0.2s;">Cancel</button>
                <button class="edit-save-btn" type="button" style="padding: 6px 14px; background: var(--primary); color: #fff; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; transition: all 0.2s;">Save & Submit</button>
            </div>
        `;

        // Hide original content
        textBody.style.display = 'none';
        if (actionsInline) actionsInline.style.display = 'none';
        msgContent.insertBefore(editContainer, textBody);

        const textarea = editContainer.querySelector('.user-edit-box');
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        // Cancel
        editContainer.querySelector('.edit-cancel-btn').addEventListener('click', () => {
            editContainer.remove();
            textBody.style.display = '';
            if (actionsInline) actionsInline.style.display = '';
        });

        // Save & Resend
        editContainer.querySelector('.edit-save-btn').addEventListener('click', () => {
            const newText = textarea.value.trim();
            if (!newText) return;

            // Update the message text
            textBody.textContent = newText;
            editContainer.remove();
            textBody.style.display = '';
            if (actionsInline) actionsInline.style.display = 'flex';

            // Remove all subsequent messages (the AI response to this message and anything after)
            let next = msgEl.nextElementSibling;
            while (next) {
                const toRemove = next;
                next = next.nextElementSibling;
                toRemove.remove();
            }

            // Resend with new text
            const ci = document.getElementById('chat-search-input') || document.getElementById('main-search-input');
            if (ci) ci.value = newText;
            handleSend();
        });

    } else if (action === 'resend-user') {
        // ── RESEND: Just resend the same message ──
        const text = msgContent?.querySelector('.text-body')?.textContent;
        if (!text) return;

        const ci = document.getElementById('chat-search-input') || document.getElementById('main-search-input');
        if (ci) ci.value = text;
        handleSend();
    } else if (action === 'copy-user') {
        const text = msgContent?.querySelector('.text-body')?.innerText;
        if (text) {
            navigator.clipboard.writeText(text).then(() => {
                btn.classList.add('copied');
                const icon = btn.querySelector('.material-symbols-outlined');
                if (icon) icon.textContent = 'check';
                setTimeout(() => {
                    btn.classList.remove('copied');
                    if (icon) icon.textContent = 'content_copy';
                }, 1500);
            });
        }
    }
}

function handleCodeCopy(btn) {
    const wrapper = btn.closest('.code-block-wrapper');
    const codeEl = wrapper?.querySelector('code');
    if (!codeEl) return;

    const rawText = codeEl.textContent;
    navigator.clipboard.writeText(rawText).then(() => {
        const label = btn.querySelector('.code-copy-label');
        const icon = btn.querySelector('.material-symbols-outlined');
        btn.classList.add('copied');
        if (label) label.textContent = 'Copied!';
        if (icon) icon.textContent = 'check';
        setTimeout(() => {
            btn.classList.remove('copied');
            if (label) label.textContent = 'Copy';
            if (icon) icon.textContent = 'content_copy';
        }, 1500);
    });
}

// ── Initialize chat ───────────────────────────────────────────
export function initChat() {
    _chatMessages = document.getElementById('chat-messages');
    _chatInterface = document.getElementById('chat-interface');
    _heroSection = document.querySelector('.hero');
    _searchInput = document.getElementById('main-search-input');

    const sendBtn = document.getElementById('main-send-btn');
    const chatSearchInput = document.getElementById('chat-search-input');
    const chatSendBtn = document.getElementById('chat-send-btn');

    // Send button clicks
    if (sendBtn) sendBtn.addEventListener('click', handleSend);
    if (chatSendBtn) chatSendBtn.addEventListener('click', handleSend);

    // Enter to send
    if (_searchInput) {
        _searchInput.addEventListener('input', () => autoResize(_searchInput));
        _searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
        });
    }

    if (chatSearchInput) {
        chatSearchInput.addEventListener('input', () => autoResize(chatSearchInput));
        chatSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
        });
    }

    // Auto resize on load
    if (_searchInput) autoResize(_searchInput);
    if (chatSearchInput) autoResize(chatSearchInput);

    // Bind message action buttons (delegated)
    bindMessageActions();
}

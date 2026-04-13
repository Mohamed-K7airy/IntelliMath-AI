// ============================================================
// Study Mode — Sphinx-SCA  (FIXED v6)
// ============================================================
// FIX 1: extractContent() — maps all backend response keys to text
// FIX 2: البطء — حذف الـ pre-solve من أول رسالة، classify بيحصل
//         locally (بدون API call)، الـ correct_answer بتتجيب
//         lazy (بعد ما المستخدم يكتب إجابة)
// FIX 3: الـ hint/solve buttons بتظهر "Session updated" لأن
//         data.display_markdown كان undefined → استخدم extractContent
// ============================================================

import { supabase } from './supabaseClient.js';
import { initMarkdown, formatMessage } from './lib/markdown.js';
import { initCalculator, initMathToolbar, initGraph } from './lib/ui.js';

// ── State ─────────────────────────────────────────────────────
const state = {
    timerMode: 'work',
    workDuration: 25 * 60,
    breakDuration: 5 * 60,
    timeRemaining: 25 * 60,
    isRunning: false,
    isFreeTimer: false,
    freeTimerElapsed: 0,
    timerInterval: null,
    sessionsCompleted: 0,
    totalDuration: 25 * 60,

    tasks: [],
    notes: [],

    currentMode: 'study',
    isStreaming: false,
    isChatActive: false,
    currentSessionId: null,
    currentUserId: null,

    uploadedImageUrl: null,
    isUploading: false,

    // Study Agent Session
    activeStudySessionId: null,
    studyCorrectAnswer: null,
    studyOriginalQuestion: null,
    studyBranch: "algebra",
    studyHintsUsed: 0,
    studyDifficulty: "medium",
    studyProblemsSolved: 0,
    studyStreak: 0
};

const $ = (id) => document.getElementById(id);

// ══════════════════════════════════════════════════════════════
// FIX 1: UNIVERSAL CONTENT EXTRACTOR
// Backend returns different keys per endpoint — map them all here
// ══════════════════════════════════════════════════════════════
function extractContent(data) {
    if (!data || typeof data !== 'object') return '';

    // Priority order: explicit display field → specific content fields → fallback
    return (
        data.display_markdown ||   // fast paths (chat, explain, help)
        data.concept_explanation ||   // /study/start → explain node
        data.socratic_question ||   // /study/start → socratic node
        data.solve_output ||   // /study/solve
        data.hint_text ||   // /study/hint
        data.mistake_feedback ||   // /study/check (wrong answer)
        data.practice_problem ||   // /study/next, /study/next_harder
        data.session_summary ||   // /study/summary
        data.message ||   // generic fallback
        ''
    );
}

// Combine multiple fields when a response has more than one meaningful piece
function extractStartContent(data) {
    const parts = [];
    if (data.concept_explanation) parts.push(data.concept_explanation);
    if (data.socratic_question) parts.push(data.socratic_question);
    if (data.solve_output) parts.push(data.solve_output);
    return parts.join('\n\n') || extractContent(data);
}

function extractCheckContent(data) {
    const parts = [];
    if (data.mistake_feedback) parts.push(data.mistake_feedback);
    if (data.socratic_question) parts.push(data.socratic_question);
    if (data.practice_problem) parts.push(data.practice_problem);
    return parts.join('\n\n') || extractContent(data);
}

// ── Auth & History ───────────────────────────────────────────

async function initAuthAndHistory() {
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
        state.currentUserId = session.user.id;
        fetchHistory(session.user.id);
    }
    supabase.auth.onAuthStateChange(async (event, session) => {
        if (session) {
            state.currentUserId = session.user.id;
            fetchHistory(session.user.id);
        } else {
            state.currentUserId = null;
            const historyList = $('sidebar-history-list');
            if (historyList) historyList.innerHTML = '<li class="history-item" style="padding:10px; color:var(--text-muted);">Log in to see history</li>';
        }
    });

    const themeBtn = $('theme-toggle-btn');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark-theme');
            document.body.classList.toggle('dark-theme', isDark);
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            const icon = themeBtn.querySelector('.theme-icon');
            if (icon) icon.textContent = isDark ? 'light_mode' : 'dark_mode';
        });
        const icon = themeBtn.querySelector('.theme-icon');
        if (icon) icon.textContent = document.documentElement.classList.contains('dark-theme') ? 'light_mode' : 'dark_mode';
    }

    $('sidebar-toggle-btn')?.addEventListener('click', () => $('main-sidebar')?.classList.toggle('collapsed'));
    $('toggle-right-panel')?.addEventListener('click', () => $('study-right-sidebar')?.classList.toggle('collapsed'));
    $('close-right-panel')?.addEventListener('click', () => $('study-right-sidebar')?.classList.add('collapsed'));
    $('open-right-panel')?.addEventListener('click', () => $('study-right-sidebar')?.classList.remove('collapsed'));
    $('sidebar-overlay')?.addEventListener('click', () => {
        $('main-sidebar')?.classList.add('collapsed');
        $('sidebar-overlay')?.classList.remove('active');
    });
}

async function fetchHistory(userId) {
    const historyList = $('sidebar-history-list');
    if (!historyList) return;
    try {
        const { data: messages, error } = await supabase
            .from('messages').select('*').eq('user_id', userId)
            .order('created_at', { ascending: false }).limit(50);
        if (error) throw error;

        historyList.innerHTML = '';
        const seenSessions = new Set();
        const topSessions = [];
        messages?.forEach(msg => {
            if (msg.session_id && !seenSessions.has(msg.session_id)) {
                seenSessions.add(msg.session_id);
                topSessions.push(msg);
            }
        });

        if (topSessions.length === 0) {
            historyList.innerHTML = '<li style="padding:10px; color:var(--text-muted); font-size:12px;">No recent chats</li>';
            return;
        }
        topSessions.slice(0, 10).forEach(session => {
            const li = document.createElement('li');
            li.className = 'history-item';
            li.innerHTML = `<a href="#" class="history-link" data-id="${session.session_id}"><span class="history-text">${escapeHtml(session.content)}</span></a>`;
            li.querySelector('.history-link').addEventListener('click', (e) => { e.preventDefault(); loadSession(session.session_id); });
            historyList.appendChild(li);
        });
    } catch (err) { console.error('History fetch error:', err); }
}

async function loadSession(sessionId) {
    state.currentSessionId = sessionId;
    state.isChatActive = true;
    $('study-hero').style.display = 'none';
    $('study-chat-active').style.display = 'flex';
    try {
        const { data: messages, error } = await supabase
            .from('messages').select('*').eq('session_id', sessionId)
            .order('created_at', { ascending: true });
        if (error) throw error;
        const chatContainer = $('chat-messages');
        chatContainer.innerHTML = '';
        messages.forEach(msg => addMessage(msg.content, msg.sender, msg.image_url));
    } catch (err) { console.error('Load session error:', err); }
}

async function saveMessageToSupabase(content, sender, imageUrl = null) {
    if (!state.currentUserId || !content) return;
    try {
        const payload = { user_id: state.currentUserId, session_id: state.currentSessionId, content, sender };
        if (imageUrl) payload.image_url = imageUrl;
        await supabase.from('messages').insert([payload]);
        fetchHistory(state.currentUserId);
    } catch (err) { console.error('Save message error:', err); }
}

// ── Image Upload ──────────────────────────────────────────────

function initImageUpload() {
    ['hero', 'chat'].forEach(type => {
        const dropZone = $(`${type}-drop-zone`);
        const input = $(`${type}-drop-zone-input`);
        dropZone?.addEventListener('click', () => input.click());
        input?.addEventListener('change', (e) => { const file = e.target.files[0]; if (file) handleFileUpload(file, type); });
        dropZone?.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) handleFileUpload(file, type);
        });
        $(`${type}-remove-preview-btn`)?.addEventListener('click', () => {
            state.uploadedImageUrl = null;
            const wrapper = $(`${type}-image-preview-wrapper`);
            if (wrapper) {
                wrapper.style.display = 'none';
                wrapper.classList.remove('is-loading', 'is-ready');
            }
            $(`${type}-drop-zone`).style.display = 'block';
            if (input) input.value = '';
        });
    });
}

let uploadTimeout;

async function handleFileUpload(file, type) {
    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
        alert('Please upload an image or PDF file.');
        return;
    }

    if (uploadTimeout) clearTimeout(uploadTimeout);
    state.isUploading = true;
    const previewWrapper = $(`${type}-image-preview-wrapper`);
    const previewImg = $(`${type}-image-preview-thumbnail`);
    const dropZone = $(`${type}-drop-zone`);

    if (previewWrapper) {
        previewWrapper.style.display = 'flex';
        previewWrapper.classList.add('is-loading');
        previewWrapper.classList.remove('is-ready');
    }

    // Show image immediately if possible
    if (previewImg) {
        if (file.type === 'application/pdf') {
            previewImg.src = 'logo.png';
        } else {
            previewImg.src = URL.createObjectURL(file);
        }
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        // We still use the base64 result for state.uploadedImageUrl as expected by the backend logic
        state.uploadedImageUrl = e.target.result;

        // Small simulated delay for modern UX feel (so spinner is visible)
        uploadTimeout = setTimeout(() => {
            if (previewWrapper) {
                previewWrapper.classList.remove('is-loading');
                previewWrapper.classList.add('is-ready');
            }
            state.isUploading = false;
            uploadTimeout = null;
        }, 800);
    };

    reader.readAsDataURL(file);
}

// ── Chat & Mode Logic ─────────────────────────────────────────

function initChat() {
    const heroTabs = document.querySelectorAll('.gpt-tab');
    heroTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            heroTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.currentMode = tab.dataset.mode;
            syncModeUI(state.currentMode);
        });
    });

    ['hero', 'chat'].forEach(type => {
        const sendBtn = $(`${type}-send-btn`);
        const input = $(`${type}-search-input`);
        sendBtn?.addEventListener('click', () => handleSend(type));
        input?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(type); } });
        input?.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = input.scrollHeight + 'px'; });
    });

    initModeDropdowns();
    bindStudyChatActions();
    initCalculator();
    initMathToolbar();
    initGraph();

    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const topic = card.dataset.topic;
            const prompt = card.dataset.prompt;
            state.studyBranch = topic;
            state.currentMode = 'study';
            syncModeUI('study');
            const heroInput = $('hero-search-input');
            if (heroInput) heroInput.value = prompt;
            handleSend('hero');
        });
    });

    document.querySelectorAll('.quick-action-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const action = pill.dataset.action;
            state.currentMode = 'study';
            syncModeUI('study');
            const heroInput = $('hero-search-input');
            if (action === 'problem' && heroInput) heroInput.focus();
            else if (action === 'explain' && heroInput) heroInput.focus();
        });
    });

    const heroMathToggle = $('hero-math-keyboard-toggle');
    const mathToolbar = $('math-toolbar');
    if (heroMathToggle && mathToolbar) {
        heroMathToggle.addEventListener('click', () => {
            const isVisible = mathToolbar.classList.toggle('visible');
            heroMathToggle.classList.toggle('active', isVisible);
            const chatMathToggle = $('chat-math-keyboard-toggle');
            if (chatMathToggle) chatMathToggle.classList.toggle('active', isVisible);
        });
    }

    const heroGraphToggle = $('hero-tool-create-graph');
    if (heroGraphToggle && window.toggleGraphBar) heroGraphToggle.addEventListener('click', window.toggleGraphBar);
    const chatGraphToggle = $('chat-tool-create-graph');
    if (chatGraphToggle && window.toggleGraphBar) chatGraphToggle.addEventListener('click', window.toggleGraphBar);

    let graphCounter = 0;
    const plotBtn = $('graph-bar-plot-btn');
    if (plotBtn) {
        plotBtn.addEventListener('click', () => {
            const fnInput = $('fn-input');
            const expr = fnInput?.value?.trim();
            if (!expr) return;
            $('graph-input-bar').style.display = 'none';
            fnInput.value = '';
            transitionToChat();
            const bubbleId = `ggb-study-${++graphCounter}`;
            const chatMessages = $('chat-messages');
            saveMessageToSupabase(`📈 Plotting function: ${expr}`, 'user');
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', 'ai-message');
            msgDiv.innerHTML = `
                <div class="message-avatar"><img src="logo.png" alt="AI"></div>
                <div class="message-content" style="max-width:600px; width:100%;">
                    <div class="ai-name">Sphinx-SCA</div>
                    <div style="padding:10px 14px; font-size:13px; font-family:monospace; color:#e94560;">📈 f(x) = ${expr}</div>
                    <div style="border-radius:12px; overflow:hidden; border:1px solid #e0e0e0; background:#ffffff;">
                        <div id="${bubbleId}" style="width:100%; height:420px;"></div>
                    </div>
                </div>`;
            chatMessages.appendChild(msgDiv);
            saveMessageToSupabase(`📈 f(x) = ${expr}`, 'ai');
            const scrollWrapper = $('study-chat-messages-wrapper');
            if (scrollWrapper) scrollWrapper.scrollTop = scrollWrapper.scrollHeight;
            setTimeout(() => {
                const container = document.getElementById(bubbleId);
                if (!container) return;
                const appletParams = {
                    appName: 'graphing', width: container.offsetWidth || 560, height: 420,
                    showToolBar: false, showAlgebraInput: true, showMenuBar: false, enableRightClick: false,
                    appletOnLoad: (api) => api.evalCommand('f(x) = ' + expr),
                };
                if (typeof GGBApplet !== 'undefined') new GGBApplet(appletParams, true).inject(bubbleId);
            }, 300);
        });
    }

    $('graph-bar-close-btn')?.addEventListener('click', () => {
        const bar = $('graph-input-bar');
        if (bar) bar.style.display = 'none';
        const fnInput = $('fn-input');
        if (fnInput) fnInput.value = '';
    });
}

function bindStudyChatActions() {
    const chatMessages = $('chat-messages');
    chatMessages?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const msgEl = btn.closest('.message');
        const msgContent = msgEl?.querySelector('.message-content');

        if (action === 'copy') {
            const text = msgContent?.querySelector('.text-body')?.textContent;
            if (text) navigator.clipboard.writeText(text).catch(() => { });
        } else if (action === 'copy-user') {
            const text = msgContent?.querySelector('.text-body')?.textContent;
            if (text) navigator.clipboard.writeText(text).catch(() => { });
        } else if (action === 'regenerate') {
            const ci = $('chat-search-input');
            if (ci && state.studyOriginalQuestion) {
                ci.value = state.studyOriginalQuestion;
                handleSend('chat');
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
        } else if (action === 'edit-user') {
            const textBody = msgContent?.querySelector('.text-body');
            const actionsInline = msgEl?.querySelector('.message-actions-inline');
            if (!textBody) return;
            const originalText = textBody.textContent;
            const editContainer = document.createElement('div');
            editContainer.className = 'user-edit-container';
            editContainer.innerHTML = `
                <textarea class="user-edit-box" style="width:100%;min-width:250px;min-height:80px;background:var(--bg-primary);border:1px solid var(--border-color);color:var(--text-primary);border-radius:8px;padding:12px;font-family:inherit;font-size:14px;outline:none;resize:vertical;margin-bottom:8px;">${originalText}</textarea>
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button class="edit-cancel-btn" type="button" style="padding:6px 12px;background:transparent;border:1px solid var(--border-color);color:var(--text-secondary);border-radius:6px;cursor:pointer;">Cancel</button>
                    <button class="edit-save-btn" type="button" style="padding:6px 14px;background:var(--primary);color:#fff;border:none;border-radius:6px;font-weight:500;cursor:pointer;">Save & Submit</button>
                </div>`;
            textBody.style.display = 'none';
            if (actionsInline) actionsInline.style.display = 'none';
            textBody.parentNode.insertBefore(editContainer, textBody);
            const textarea = editContainer.querySelector('textarea');
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
            editContainer.querySelector('.edit-cancel-btn').addEventListener('click', () => {
                editContainer.remove(); textBody.style.display = '';
                if (actionsInline) actionsInline.style.display = 'flex';
            });
            editContainer.querySelector('.edit-save-btn').addEventListener('click', () => {
                const newText = textarea.value.trim();
                if (!newText) return;
                textBody.textContent = newText;
                editContainer.remove();
                textBody.style.display = '';
                if (actionsInline) actionsInline.style.display = 'flex';
                const ci = $('chat-search-input');
                if (ci) ci.value = newText;
                let next = msgEl.nextElementSibling;
                while (next) { const toRemove = next; next = next.nextElementSibling; toRemove.remove(); }
                handleSend('chat');
            });
        } else if (action === 'resend-user') {
            const text = msgContent?.querySelector('.text-body')?.textContent;
            if (text) { const ci = $('chat-search-input'); if (ci) ci.value = text; handleSend('chat'); }
        }
    });
}

function initModeDropdowns() {
    ['hero', 'chat'].forEach(type => {
        const btn = $(`${type}-mode-btn`) || $(`${type}-mode-dropdown-btn`);
        const menu = $(`${type}-mode-dropdown-menu`);
        btn?.addEventListener('click', (e) => { e.stopPropagation(); menu.classList.toggle('active'); });
        menu?.querySelectorAll('.mode-option').forEach(opt => {
            opt.addEventListener('click', () => { state.currentMode = opt.dataset.mode; syncModeUI(state.currentMode); menu.classList.remove('active'); });
        });
    });
    document.addEventListener('click', () => document.querySelectorAll('.mode-dropdown-menu').forEach(m => m.classList.remove('active')));
}

function syncModeUI(mode) {
    document.querySelectorAll('.gpt-tab').forEach(t => t.classList.toggle('active', t.dataset.mode === mode));
    ['hero', 'chat'].forEach(type => {
        const btn = $(`${type}-mode-btn`) || $(`${type}-mode-dropdown-btn`);
        if (!btn) return;
        const text = btn.querySelector('.dropdown-text');
        const icon = btn.querySelector('.dropdown-icon');
        const label = mode === 'think' ? 'Deep Think' : (mode === 'steps' ? 'Steps' : (mode === 'study' ? 'Study Agent' : 'General'));
        const iconName = mode === 'think' ? 'psychology' : (mode === 'steps' ? 'format_list_numbered' : (mode === 'study' ? 'school' : 'auto_awesome'));
        if (text) text.textContent = label;
        if (icon) icon.textContent = iconName;
        $(`${type}-mode-dropdown-menu`)?.querySelectorAll('.mode-option').forEach(opt => opt.classList.toggle('active', opt.dataset.mode === mode));
    });
}

function transitionToChat() {
    if (!state.isChatActive) {
        state.isChatActive = true;
        const studyHero = $('study-hero');
        const studyChat = $('study-chat-active');
        if (studyHero) studyHero.style.display = 'none';
        if (studyChat) studyChat.style.display = 'flex';
    }
    if (!state.currentSessionId) state.currentSessionId = generateUUID();
}

// ══════════════════════════════════════════════════════════════
// MAIN SEND
// ══════════════════════════════════════════════════════════════

async function handleSend(type) {
    if (state.isStreaming) return;
    const input = $(`${type}-search-input`);
    const text = input?.value?.trim() || '';  // ✅ FIX (W-09): null-safe access
    const imageUrl = state.uploadedImageUrl;
    if (!text && !imageUrl) return;

    if (state.currentMode === 'study') return handleStudySend(text, imageUrl, type);

    transitionToChat();
    input.value = '';
    input.style.height = 'auto';
    const previewWrapper = $(`${type}-image-preview-wrapper`);
    if (previewWrapper) {
        previewWrapper.style.display = 'none';
        previewWrapper.classList.remove('is-loading', 'is-ready');
    }
    state.uploadedImageUrl = null;
    const dropZoneInput = $(`${type}-drop-zone-input`);
    if (dropZoneInput) dropZoneInput.value = '';

    addMessage(text, 'user', imageUrl);
    saveMessageToSupabase(text || '📷 Image Message', 'user', imageUrl);

    const aiMsgDiv = addMessage('', 'ai');
    const aiTextDiv = aiMsgDiv.querySelector('.text-body');
    aiTextDiv.innerHTML = `
        <div class="stream-skeleton" data-role="skeleton">
            <div class="skeleton skeleton-line" style="width:70%"></div>
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-line" style="width:45%"></div>
        </div>`;

    state.isStreaming = true;
    let fullResponse = '';
    let gotFirstToken = false;

    try {
        const API_URL = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '') : (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');
        const response = await fetch(`${API_URL}/solve_stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text || 'Solve this math problem from the image.', image_data: imageUrl, mode: state.currentMode, session_id: state.currentSessionId, user_id: state.currentUserId })
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (dataStr === '[DONE]') return;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.content) {
                            if (!gotFirstToken) { gotFirstToken = true; aiTextDiv.querySelector('[data-role="skeleton"]')?.remove(); }
                            fullResponse += data.content;
                            aiTextDiv.innerHTML = formatMessage(fullResponse) + '<span class="typing-cursor" aria-hidden="true"></span>';
                            const wrapper = $('study-chat-messages-wrapper');
                            wrapper.scrollTop = wrapper.scrollHeight;
                        }
                    } catch (e) { }
                }
            });
        }
        if (fullResponse) saveMessageToSupabase(fullResponse, 'ai');
    } catch (err) {
        aiTextDiv.innerHTML = '<span style="color:var(--primary);">Error connecting to server. Please try again.</span>';
    } finally {
        state.isStreaming = false;
        aiTextDiv.innerHTML = formatMessage(fullResponse);
    }
}

// ══════════════════════════════════════════════════════════════
// STUDY SEND — FIXED
// ══════════════════════════════════════════════════════════════

async function handleStudySend(text, imageUrl, type) {
    const input = $(`${type}-search-input`);
    input.value = '';
    input.style.height = 'auto';
    const previewWrapper = $(`${type}-image-preview-wrapper`);
    if (previewWrapper) previewWrapper.style.display = 'none';
    const dropZone = $(`${type}-drop-zone`);
    if (dropZone) dropZone.style.display = 'block';
    state.uploadedImageUrl = null;
    const dropZoneInput = $(`${type}-drop-zone-input`);
    if (dropZoneInput) dropZoneInput.value = '';

    transitionToChat();
    addMessage(text, 'user', imageUrl);
    saveMessageToSupabase(text, 'user', imageUrl);

    const aiMsgDiv = addMessage('', 'ai');
    const aiTextDiv = aiMsgDiv.querySelector('.text-body');
    showSkeleton(aiTextDiv);

    state.isStreaming = true;
    const API_URL = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '') : (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

    try {
        // ── FIX 2: Classify LOCALLY — no API call needed ──────────
        // The backend classify endpoint is slow (LLM call).
        // We use the same fast regex logic here in JS.
        const intent = classifyIntentLocal(text);

        // ── FAST PATHS ────────────────────────────────────────────
        if (intent === 'casual') {
            const res = await fetch(`${API_URL}/study/chat`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, user_id: state.currentUserId })
            });
            const data = await res.json();
            const content = extractContent(data);
            aiTextDiv.innerHTML = formatMessage(content);
            saveMessageToSupabase(content, 'ai');
            state.isStreaming = false;
            return;
        }

        if (intent === 'explain' && !state.activeStudySessionId) {
            const res = await fetch(`${API_URL}/study/explain`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, branch: state.studyBranch, user_id: state.currentUserId })
            });
            const data = await res.json();
            const content = extractContent(data);
            aiTextDiv.innerHTML = formatMessage(content);
            saveMessageToSupabase(content, 'ai');
            state.isStreaming = false;
            return;
        }

        if (intent === 'help' && !state.activeStudySessionId) {
            const res = await fetch(`${API_URL}/study/help`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, branch: state.studyBranch, user_id: state.currentUserId })
            });
            const data = await res.json();
            const content = extractContent(data);
            aiTextDiv.innerHTML = formatMessage(content);
            saveMessageToSupabase(content, 'ai');
            state.isStreaming = false;
            return;
        }

        // ── GIVE UP / SHOW ANSWER ─────────────────────────────────
        if (intent === 'giveup' && state.activeStudySessionId) {
            const res = await fetch(`${API_URL}/study/solve`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
            });
            const data = await res.json();
            const content = extractContent(data);
            aiTextDiv.innerHTML = formatMessage(content);
            appendStudyActions(aiMsgDiv, 'solved');
            saveMessageToSupabase(content, 'ai');
            state.isStreaming = false;
            return;
        }

        // ── NEW SESSION ───────────────────────────────────────────
        if (!state.activeStudySessionId) {
            state.studyOriginalQuestion = text;
            state.studyBranch = state.studyBranch || 'algebra';
            state.studyHintsUsed = 0;
            state.studyCorrectAnswer = '';   // will be fetched lazily

            // FIX 2: REMOVED /solve pre-call — was causing ~3-4s extra delay
            // Correct answer is now fetched lazily when student submits first attempt

            const startRes = await fetch(`${API_URL}/study/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, branch: state.studyBranch, user_id: state.currentUserId })
            });
            const startData = await startRes.json();

            state.activeStudySessionId = startData.session_id;
            state.studyDifficulty = startData.difficulty || 'medium';

            // FIX 1: Use extractStartContent to combine concept + socratic
            const content = extractStartContent(startData);
            aiTextDiv.innerHTML = formatMessage(content || 'Ready! Take a look at the problem. 🎯');

            const wasAutoSolved = !!(startData.solve_output) || startData.next_phase === 'practice' || state.studyDifficulty === 'easy';
            appendStudyActions(aiMsgDiv, wasAutoSolved ? 'solved' : 'active');
            saveMessageToSupabase(content, 'ai');

        } else {
            // ── STUDENT ANSWER CHECK ──────────────────────────────
            // Lazy fetch correct answer if we don't have it yet
            if (!state.studyCorrectAnswer) {
                try {
                    const solveRes = await fetch(`${API_URL}/solve`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: state.studyOriginalQuestion, mode: 'general', user_id: state.currentUserId })
                    });
                    const solveData = await solveRes.json();
                    state.studyCorrectAnswer = typeof solveData.final_answer === 'object'
                        ? JSON.stringify(solveData.final_answer)
                        : (solveData.final_answer || '');
                } catch (e) {
                    console.warn('[Study] Could not fetch correct answer lazily:', e);
                }
            }

            const checkRes = await fetch(`${API_URL}/study/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.activeStudySessionId,
                    question: state.studyOriginalQuestion,
                    branch: state.studyBranch,
                    student_answer: text,
                    correct_answer: state.studyCorrectAnswer,
                    user_id: state.currentUserId
                })
            });
            const checkData = await checkRes.json();

            // FIX 1: extractCheckContent combines feedback + socratic question
            const content = extractCheckContent(checkData);
            aiTextDiv.innerHTML = formatMessage(content || 'Let me think about that... 💭');

            if (checkData.is_correct || checkData.next_phase === 'practice' || checkData.next_phase === 'summary') {
                state.studyProblemsSolved++;
                state.studyStreak++;
                appendStudyActions(aiMsgDiv, 'solved');
            } else {
                appendStudyActions(aiMsgDiv, 'active');
            }
            saveMessageToSupabase(content, 'ai');
        }

    } catch (err) {
        console.error('[Study] Error:', err);
        aiTextDiv.innerHTML = '<span style="color:var(--primary);">Error connecting to study server. Please try again.</span>';
    } finally {
        state.isStreaming = false;
        const wrapper = $('study-chat-messages-wrapper');
        if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
    }
}

// ══════════════════════════════════════════════════════════════
// FIX 2: LOCAL INTENT CLASSIFIER
// Replaces the /study/classify API call — runs instantly, no latency
// Same logic as study_llm.py classify_intent()
// ══════════════════════════════════════════════════════════════
function classifyIntentLocal(text) {
    const t = text.trim().toLowerCase();

    // Math operators / expressions → study
    if (/[\d]+\s*[+\-*/^=×÷]\s*[\d]/.test(t)) return 'study';
    if (/[a-zA-Z]\s*[+\-*/^=]/.test(t)) return 'study';
    if (/\\frac|\\sqrt|\\int|\\sum/.test(t)) return 'study';
    if (/\d+x|\d+y|\d+z/.test(t)) return 'study';

    // Give-up
    if (/i give up|show.?solution|show.?answer|استسلم|وريني الحل|ورني الحل|حل لي|حلها/.test(t)) return 'giveup';

    // Help / confused
    if (/مش فاهم|مش عارف|لا أفهم|لا افهم|ساعدني|help me|confused|stuck|i.?m lost|don.?t understand/.test(t)) return 'help';

    // Explain / theory
    if (/explain|اشرح|وضح|فهمني|ايه هو|what is|what are|يعني ايه|definition|concept/.test(t)) return 'explain';

    // Casual
    if (/^(hi|hello|hey|مرحبا|اهلا|السلام|ازيك|صباح|مساء|شكرا|thanks|bye|كيفك|عامل ايه|how are you|who are you|what can you do)[\s!?.]*$/.test(t)) return 'casual';

    // Math words (Arabic + English)
    if (/solve|حل|factor|simplify|differentiate|integrate|calculate|find|evaluate|compute|limit|derive|prove|احسب|بسّط|اشتق|تكامل|عامل|حدد/.test(t)) return 'study';

    // Short text, no math → casual
    if (t.length < 20 && !/[+\-*/=^()[\]{}]/.test(t)) return 'casual';

    return 'study';
}

// ══════════════════════════════════════════════════════════════
// STUDY ACTION BUTTONS
// ══════════════════════════════════════════════════════════════

function appendStudyActions(aiMsgDiv, mode = 'active') {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'study-actions';
    const API_URL = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '') : (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

    if (mode === 'active') {
        // ── HINT BUTTON ──
        if (state.studyHintsUsed < 3) {
            const hintBtn = document.createElement('button');
            hintBtn.className = 'study-action-btn hint-btn';
            const remaining = 3 - state.studyHintsUsed;
            hintBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px">lightbulb</span> Hint (${remaining} left)`;
            hintBtn.addEventListener('click', async () => {
                if (state.isStreaming) return;
                state.isStreaming = true;
                hintBtn.disabled = true;
                hintBtn.style.opacity = '0.5';
                const hintMsgDiv = addMessage('', 'ai');
                const hintTextDiv = hintMsgDiv.querySelector('.text-body');
                showSkeleton(hintTextDiv);
                try {
                    const res = await fetch(`${API_URL}/study/hint`, {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
                    });
                    const data = await res.json();
                    // FIX 1: use extractContent
                    const content = extractContent(data);
                    state.studyHintsUsed = 3 - (data.hints_remaining ?? (3 - state.studyHintsUsed - 1));
                    hintTextDiv.innerHTML = formatMessage(content || '💡 Think about the next step...');
                    appendStudyActions(hintMsgDiv, state.studyHintsUsed >= 3 ? 'hints-done' : 'active');
                    saveMessageToSupabase(content, 'ai');
                } catch (e) {
                    hintTextDiv.innerHTML = 'Error getting hint.';
                } finally {
                    state.isStreaming = false;
                    $('study-chat-messages-wrapper')?.scrollTo({ top: 999999, behavior: 'smooth' });
                }
            });
            actionsDiv.appendChild(hintBtn);
        }

        // ── SOLVE BUTTON ──
        const solveBtn = document.createElement('button');
        solveBtn.className = 'study-action-btn solve-btn';
        solveBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px">bolt</span> Solve`;
        solveBtn.addEventListener('click', async () => {
            if (state.isStreaming) return;
            state.isStreaming = true;
            solveBtn.disabled = true;
            solveBtn.style.opacity = '0.5';
            const solveMsgDiv = addMessage('', 'ai');
            const solveTextDiv = solveMsgDiv.querySelector('.text-body');
            showSkeleton(solveTextDiv);
            try {
                const res = await fetch(`${API_URL}/study/solve`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
                });
                const data = await res.json();
                // FIX 1: use extractContent
                const content = extractContent(data);
                solveTextDiv.innerHTML = formatMessage(content || 'Could not generate solution.');
                appendStudyActions(solveMsgDiv, 'solved');
                saveMessageToSupabase(content, 'ai');
            } catch (e) {
                solveTextDiv.innerHTML = 'Error solving.';
            } finally {
                state.isStreaming = false;
                $('study-chat-messages-wrapper')?.scrollTo({ top: 999999, behavior: 'smooth' });
            }
        });
        actionsDiv.appendChild(solveBtn);

        // ── END SESSION ──
        actionsDiv.appendChild(makeEndBtn());

    } else if (mode === 'solved') {
        // ── NEXT PROBLEM ──
        const nextBtn = document.createElement('button');
        nextBtn.className = 'study-action-btn next-btn';
        nextBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px">arrow_forward</span> Next Problem`;
        nextBtn.addEventListener('click', () => handleNextProblem(nextBtn, 'next', API_URL));
        actionsDiv.appendChild(nextBtn);

        // ── TRY HARDER ──
        const harderBtn = document.createElement('button');
        harderBtn.className = 'study-action-btn harder-btn';
        harderBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px;color:#f59e0b;">fitness_center</span> Try Harder`;
        harderBtn.addEventListener('click', () => handleNextProblem(harderBtn, 'next_harder', API_URL));
        actionsDiv.appendChild(harderBtn);

        if (state.studyStreak > 1) {
            const streakBadge = document.createElement('span');
            streakBadge.className = 'streak-badge';
            streakBadge.innerHTML = `🔥 ${state.studyStreak} streak`;
            actionsDiv.appendChild(streakBadge);
        }

        actionsDiv.appendChild(makeEndBtn());

    } else if (mode === 'hints-done') {
        // No more hints — just Solve and End
        const solveBtn = document.createElement('button');
        solveBtn.className = 'study-action-btn solve-btn';
        solveBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px">bolt</span> Solve`;
        solveBtn.addEventListener('click', async () => {
            if (state.isStreaming) return;
            state.isStreaming = true;
            solveBtn.disabled = true;
            const solveMsgDiv = addMessage('', 'ai');
            const solveTextDiv = solveMsgDiv.querySelector('.text-body');
            showSkeleton(solveTextDiv);
            try {
                const res = await fetch(`${API_URL}/study/solve`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
                });
                const data = await res.json();
                const content = extractContent(data);
                solveTextDiv.innerHTML = formatMessage(content);
                appendStudyActions(solveMsgDiv, 'solved');
                saveMessageToSupabase(content, 'ai');
            } catch (e) { solveTextDiv.innerHTML = 'Error solving.'; }
            finally { state.isStreaming = false; }
        });
        actionsDiv.appendChild(solveBtn);
        actionsDiv.appendChild(makeEndBtn());
    }

    aiMsgDiv.querySelector('.message-content').appendChild(actionsDiv);
}

// Helper: shared "Next / Harder" handler (avoids duplicate code)
async function handleNextProblem(btn, endpoint, API_URL) {
    if (state.isStreaming) return;
    state.isStreaming = true;
    btn.disabled = true;
    btn.style.opacity = '0.5';
    const nextMsgDiv = addMessage('', 'ai');
    const nextTextDiv = nextMsgDiv.querySelector('.text-body');
    showSkeleton(nextTextDiv);
    try {
        const res = await fetch(`${API_URL}/study/${endpoint}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
        });
        const data = await res.json();
        // FIX 1: use extractContent
        const content = extractContent(data);
        nextTextDiv.innerHTML = formatMessage(content || 'Could not generate problem.');
        saveMessageToSupabase(content, 'ai');

        if (data.practice_problem) {
            state.studyOriginalQuestion = data.practice_problem;
            state.studyCorrectAnswer = '';   // reset for lazy fetch
            state.studyHintsUsed = 0;
        }
        appendStudyActions(nextMsgDiv, 'active');
    } catch (e) {
        nextTextDiv.innerHTML = 'Error getting next problem.';
    } finally {
        state.isStreaming = false;
        $('study-chat-messages-wrapper')?.scrollTo({ top: 999999, behavior: 'smooth' });
    }
}

function makeEndBtn() {
    const endBtn = document.createElement('button');
    endBtn.className = 'study-action-btn end-btn';
    endBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px">stop_circle</span> End Session`;
    endBtn.addEventListener('click', () => handleEndSession());
    return endBtn;
}

async function handleEndSession() {
    if (state.isStreaming) return;
    state.isStreaming = true;
    const summaryMsgDiv = addMessage('', 'ai');
    const summaryTextDiv = summaryMsgDiv.querySelector('.text-body');
    showSkeleton(summaryTextDiv);
    try {
        const API_URL = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '') : (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');
        const res = await fetch(`${API_URL}/study/summary`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.activeStudySessionId, question: state.studyOriginalQuestion, branch: state.studyBranch, user_id: state.currentUserId })
        });
        const data = await res.json();
        // FIX 1: use extractContent
        let content = extractContent(data);
        if (state.studyProblemsSolved > 0) {
            content += `\n\n**Session Stats:** ${state.studyProblemsSolved} problem(s) solved | Best streak: 🔥 ${state.studyStreak}`;
        }
        summaryTextDiv.innerHTML = formatMessage(content);
        saveMessageToSupabase(content, 'ai');
        state.activeStudySessionId = null;
        state.studyHintsUsed = 0;
        state.studyProblemsSolved = 0;
        state.studyStreak = 0;
        state.studyCorrectAnswer = '';
        state.studyOriginalQuestion = null;
    } catch (e) {
        summaryTextDiv.innerHTML = 'Error generating summary.';
    } finally {
        state.isStreaming = false;
        $('study-chat-messages-wrapper')?.scrollTo({ top: 999999, behavior: 'smooth' });
    }
}

// ══════════════════════════════════════════════════════════════
// UI HELPERS
// ══════════════════════════════════════════════════════════════

function showSkeleton(el) {
    el.innerHTML = `
        <div class="stream-skeleton" data-role="skeleton">
            <div class="skeleton skeleton-line" style="width:70%"></div>
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-line" style="width:45%"></div>
        </div>`;
}

function addMessage(text, sender, imageUrl = null) {
    const chatContainer = $('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;

    if (sender === 'ai') {
        msgDiv.innerHTML = `
            <div class="message-avatar"><img src="logo.png"></div>
            <div class="message-content">
                <div class="ai-name">SPHINX-SCA</div>
                <div class="text-body">${formatMessage(text)}</div>
                <div class="message-actions">
                    <button class="action-btn" data-action="copy" title="Copy"><span class="material-symbols-outlined">content_copy</span></button>
                    <button class="action-btn" data-action="regenerate" title="Regenerate"><span class="material-symbols-outlined">refresh</span></button>
                    <button class="action-btn" data-action="like" title="Like"><span class="material-symbols-outlined">thumb_up_off_alt</span></button>
                    <button class="action-btn" data-action="dislike" title="Dislike"><span class="material-symbols-outlined">thumb_down_off_alt</span></button>
                </div>
            </div>`;
    } else {
        msgDiv.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:flex-end;width:100%;">
                <div class="message-content" style="max-width:100%;">
                    ${imageUrl ? `<img src="${escapeHtml(imageUrl)}" class="message-image">` : ''}  
                    <div class="text-body">${escapeHtml(text)}</div>
                </div>
                <div class="message-actions-inline" style="display:flex;gap:4px;align-items:center;margin-top:6px;margin-right:4px;">
                    <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <button class="action-btn" data-action="resend-user" title="Resend"><span class="material-symbols-outlined">refresh</span></button>
                    <button class="action-btn" data-action="edit-user" title="Edit"><span class="material-symbols-outlined">edit</span></button>
                    <button class="action-btn" data-action="copy-user" title="Copy"><span class="material-symbols-outlined">content_copy</span></button>
                </div>
            </div>
            <div class="message-avatar"><img src="user.png"></div>`;
    }

    chatContainer.appendChild(msgDiv);
    const wrapper = $('study-chat-messages-wrapper');
    if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
    return msgDiv;
}

// ── Helpers ───────────────────────────────────────────────────

function generateUUID() { return crypto.randomUUID(); }
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Tools, Notes, Timer — unchanged ──────────────────────────

function initModals() {
    $('welcome-start-btn')?.addEventListener('click', () => $('study-welcome-overlay').classList.remove('active'));
}

function initToolsAndSymbols() {
    const mathSymbolSets = {
        popular: ['π', '∞', '√', '∫', 'Σ', '±', '≠', '≈', '≥', '≤', '÷', '×', 'log', 'ln', 'x²', 'x³', 'xⁿ'],
        trig: ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'θ', 'φ', 'α', 'β'],
        calculus: ['∫', '∬', '∮', 'd/dx', '∂', 'lim', '→', 'Δ', '∇', 'dy/dx'],
        comparison: ['=', '≠', '≈', '≡', '>', '<', '≥', '≤', '≫', '≪'],
        sets: ['∈', '∉', '⊂', '⊃', '⊆', '⊇', '∩', '∪', '∅', 'ℝ', 'ℤ', 'ℕ'],
        arrows: ['→', '←', '↔', '⇒', '⇐', '⇔', '↑', '↓', '⟹', '⟸'],
        greek: ['α', 'β', 'γ', 'δ', 'ε', 'θ', 'λ', 'μ', 'σ', 'τ', 'φ', 'ω', 'Ω', 'Δ'],
    };
    const toolbar = $('math-toolbar');
    const grid = $('math-symbols-grid');
    $('hero-math-keyboard-toggle')?.addEventListener('click', () => toolbar.classList.toggle('active'));
    $('chat-math-keyboard-toggle')?.addEventListener('click', () => toolbar.classList.toggle('active'));
    $('math-toolbar-close')?.addEventListener('click', () => toolbar.classList.remove('active'));
    const renderSymbols = (category) => {
        const symbols = mathSymbolSets[category] || mathSymbolSets.popular;
        grid.innerHTML = symbols.map(s => `<button class="math-sym-btn">${s}</button>`).join('');
        grid.querySelectorAll('.math-sym-btn').forEach(btn => {
            btn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                const activeType = state.isChatActive ? 'chat' : 'hero';
                const input = $(`${activeType}-search-input`);
                if (!input) return;
                const start = input.selectionStart;
                const end = input.selectionEnd;
                const symbol = btn.textContent;
                input.value = input.value.substring(0, start) + symbol + input.value.substring(end);
                input.focus();
                const pos = start + symbol.length;
                input.setSelectionRange(pos, pos);
                input.dispatchEvent(new Event('input'));
            });
        });
    };
    renderSymbols('popular');
    document.querySelectorAll('.math-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.math-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderSymbols(tab.dataset.tab);
        });
    });
}

function initStudyTools() {
    // Timer
    const playBtn = $('timer-play-btn');
    const resetBtn = $('timer-reset-btn');
    const skipBtn = $('timer-skip-btn');

    playBtn?.addEventListener('click', () => state.isRunning ? pauseTimer() : startTimer());
    resetBtn?.addEventListener('click', () => {
        clearInterval(state.timerInterval);
        state.isRunning = false;
        state.timeRemaining = state.workDuration;
        state.freeTimerElapsed = 0;
        const playIcon = $('play-icon');
        if (playIcon) playIcon.textContent = 'play_arrow';
        updateTimerUI();
    });

    skipBtn?.addEventListener('click', () => {
        if (state.isFreeTimer) {
            state.freeTimerElapsed = 0;
        } else {
            // Toggle between work and break or just reset
            state.timeRemaining = 0; 
            // The interval logic will handle session completion in the next tick
        }
        updateTimerUI();
    });

    const timerPlanButtons = document.querySelectorAll('.timer-plan-btn');
    timerPlanButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            timerPlanButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const workMins = parseInt(btn.dataset.work || '0');
            const breakMins = parseInt(btn.dataset.break || '0');
            
            clearInterval(state.timerInterval);
            state.isRunning = false;
            const playIcon = $('play-icon');
            if (playIcon) playIcon.textContent = 'play_arrow';

            if (workMins === 0 && breakMins === 0) {
                state.isFreeTimer = true;
                state.freeTimerElapsed = 0;
            } else {
                state.isFreeTimer = false;
                state.workDuration = workMins * 60;
                state.breakDuration = breakMins * 60;
                state.timeRemaining = state.workDuration;
                state.timerMode = 'work';
            }
            updateTimerUI();
        });
    });

    updateTimerUI();
    initTasks();
    initNotes();
}

function initTasks() {
    const savedTasks = localStorage.getItem('study-tasks');
    if (savedTasks) try { state.tasks = JSON.parse(savedTasks); renderTasks(); } catch (e) { }

    $('task-add-btn')?.addEventListener('click', () => addTask());
    $('task-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') addTask(); });
}

function addTask() {
    const input = $('task-input');
    const text = input?.value?.trim();
    if (!text) return;
    state.tasks.push({ id: Date.now(), text, done: false });
    input.value = '';
    saveTasks(); renderTasks();
}

function toggleTask(id) { state.tasks = state.tasks.map(t => t.id === id ? { ...t, done: !t.done } : t); saveTasks(); renderTasks(); }
function deleteTask(id) { state.tasks = state.tasks.filter(t => t.id !== id); saveTasks(); renderTasks(); }
function saveTasks() { localStorage.setItem('study-tasks', JSON.stringify(state.tasks)); }

function renderTasks() {
    const list = $('tasks-list');
    if (!list) return;
    list.innerHTML = state.tasks.map(task => `
        <li class="task-item ${task.done ? 'done' : ''}" data-id="${task.id}">
            <button class="task-checkbox">${task.done ? '<span class="material-symbols-outlined">check_circle</span>' : '<span class="material-symbols-outlined">radio_button_unchecked</span>'}</button>
            <span class="task-text">${escapeHtml(task.text)}</span>
            <button class="task-delete-btn"><span class="material-symbols-outlined">delete</span></button>
        </li>`).join('');
    list.querySelectorAll('.task-item').forEach(item => {
        const id = parseInt(item.dataset.id);
        item.querySelector('.task-checkbox').addEventListener('click', () => toggleTask(id));
        item.querySelector('.task-delete-btn').addEventListener('click', (e) => { e.stopPropagation(); deleteTask(id); });
    });
}

function initNotes() {
    const savedNotes = localStorage.getItem('study-notes-blocks');
    if (savedNotes) try { state.notes = JSON.parse(savedNotes); renderNotes(); } catch (e) { }
    else {
        const oldNotes = localStorage.getItem('study-notes');
        if (oldNotes?.trim()) { state.notes = [{ id: Date.now(), text: oldNotes }]; saveNotes(); renderNotes(); localStorage.removeItem('study-notes'); }
    }
    $('note-add-btn')?.addEventListener('click', () => addNote());
    $('note-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') addNote(); });
    $('clear-notes-btn')?.addEventListener('click', () => { if (confirm('Clear all notes?')) { state.notes = []; saveNotes(); renderNotes(); } });
}

function addNote() {
    const input = $('note-input');
    const text = input?.value?.trim();
    if (!text) return;
    state.notes.push({ id: Date.now(), text });
    input.value = '';
    saveNotes(); renderNotes();
}

function deleteNote(id) { state.notes = state.notes.filter(n => n.id !== id); saveNotes(); renderNotes(); }
function saveNotes() { localStorage.setItem('study-notes-blocks', JSON.stringify(state.notes)); }
function renderNotes() {
    const list = $('notes-list');
    if (!list) return;
    list.innerHTML = state.notes.map(note => `
        <li class="note-item" data-id="${note.id}">
            <div class="note-icon"><span class="material-symbols-outlined">description</span></div>
            <div class="note-text">${escapeHtml(note.text)}</div>
            <button class="note-delete-btn"><span class="material-symbols-outlined">delete</span></button>
        </li>`).join('');
    list.querySelectorAll('.note-delete-btn').forEach(btn => {
        const id = parseInt(btn.closest('.note-item').dataset.id);
        btn.addEventListener('click', () => deleteNote(id));
    });
}

function startTimer() {
    state.isRunning = true;
    $('play-icon').textContent = 'pause';
    state.timerInterval = setInterval(() => {
        if (state.isFreeTimer) { state.freeTimerElapsed++; updateTimerUI(); }
        else {
            if (state.timeRemaining > 0) { state.timeRemaining--; updateTimerUI(); }
            else { clearInterval(state.timerInterval); state.isRunning = false; $('play-icon').textContent = 'play_arrow'; alert('Timer Finished!'); }
        }
    }, 1000);
}

function pauseTimer() { state.isRunning = false; $('play-icon').textContent = 'play_arrow'; clearInterval(state.timerInterval); }

function updateTimerUI() {
    let displayTime = state.isFreeTimer ? state.freeTimerElapsed : state.timeRemaining;
    $('timer-label').textContent = state.isFreeTimer ? 'Elapsed' : 'Focus';
    const mins = Math.floor(Math.max(0, displayTime) / 60);
    const secs = Math.max(0, displayTime) % 60;
    $('timer-time').textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    const ring = $('timer-ring-progress');
    const circumference = 2 * Math.PI * 100;
    let offset = state.isFreeTimer
        ? circumference * (1 - (state.freeTimerElapsed % 60) / 60)
        : (state.workDuration > 0 ? circumference * (1 - state.timeRemaining / state.workDuration) : circumference);
    ring.style.strokeDashoffset = offset;
}

// ── Bootstrap ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initMarkdown();
    initAuthAndHistory();
    initImageUpload();
    initChat();
    initStudyTools();
    initModals();
    initToolsAndSymbols();
    
    // Auto-collapse right sidebar on mobile
    if (window.innerWidth <= 1200) {
        document.getElementById('study-right-sidebar')?.classList.add('collapsed');
    }
    
    setTimeout(() => { if (!state.isChatActive) { state.currentMode = 'study'; syncModeUI('study'); } }, 100);
});
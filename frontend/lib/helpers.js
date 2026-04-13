// ============================================================
// Utility helpers shared across all frontend modules
// ============================================================

/** Generate a UUID v4. */
export function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/** HH:MM label for the current time. */
export function nowTimeLabel(d = new Date()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Auto-resize a textarea to fit its content (max 180px). */
let _resizeTimeout;
export function autoResize(el) {
    if (!el) return;
    clearTimeout(_resizeTimeout);
    _resizeTimeout = setTimeout(() => {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 180) + 'px';
    }, 30);
}

/** Escape a string for safe HTML insertion. */
export function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/** Escape a string for use in an HTML attribute value. */
export function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

/** Scroll the chat panel to the bottom smoothly */
export function scrollToBottom(el, smooth = true) {
    if (!el) return;
    requestAnimationFrame(() => {
        if (smooth) {
            el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        } else {
            el.scrollTop = el.scrollHeight;
        }
    });
}

// ─── Shared Application State ─────────────────────────────────
export const appState = {
    currentMode: 'general',
    currentUserId: null,
    currentSessionId: generateUUID(),
    isChatActive: false,
    isStreaming: false,
};

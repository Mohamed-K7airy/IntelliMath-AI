// ============================================================
// Markdown + KaTeX + Highlight.js + Code Copy Buttons
// ============================================================
// Dependencies (loaded via CDN <script> tags in index.html):
//   - marked  (global)
//   - katex   (global)
//   - hljs    (global, highlight.js)

import { escapeHtml } from './helpers.js';

let _initialized = false;

/**
 * One-time configuration for the marked renderer.
 * Called once at app startup.
 */
export function initMarkdown() {
    if (_initialized) return;
    _initialized = true;

    if (typeof marked === 'undefined') {
        console.warn('[markdown] marked.js not loaded');
        return;
    }

    marked.setOptions({
        breaks: true,       // Single newline → <br>
        gfm: true,          // GitHub-flavored markdown (tables, strikethrough, etc.)
        headerIds: false,    // Avoid id pollution
        mangle: false,       // Don't mangle emails
        smartypants: false,
        // highlight.js integration: marked calls this for fenced code blocks
        highlight: function (code, lang) {
            if (typeof hljs !== 'undefined') {
                try {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                } catch { /* fall through */ }
            }
            return escapeHtml(code);
        },
    });
}

/**
 * Render a raw AI response string into rich HTML:
 *  1) Protect fenced/inline code from KaTeX processing
 *  2) Render KaTeX (block then inline math)
 *  3) Restore code tokens so marked can handle them
 *  4) Run marked.parse()
 *  5) Post-process: wrap <pre><code> in a container with copy button
 *
 * @param {string} text — raw text (may contain markdown, LaTeX, code)
 * @returns {string} — sanitized HTML string
 */
export function formatMessage(text) {
    if (!text) return '';

    try {
        let s = text;

        // ── Step 1: Extract fenced code blocks ──────────────────────
        const codeBlocks = [];
        s = s.replace(/```([\w]*)\n?([\s\S]*?)```/g, (_m, lang, code) => {
            codeBlocks.push({ lang: lang || '', code });
            return `\n\n%%FENCED_${codeBlocks.length - 1}%%\n\n`;
        });

        // Extract inline code
        const inlineCodes = [];
        s = s.replace(/`([^`\n]+)`/g, (_m, code) => {
            inlineCodes.push(code);
            return `%%INLINE_${inlineCodes.length - 1}%%`;
        });

        // ── Step 2: KaTeX — Block math ──────────────────────────────

        // $$ ... $$ (display)
        s = s.replace(/\$\$([\s\S]*?)\$\$/g, (_m, p1) => {
            try {
                return '\n\n' + katex.renderToString(p1.trim(), { displayMode: true, throwOnError: false }) + '\n\n';
            } catch { return _m; }
        });

        // \[ ... \] (display)
        s = s.replace(/\\\[([\s\S]*?)\\\]/g, (_m, p1) => {
            try {
                return '\n\n' + katex.renderToString(p1.trim(), { displayMode: true, throwOnError: false }) + '\n\n';
            } catch { return _m; }
        });

        // ── Step 3: KaTeX — Inline math ─────────────────────────────

        // \( ... \) (inline)
        s = s.replace(/\\\((.*?)\\\)/gs, (_m, p1) => {
            try {
                return katex.renderToString(p1.trim(), { displayMode: false, throwOnError: false });
            } catch { return _m; }
        });

        // $ ... $ (single-dollar inline, non-greedy)
        // Avoid matching $$ or purely numeric strings like "$5"
        s = s.replace(/(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\$)/g, (_m, p1) => {
            const trimmed = p1.trim();
            // Skip if it looks like a currency value (starts with a digit)
            if (/^\d+([.,]\d+)?$/.test(trimmed)) return _m;
            try {
                return katex.renderToString(trimmed, { displayMode: false, throwOnError: false });
            } catch { return _m; }
        });

        // ── Step 4: Restore code tokens ─────────────────────────────
        // Inline code → backticks (marked will render them properly)
        inlineCodes.forEach((code, i) => {
            s = s.replace(`%%INLINE_${i}%%`, '`' + code + '`');
        });

        // Fenced code → triple backticks (marked will render + highlight)
        codeBlocks.forEach((block, i) => {
            s = s.replace(
                `%%FENCED_${i}%%`,
                '```' + block.lang + '\n' + block.code + '\n```'
            );
        });

        // ── Step 5: Parse Markdown ──────────────────────────────────
        let html = marked.parse(s);

        // ── Step 6: Post-process code blocks — add copy button ──────
        html = html.replace(
            /<pre><code(?: class="language-([\w+#-]*)")?\s*>([\s\S]*?)<\/code><\/pre>/g,
            (_match, lang, code) => {
                const label = lang || 'code';
                // Decode HTML entities for the raw copy text
                const rawText = code
                    .replace(/<[^>]*>/g, '')       // strip highlight spans
                    .replace(/&amp;/g, '&')
                    .replace(/&lt;/g, '<')
                    .replace(/&gt;/g, '>')
                    .replace(/&quot;/g, '"')
                    .replace(/&#039;/g, "'")
                    .replace(/&#39;/g, "'");

                return `<div class="code-block-wrapper" data-raw-code="${escapeHtml(rawText)}">
                    <div class="code-block-header">
                        <span class="code-lang">${escapeHtml(label)}</span>
                        <button class="code-copy-btn" type="button" title="Copy code">
                            <span class="material-symbols-outlined" style="font-size:14px">content_copy</span>
                            <span class="code-copy-label">Copy</span>
                        </button>
                    </div>
                    <pre><code class="language-${lang || ''}">${code}</code></pre>
                </div>`;
            }
        );

        html = `<div dir="auto">${html}</div>`;

        return html;
    } catch (e) {
        console.error('[markdown] formatMessage error:', e);
        return escapeHtml(text);
    }
}

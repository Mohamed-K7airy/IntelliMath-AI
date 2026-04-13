// ============================================================
// UI Components — Sidebar, Theme, Calculator, Math Toolbar,
//                 Mode Dropdown, Graph, Modals
// ============================================================

import { appState, autoResize } from './helpers.js';

// ── Sidebar ───────────────────────────────────────────────────
export function initSidebar() {
    const mainSidebar = document.getElementById('main-sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const mobileLeftMenuBtn = document.getElementById('mobile-left-menu-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebarToggleBtn && mainSidebar) {
        sidebarToggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                mainSidebar.classList.remove('mobile-open');
                if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            } else {
                mainSidebar.classList.toggle('collapsed');
            }
        });
    }

    if (mobileLeftMenuBtn && mainSidebar) {
        mobileLeftMenuBtn.addEventListener('click', () => {
            mainSidebar.classList.add('mobile-open');
            if (sidebarOverlay) sidebarOverlay.classList.add('active');
        });
    }

    if (sidebarOverlay && mainSidebar) {
        sidebarOverlay.addEventListener('click', () => {
            mainSidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('active');
        });
    }
}

// ── Theme ─────────────────────────────────────────────────────
export function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = themeToggleBtn?.querySelector('.theme-icon');

    function updateThemeUI() {
        if (!themeIcon) return;
        const isDark = document.body.classList.contains('dark-theme');
        themeIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
    }
    updateThemeUI();

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.documentElement.classList.toggle('dark-theme');
            document.body.classList.toggle('dark-theme');
            const isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeUI();
        });
    }

    // Profile container touch support (mobile)
    const profileContainer = document.getElementById('nav-profile-container');
    if (profileContainer) {
        profileContainer.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                profileContainer.classList.toggle('active');
            }
        });
    }
}

// ── Mode Dropdown & GPT Tabs ──────────────────────────────────
export function initMode() {
    const modeDropdownBtn = document.getElementById('mode-dropdown-btn');
    const modeDropdownMenu = document.getElementById('mode-dropdown-menu');
    const chatModeBtn = document.getElementById('chat-mode-btn');
    const chatModeMenu = document.getElementById('chat-mode-dropdown-menu');
    const modeOptions = document.querySelectorAll('.mode-option');
    const gptTabs = document.querySelectorAll('.gpt-tab');

    const toggleMenu = (menu, e) => {
        e.stopPropagation();
        document.querySelectorAll('.mode-dropdown-menu').forEach((m) => {
            if (m !== menu) m.classList.remove('active');
        });
        menu.classList.toggle('active');
    };

    if (modeDropdownBtn && modeDropdownMenu) {
        modeDropdownBtn.addEventListener('click', (e) => toggleMenu(modeDropdownMenu, e));
    }
    if (chatModeBtn && chatModeMenu) {
        chatModeBtn.addEventListener('click', (e) => toggleMenu(chatModeMenu, e));
    }

    // Close menus on document click
    document.addEventListener('click', () => {
        document.querySelectorAll('.mode-dropdown-menu').forEach((m) => m.classList.remove('active'));
    });

    // Sync helper: update both dropdown buttons
    function syncModeUI(mode) {
        appState.currentMode = mode;
        const option = Array.from(modeOptions).find((o) => o.dataset.mode === mode);
        if (!option) return;

        const text = option.querySelector('span:last-child').textContent;
        const icon = option.querySelector('.material-symbols-outlined').textContent;

        [modeDropdownBtn, chatModeBtn].forEach((btn) => {
            if (!btn) return;
            const dt = btn.querySelector('.dropdown-text');
            const di = btn.querySelector('.dropdown-icon');
            if (dt) dt.textContent = text;
            if (di) di.textContent = icon;
        });

        modeOptions.forEach((o) => o.classList.toggle('active', o.dataset.mode === mode));
        gptTabs.forEach((t) => t.classList.toggle('active', t.dataset.mode === mode));
    }

    // GPT Tabs click
    gptTabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const mode = tab.dataset.mode;
            if (!mode) {
                // Coming-soon tab
                const modal = document.getElementById('coming-soon-modal');
                if (modal) { modal.classList.add('active'); modal.style.display = 'flex'; }
                return;
            }
            syncModeUI(mode);
        });
    });

    // Mode dropdown options click
    modeOptions.forEach((option) => {
        option.addEventListener('click', () => {
            syncModeUI(option.dataset.mode);
            document.querySelectorAll('.mode-dropdown-menu').forEach((m) => m.classList.remove('active'));
        });
    });
}

// ── Calculator ────────────────────────────────────────────────
export function initCalculator() {
    let calcExpression = '';
    const calcToggleBtn = document.getElementById('chat-calc-toggle');
    const heroCalcToggle = document.getElementById('hero-calc-toggle');
    const calculatorPanel = document.getElementById('calculatorPanel');
    const calcCloseBtn = document.getElementById('calcCloseBtn');

    const toggleCalculator = () => calculatorPanel?.classList.toggle('open');

    if (calcToggleBtn && calculatorPanel) calcToggleBtn.addEventListener('click', toggleCalculator);
    if (heroCalcToggle && calculatorPanel) heroCalcToggle.addEventListener('click', toggleCalculator);

    if (calcCloseBtn && calculatorPanel) {
        calcCloseBtn.addEventListener('click', () => {
            calculatorPanel.classList.remove('open');
            calcExpression = '';
            const display = document.getElementById('calcDisplay');
            if (display) display.textContent = '0';
        });
    }

    // Calculator button clicks via delegation
    document.querySelector('.calc-grid')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.calc-btn');
        if (!btn) return;
        const val = btn.dataset.calc;
        const display = document.getElementById('calcDisplay');

        if (val === 'AC') {
            calcExpression = '';
            display.textContent = '0';
        } else if (val === '⌫') {
            calcExpression = calcExpression.slice(0, -1);
            display.textContent = calcExpression || '0';
        } else if (val === '=') {
            try {
                const expr = calcExpression.replace(/\^/g, '**').replace(/\(-\)/g, '-');
                // ✅ FIX (C-02): Validate expression before evaluating to prevent code injection
                // Only allow digits, operators, parentheses, and decimal points
                if (!/^[\d+\-*/().%e\s]+$/.test(expr)) {
                    display.textContent = 'Invalid';
                    calcExpression = '';
                    return;
                }
                const result = Function('"use strict"; return (' + expr + ')')();
                if (typeof result !== 'number' || !isFinite(result)) {
                    display.textContent = 'Error';
                    calcExpression = '';
                    return;
                }
                display.textContent = parseFloat(result.toFixed(10)).toString();
                calcExpression = display.textContent;
            } catch {
                display.textContent = 'Error';
                calcExpression = '';
            }
        } else {
            calcExpression += val;
            display.textContent = calcExpression;
        }
    });
}

// ── Math Toolbar ──────────────────────────────────────────────
export function initMathToolbar() {
    const mathToolbar = document.getElementById('math-toolbar');
    const heroMathToggle = document.getElementById('math-keyboard-toggle');
    const chatMathToggle = document.getElementById('chat-math-keyboard-toggle');

    const toggleMathToolbar = () => {
        if (!mathToolbar) return;
        const isVisible = mathToolbar.classList.toggle('visible');
        heroMathToggle?.classList.toggle('active', isVisible);
        chatMathToggle?.classList.toggle('active', isVisible);
    };

    const closeMathToolbar = () => {
        if (!mathToolbar) return;
        mathToolbar.classList.remove('visible');
        heroMathToggle?.classList.remove('active');
        chatMathToggle?.classList.remove('active');
    };

    if (heroMathToggle) heroMathToggle.addEventListener('click', toggleMathToolbar);
    if (chatMathToggle) chatMathToggle.addEventListener('click', toggleMathToolbar);

    const mathToolbarClose = document.getElementById('math-toolbar-close');
    if (mathToolbarClose) mathToolbarClose.addEventListener('click', closeMathToolbar);

    // Symbol insertion helper
    function insertSymbol(symbol) {
        const chatVisible = document.getElementById('chat-interface').style.display !== 'none';
        const target = chatVisible
            ? document.getElementById('chat-search-input')
            : document.getElementById('main-search-input');
        if (!target) return;

        const start = target.selectionStart;
        const end = target.selectionEnd;
        const before = target.value.substring(0, start);
        const after = target.value.substring(end);
        target.value = before + symbol + after;
        target.selectionStart = target.selectionEnd = start + symbol.length;
        target.focus();
        autoResize(target);
    }

    // Initial symbol buttons
    document.querySelectorAll('.math-sym-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            if (btn.dataset.insert) insertSymbol(btn.dataset.insert);
        });
    });

    // Tab switching with symbol set replacement
    const mathSymbolSets = {
        popular: ['/', 'x^', 'x_', '√(', '∛(', 'log(', '∫', 'Σ', 'π', '∞', '+', '−', '×', '÷', '!', 'log(', 'ln(', 'x^2', 'x^(-1)', '(n choose k)', '∂', 'e^', 'e^(iπ)', '±'],
        trig: ['sin(', 'cos(', 'tan(', 'sec(', 'csc(', 'cot(', 'arcsin(', 'arccos(', 'arctan(', 'sinh(', 'cosh(', 'tanh('],
        calculus: ['∫', '∬', '∮', 'd/dx', '∂', '∂/∂x', 'lim', '→', 'Δ', '∇', 'dy/dx', "d²y/dx²"],
        comparison: ['≥', '≤', '≠', '≈', '≡', '∝', '<', '>', '≫', '≪'],
        sets: ['∈', '∉', '⊂', '⊃', '⊆', '⊇', '∩', '∪', '∅', 'ℝ', 'ℤ', 'ℕ', 'ℚ'],
        arrows: ['→', '←', '↔', '⇒', '⇐', '⇔', '↑', '↓', '⟹', '⟸'],
        greek: ['α', 'β', 'γ', 'δ', 'ε', 'θ', 'λ', 'μ', 'σ', 'τ', 'φ', 'ω', 'Ω', 'Δ', 'Γ', 'Θ', 'Λ', 'Φ', 'Ψ'],
    };

    const mathTabs = document.querySelectorAll('.math-tab');
    mathTabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            mathTabs.forEach((t) => t.classList.remove('active'));
            tab.classList.add('active');

            const category = tab.dataset.tab;
            const symbols = mathSymbolSets[category] || mathSymbolSets.popular;
            const grid = document.getElementById('math-symbols-grid');
            if (!grid) return;

            grid.innerHTML = symbols
                .map((sym) => {
                    const display = sym.length <= 3 ? sym : sym.replace('(', '');
                    return `<button class="math-sym-btn" data-insert="${sym}" title="${sym}">${display}</button>`;
                })
                .join('');

            // Re-bind
            grid.querySelectorAll('.math-sym-btn').forEach((btn) => {
                btn.addEventListener('click', () => {
                    if (btn.dataset.insert) insertSymbol(btn.dataset.insert);
                });
            });
        });
    });
}

// ── Modals ─────────────────────────────────────────────────────
export function initModals() {
    // Coming Soon modal
    const comingSoonModal = document.getElementById('coming-soon-modal');
    const closeComingSoonBtn = document.getElementById('close-coming-soon');
    if (closeComingSoonBtn && comingSoonModal) {
        closeComingSoonBtn.addEventListener('click', () => {
            comingSoonModal.style.display = 'none';
        });
    }

    // Mic buttons → coming soon
    document.querySelectorAll('.mic-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            if (comingSoonModal) {
                comingSoonModal.style.display = 'flex';
            }
        });
    });

    // Media zoom modal
    const mediaModal = document.getElementById('media-modal');
    const mediaModalImg = document.getElementById('media-modal-img');
    const mediaModalClose = document.getElementById('media-modal-close');

    // Delegate: clicking any .message-image or [data-action="zoom-media"]
    document.addEventListener('click', (e) => {
        const target = e.target.closest('.message-image, [data-action="zoom-media"]');
        if (target && mediaModal && mediaModalImg) {
            const src = target.src || target.dataset.src;
            if (src) {
                mediaModalImg.src = src;
                mediaModal.classList.add('active');
            }
        }
    });

    if (mediaModalClose && mediaModal) {
        mediaModalClose.addEventListener('click', () => {
            mediaModal.classList.remove('active');
            if (mediaModalImg) mediaModalImg.src = '';
        });
    }
    if (mediaModal) {
        mediaModal.addEventListener('click', (e) => {
            if (e.target === mediaModal) {
                mediaModal.classList.remove('active');
                if (mediaModalImg) mediaModalImg.src = '';
            }
        });
    }
}

// ── Graph (direct plot bar) ───────────────────────────────────
export function initGraph() {
    let graphBubbleCounter = 0;
    let isDraggableInitialized = false;

    function dragElement(elmnt) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        const handle = elmnt.querySelector('.drag-handle');

        (handle || elmnt).onmousedown = function (e) {
            e = e || window.event;
            e.preventDefault();
            const rect = elmnt.getBoundingClientRect();
            elmnt.style.top = rect.top + 'px';
            elmnt.style.left = rect.left + 'px';
            elmnt.style.transform = 'none';
            elmnt.style.bottom = 'auto';
            elmnt.style.margin = '0';
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDrag;
            document.onmousemove = elementDrag;
        };

        function elementDrag(e) {
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            const maxX = window.innerWidth - elmnt.offsetWidth;
            const maxY = window.innerHeight - elmnt.offsetHeight;
            elmnt.style.left = Math.min(Math.max(elmnt.offsetLeft - pos1, 0), maxX) + 'px';
            elmnt.style.top = Math.min(Math.max(elmnt.offsetTop - pos2, 0), maxY) + 'px';
            elmnt.style.transform = 'none';
            elmnt.style.bottom = 'auto';
        }

        function closeDrag() {
            document.onmouseup = null;
            document.onmousemove = null;
        }
    }

    window.toggleGraphBar = function () {
        const bar = document.getElementById('graph-input-bar');
        if (!bar) return;
        if (!isDraggableInitialized) {
            dragElement(bar);
            isDraggableInitialized = true;
        }
        const isVisible = bar.style.display === 'flex';
        bar.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            setTimeout(() => {
                const fnInput = document.getElementById('fn-input');
                if (fnInput) { fnInput.focus(); fnInput.click(); }
            }, 100);
        }
    };

    window.plotFnToChat = function () {
        const fnInput = document.getElementById('fn-input');
        const expr = fnInput?.value?.trim();
        if (!expr) return;

        document.getElementById('graph-input-bar').style.display = 'none';
        fnInput.value = '';

        // Transition to chat
        const heroSection = document.querySelector('.hero');
        const chatInterface = document.getElementById('chat-interface');
        if (heroSection && heroSection.style.display !== 'none') {
            heroSection.style.display = 'none';
            if (chatInterface) chatInterface.style.display = 'flex';
            const floatingWrapper = document.getElementById('floating-search-wrapper');
            if (floatingWrapper) floatingWrapper.style.display = 'flex';
            appState.isChatActive = true;
        }

        const bubbleId = 'ggb-bubble-' + (++graphBubbleCounter);
        const chatMessages = document.getElementById('chat-messages');
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

        const scrollWrapper = document.getElementById('chat-interface');
        if (scrollWrapper) scrollWrapper.scrollTop = scrollWrapper.scrollHeight;

        setTimeout(() => {
            const container = document.getElementById(bubbleId);
            if (!container) return;
            const appletParams = {
                appName: 'graphing',
                width: container.offsetWidth || 560,
                height: 420,
                showToolBar: false,
                showAlgebraInput: true,
                showMenuBar: false,
                enableRightClick: false,
                appletOnLoad: (api) => api.evalCommand('f(x) = ' + expr),
            };

            if (typeof GGBApplet !== 'undefined') {
                new GGBApplet(appletParams, true).inject(bubbleId);
            } else {
                const script = document.createElement('script');
                script.src = 'https://www.geogebra.org/apps/deployggb.js';
                script.onload = () => new GGBApplet(appletParams, true).inject(bubbleId);
                script.onerror = () => {
                    container.innerHTML = '<div style="padding:20px;color:red;">Failed to load Graphing engine.</div>';
                };
                document.head.appendChild(script);
            }
        }, 300);
    };
}

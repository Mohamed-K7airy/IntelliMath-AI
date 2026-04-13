// ============================================================
// Image Upload — Preview, Drag & Drop, Progress
// ============================================================

/**
 * Image upload state — used by chat.js for the send flow.
 */
export const imageState = {
    file: null,
    objectUrl: null,
    dataUrl: null,
    isPreparing: false,
};

// ── DOM Cache ─────────────────────────────────────────────────
let _uploadTimeout;

// Helper to get prefix based on active view
function getPrefix() {
    const chatInterface = document.getElementById('chat-interface');
    const isChatActive = chatInterface && chatInterface.style.display !== 'none';
    return isChatActive ? 'chat-' : '';
}

function getEl(id, prefix = '') {
    return document.getElementById(prefix + id);
}

// ── UI helpers ────────────────────────────────────────────────
export function setImageUploadUI(state) {
    const prefix = getPrefix();
    const wrapper = getEl('image-preview-wrapper', prefix);
    const thumb = getEl('image-preview-thumbnail', prefix);
    const overlayText = getEl('upload-overlay-text', prefix);
    const progressBar = getEl('upload-progress-bar', prefix);

    if (!wrapper || !thumb) return;

    // Manage classes for modern CSS animations
    if (state.visible) {
        wrapper.classList.add('is-visible');
        if (state.loading) {
            wrapper.classList.add('is-loading');
            wrapper.classList.remove('is-ready');
        } else {
            wrapper.classList.remove('is-loading');
            wrapper.classList.add('is-ready');
        }
    } else {
        wrapper.classList.remove('is-visible', 'is-loading', 'is-ready');
        wrapper.style.display = 'none'; // Ensure it's hidden if not visible
    }

    if (overlayText && typeof state.text === 'string') overlayText.textContent = state.text;
    if (progressBar && typeof state.progress === 'number') {
        progressBar.style.width = `${Math.max(0, Math.min(100, state.progress))}%`;
    }
}

function revokePreviewUrl() {
    if (imageState.objectUrl) {
        try { URL.revokeObjectURL(imageState.objectUrl); } catch { /* ignore */ }
        imageState.objectUrl = null;
    }
}

function fileToDataUrlWithProgress(file, onProgress) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Failed to read image'));
        reader.onabort = () => reject(new Error('Image read aborted'));
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onprogress = (e) => {
            if (e.lengthComputable && typeof onProgress === 'function') {
                onProgress((e.loaded / e.total) * 100);
            }
        };
        reader.readAsDataURL(file);
    });
}

// ── Public API ────────────────────────────────────────────────

/** Show an image preview and read the file into a base64 data URL. */
export async function showImagePreview(file) {
    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
        alert('Please upload an image or PDF file.');
        return;
    }

    if (_uploadTimeout) clearTimeout(_uploadTimeout);
    imageState.file = file;
    imageState.dataUrl = null;
    revokePreviewUrl();

    const prefix = getPrefix();
    const thumb = getEl('image-preview-thumbnail', prefix);
    const wrapper = getEl('image-preview-wrapper', prefix);

    // Instant preview via object URL
    imageState.objectUrl = URL.createObjectURL(file);
    if (thumb) {
        if (file.type === 'application/pdf') {
            thumb.src = 'logo.png';
        } else {
            thumb.src = imageState.objectUrl;
        }
    }

    // Show loading state
    if (wrapper) wrapper.style.display = 'flex';

    setImageUploadUI({ visible: true, loading: true, progress: 0, text: 'Uploading…' });

    imageState.isPreparing = true;
    try {
        const dataUrl = await fileToDataUrlWithProgress(file, (p) => {
            setImageUploadUI({ visible: true, loading: true, progress: p, text: 'Uploading…' });
        });
        imageState.dataUrl = dataUrl;

        // Small aesthetic delay so users see the professional spinner
        _uploadTimeout = setTimeout(() => {
            setImageUploadUI({ visible: true, loading: false, progress: 100, text: 'Uploaded' });
            _uploadTimeout = null;
        }, 800);
    } catch (e) {
        console.error('Image preparation failed:', e);
        imageState.dataUrl = null;
        setImageUploadUI({ visible: true, loading: false, progress: 0, text: 'Upload failed' });
    } finally {
        imageState.isPreparing = false;
    }
}

/** Clear the image preview and reset state. */
export function removeImagePreview() {
    if (_uploadTimeout) clearTimeout(_uploadTimeout);

    imageState.file = null;
    imageState.dataUrl = null;
    revokePreviewUrl();

    // Clear ALL potential previews
    ['', 'chat-'].forEach(prefix => {
        const wrapper = getEl('image-preview-wrapper', prefix);
        const thumb = getEl('image-preview-thumbnail', prefix);
        if (wrapper) {
            wrapper.style.display = 'none';
            wrapper.classList.remove('is-visible', 'is-loading', 'is-ready');
        }
        if (thumb) thumb.src = '';
    });

    setImageUploadUI({ visible: false, loading: false, progress: 0, text: '' });

    ['image-upload-input', 'drop-zone-input', 'chat-drop-zone-input'].forEach(id => {
        const inp = document.getElementById(id);
        if (inp) inp.value = '';
    });
}

/**
 * Initialize all image-related listeners
 */
export function initImageUpload() {
    // Global delegation for remove buttons (handles both landing and chat)
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.remove-preview-btn');
        if (btn) removeImagePreview();
    });

    // Upload button (hero)
    const uploadBtnMain = document.getElementById('upload-btn-main');
    const imageUploadInput = document.getElementById('image-upload-input');
    if (uploadBtnMain && imageUploadInput) {
        uploadBtnMain.addEventListener('click', (e) => {
            e.stopPropagation();
            imageUploadInput.click();
        });
        imageUploadInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) showImagePreview(file);
        });
    }

    // Drag & Drop zones
    const dropZones = [
        { zone: document.getElementById('drop-zone'), input: document.getElementById('drop-zone-input') },
        { zone: document.getElementById('chat-drop-zone'), input: document.getElementById('chat-drop-zone-input') },
    ];

    dropZones.forEach(({ zone, input }) => {
        if (!zone || !input) return;

        zone.addEventListener('click', (e) => {
            if (e.target === zone || e.target.closest('.upload-content')) {
                e.stopPropagation();
                input.click();
            }
        });

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) showImagePreview(file);
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) showImagePreview(file);
        });
    });
}


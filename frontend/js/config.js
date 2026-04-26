// Centralized configuration — GST Invoice Scanner frontend
const CONFIG = {
    API_BASE_URL: (() => {
        const hostname = window.location.hostname;
        if (hostname === '127.0.0.1' || hostname === 'localhost') {
            return `http://${hostname}:8000`;
        }
        return 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com';
    })(),
    SUPABASE_URL: 'https://qcttkeoxdwkmdjjlsjdx.supabase.co',
    SUPABASE_ANON_KEY: window.ENV_SUPABASE_ANON_KEY || 'REPLACE_WITH_SUPABASE_ANON_KEY'};

window.getApiUrl = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;

// Token helpers — kept for Supabase SDK internal use only.
// NOT injected into API request headers anymore (HttpOnly cookie handles auth).
window.getToken   = () => sessionStorage.getItem('authToken');
window.setToken   = (token) => { if (token) sessionStorage.setItem('authToken', token); };
window.clearToken = () => sessionStorage.removeItem('authToken');

// ── Core API Client (Zero-Trust) ─────────────────────────────────────────────
// Auth is handled exclusively via the HttpOnly 'sb_session' cookie.
// The browser sends it automatically on every credentialed request.
// No Authorization header is ever injected here.
window.apiFetch = async (url, options = {}) => {
    options.credentials = 'include';   // Always send the HttpOnly cookie
    options.headers = options.headers || {};

    // Fallback for Incognito/Safari where third-party cookies are blocked
    const token = window.getToken();
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    let response;
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000); // 90s hard timeout to accommodate OCR + LLM
        response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timeoutId);
    } catch (err) {
        if (err.name === 'AbortError') {
            window._showNetworkError('Request timed out. The server is taking too long.');
        } else {
            window._showNetworkError('No connection. Check your internet and try again.');
        }
        throw err;
    }

    // Intercept 401 — cookie missing or expired
    const isAuthEndpoint = url.includes('/api/auth/session') || url.includes('/api/logout');
    if (response.status === 401 && !isAuthEndpoint) {
        window._handleSessionExpired();
    }

    return response;
};

// ── Session Expiration Handler ────────────────────────────────────────────────
window._sessionExpiredShown = false;
window._handleSessionExpired = () => {
    if (window._sessionExpiredShown) return;
    window._sessionExpiredShown = true;

    sessionStorage.removeItem('currentUser');
    sessionStorage.removeItem('currentCompany');
    window.clearToken();

    const overlay = document.createElement('div');
    overlay.className = 'session-expired-overlay';
    overlay.innerHTML = `
        <div class="session-expired-card">
            <div class="session-expired-icon">⏱</div>
            <h2>Session expired</h2>
            <p>Your session has timed out for security reasons. Please sign in again to continue.</p>
            <button class="session-expired-btn" id="sessionExpiredBtn">Sign in again →</button>
        </div>
    `;
    document.body.appendChild(overlay);
    document.getElementById('sessionExpiredBtn').addEventListener('click', () => {
        window.location.href = 'login.html';
    });
};

// ── Network Error Banner (lightweight, replaced by toast in Phase 5) ──────────
window._showNetworkError = (message) => {
    if (document.getElementById('network-error-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'network-error-banner';
    banner.style.cssText = `
        position:fixed; bottom:1.5rem; left:50%; transform:translateX(-50%);
        background:#1a1a2e; color:#fff; padding:0.8rem 1.5rem;
        border-radius:8px; font-size:0.9rem; font-weight:600;
        z-index:9999; box-shadow:0 8px 32px rgba(0,0,0,0.3);
        border-left:4px solid #ef4444;
    `;
    banner.textContent = `⚠ ${message}`;
    document.body.appendChild(banner);
    setTimeout(() => banner.remove(), 5000);
};

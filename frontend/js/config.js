// Centralized configuration for the GST Invoice Scanner frontend
const CONFIG = {
    API_BASE_URL: (() => {
        const hostname = window.location.hostname;

        // Local development
        if (hostname === '127.0.0.1' || hostname === 'localhost') {
            return `http://${hostname}:8000`;
        }

        // Production
        return 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com';
    })(),
    SUPABASE_URL: 'https://qcttkeoxdwkmdjjlsjdx.supabase.co',
    SUPABASE_ANON_KEY: 'your-anon-key-here' // USER: Replace with your actual anon key
};


window.getApiUrl = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;

window.getToken = () => sessionStorage.getItem('authToken');
window.setToken = (token) => { if (token) sessionStorage.setItem('authToken', token); };
window.clearToken = () => sessionStorage.removeItem('authToken');
window.getAuthHeaders = () => ({ 'Authorization': `Bearer ${window.getToken()}` });

window.apiFetch = async (url, options = {}) => {
    options.credentials = 'include';
    const token = window.getToken();
    if (token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(url, options);

    // Intercept 401 — but not for login/register calls
    const isAuthEndpoint = url.includes('/api/login') || url.includes('/api/register');
    if (response.status === 401 && !isAuthEndpoint) {
        window._handleSessionExpired();
    }

    return response;
};

// ── Session Expiration Handler ───────────────────────────────────────
window._sessionExpiredShown = false;
window._handleSessionExpired = () => {
    if (window._sessionExpiredShown) return;
    window._sessionExpiredShown = true;

    // Clear all session data
    sessionStorage.removeItem('currentUser');
    sessionStorage.removeItem('currentCompany');
    window.clearToken();

    // Build and inject the modal
    const overlay = document.createElement('div');
    overlay.className = 'session-expired-overlay';
    overlay.innerHTML = `
        <div class="session-expired-card">
            <div class="session-expired-icon">⏱</div>
            <h2>Session expired</h2>
            <p>Your session has timed out for security reasons. Please sign in again to continue where you left off.</p>
            <button class="session-expired-btn" id="sessionExpiredBtn">
                Sign in again →
            </button>
        </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById('sessionExpiredBtn').addEventListener('click', () => {
        window.location.href = 'login.html';
    });
};

// Centralized configuration for the GST Invoice Scanner frontend
const CONFIG = {
    API_BASE_URL: (() => {
        const hostname = window.location.hostname;
        
        // Local development
        if (hostname === '127.0.0.1' || hostname === 'localhost') {
            return `http://${hostname}:8000`;
        }
        
        // Vercel deployment
        if (hostname.includes('vercel.app')) {
            return 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com';
        }
        
        // Netlify or production
        return 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com';
    })()
};

window.getApiUrl = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;

// ── Token management ──────────────────────────────────────────────────
// Stores JWT in sessionStorage and sends it as Authorization: Bearer header.
// This is required for cross-origin requests (Netlify/Vercel → Render) because
// SameSite=None cookies are blocked by modern browsers in third-party contexts.
window.getToken = () => sessionStorage.getItem('authToken');
window.setToken = (token) => { if (token) sessionStorage.setItem('authToken', token); };
window.clearToken = () => sessionStorage.removeItem('authToken');

// ── Global fetch wrapper ──────────────────────────────────────────────
window.apiFetch = async (url, options = {}) => {
    options.credentials = 'include';  // still send cookies for local dev
    const token = window.getToken();
    if (token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, options);
};

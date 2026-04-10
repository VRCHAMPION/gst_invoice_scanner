// Centralized configuration for the GST Invoice Scanner frontend
const CONFIG = {
    // CHANGE THIS TO YOUR RENDER URL (e.g., https://your-app.onrender.com)
    API_BASE_URL: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
        ? `http://${window.location.hostname}:8000` 
        : 'https://gst-invoice-scanner-api-vrc.onrender.com'
};

// Global helper to get the base URL
window.getApiUrl = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;

// Global fetch wrapper to force credentials inclusion for HttpOnly cookies
window.apiFetch = async (url, options = {}) => {
    options.credentials = 'include';
    return fetch(url, options);
};

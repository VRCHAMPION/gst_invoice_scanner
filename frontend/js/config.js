// Centralized configuration for the GST Invoice Scanner frontend
const CONFIG = {
    // CHANGE THIS TO YOUR RENDER URL (e.g., https://your-app.onrender.com)
    API_BASE_URL: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
        ? 'http://127.0.0.1:8000' 
        : 'https://gst-invoice-scanner.onrender.com'
};

// Global helper to get the base URL
window.getApiUrl = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;

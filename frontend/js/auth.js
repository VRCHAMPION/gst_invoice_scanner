const API_BASE = 'http://127.0.0.1:8000';

// ── Auth Token Management ────────────────────────────────────────────
function getToken() {
    return sessionStorage.getItem('authToken');
}

function getAuthHeaders() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function checkAuth() {
    const token = getToken();
    const path = window.location.pathname;
    const isAuthPage = path.includes('login.html') || path.includes('register.html');

    if (!token && !isAuthPage) {
        window.location.href = 'login.html';
    } else if (token && isAuthPage) {
        window.location.href = 'index.html';
    }
}

// RUN IMMEDIATELY TO PREVENT BLINK
checkAuth();

// ── Login (API-based) ────────────────────────────────────────────────
async function login(username, password) {
    try {
        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const err = await response.json();
            return { success: false, message: err.detail || 'Invalid credentials' };
        }

        const data = await response.json();
        sessionStorage.setItem('authToken', data.access_token);
        sessionStorage.setItem('currentUser', JSON.stringify(data.user));
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Server connection failed' };
    }
}

// ── Register (API-based) ─────────────────────────────────────────────
async function register(name, username, password) {
    try {
        const response = await fetch(`${API_BASE}/api/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, username, password })
        });

        if (!response.ok) {
            const err = await response.json();
            return { success: false, message: err.detail || 'Registration failed' };
        }

        const data = await response.json();
        sessionStorage.setItem('authToken', data.access_token);
        sessionStorage.setItem('currentUser', JSON.stringify(data.user));
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Server connection failed' };
    }
}

function logout() {
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}

function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

// ── Global UI Updates ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    if (user) {
        const userNameDisplays = document.querySelectorAll('.display-user-name');
        userNameDisplays.forEach(el => el.textContent = user.name);
    }

    const logoutBtns = document.querySelectorAll('.logout-trigger');
    logoutBtns.forEach(btn => btn.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    }));
});

// ── Utility: Format Indian Currency ──────────────────────────────────
function formatCurrency(amount) {
    if (amount === undefined || amount === null) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2
    }).format(amount);
}

// ── Utility: Format Date ─────────────────────────────────────────────
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        if (isNaN(date)) return dateString;
        return date.toLocaleDateString('en-IN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

// ── Utility: Counter Animation ───────────────────────────────────────
function animateCounter(el, target) {
    let current = 0;
    const duration = 1500;
    const start = performance.now();
    
    const update = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const value = Math.floor(progress * target);
        
        if (el.dataset.type === 'currency') {
            el.textContent = formatCurrency(value);
        } else {
            el.textContent = value;
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            if (el.dataset.type === 'currency') {
                el.textContent = formatCurrency(target);
            } else {
                el.textContent = target;
            }
        }
    };
    
    requestAnimationFrame(update);
}

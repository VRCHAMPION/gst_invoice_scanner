// API_BASE is now handled by getApiUrl() helper in config.js

// ── Auth Management ──────────────────────────────────────────────────
// We no longer manually manage the token in frontend.
// HttpOnly Cookies manage the session automatically via apiFetch wrapper.
function getAuthHeaders() {
    return {};
}

function checkAuth() {
    const user = getCurrentUser();
    const path = window.location.pathname;
    // Match both /login.html and /login (Netlify serves both)
    const isAuthPage = path.includes('login') || path.includes('register') || path === '/';
    const isOnboarding = path.includes('onboarding');

    if (!user && !isAuthPage) {
        window.location.href = 'login.html';
    } else if (user && isAuthPage) {
        window.location.href = 'upload.html';
    } else if (user && !isOnboarding && !user.company_id) {
        window.location.href = 'onboarding.html';
    }
}

// RUN IMMEDIATELY TO PREVENT BLINK
checkAuth();

// ── Login (API-based) ────────────────────────────────────────────────
async function login(email, password) {
    try {
        const response = await apiFetch(getApiUrl('/api/login'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: password })
        });

        if (!response.ok) {
            const err = await response.json();
            return { success: false, message: err.detail || 'Invalid credentials' };
        }

        const data = await response.json();
        // token is handled via HttpOnly cookie natively now!
        sessionStorage.setItem('currentUser', JSON.stringify(data.user));
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Server connection failed' };
    }
}

// ── Register (API-based) ─────────────────────────────────────────────
async function register(name, email, password, role) {
    try {
        const response = await apiFetch(getApiUrl('/api/register'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password, role })
        });

        if (!response.ok) {
            const err = await response.json();
            return { success: false, message: err.detail || 'Registration failed' };
        }

        const data = await response.json();
        sessionStorage.setItem('currentUser', JSON.stringify(data.user));
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Server connection failed' };
    }
}

async function logout() {
    try {
        await apiFetch(getApiUrl('/api/logout'), { method: 'POST' });
    } catch(e) { console.error(e); }
    sessionStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}

function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

// ── Global UI Updates ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    const company = JSON.parse(sessionStorage.getItem('currentCompany'));
    
    if (user) {
        const userNameDisplays = document.querySelectorAll('.display-user-name');
        userNameDisplays.forEach(el => {
            el.textContent = `${user.name} (${user.role.toUpperCase()})`;
        });

        if (company) {
             const companyDisplays = document.querySelectorAll('.display-company-name');
             companyDisplays.forEach(el => el.textContent = company.name.toUpperCase());
        }
    }

    const logoutBtns = document.querySelectorAll('.logout-trigger');
    logoutBtns.forEach(btn => btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await logout();
    }));
});

// ── Utilities (formatCurrency, formatDate, animateCounter) ───────────
// Defined in utils.js — loaded before this file in every HTML page.

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
    const isAuthPage = path.includes('login.html') || path.includes('register.html') || path === '/' || path.endsWith('/gst_invoice_scanner/frontend/');
    const isOnboarding = path.includes('onboarding.html');

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

// Auth state management

function checkAuth() {
    const user = getCurrentUser();
    const path = window.location.pathname;

    const isLoginPage     = path.includes('login');
    const isRegisterPage  = path.includes('register');
    const isLandingPage   = path === '/';
    const isOnboardingPage = path.includes('onboarding');

    // Redirect unauthenticated users to login
    if (!user && !isLoginPage && !isRegisterPage && !isLandingPage) {
        window.location.href = 'login.html';
        return;
    }

    // Logged-in users shouldn't see login page
    if (user && isLoginPage) {
        window.location.href = 'upload.html';
        return;
    }

    // Users without company need to complete onboarding
    if (user && !isOnboardingPage && !isRegisterPage && !isLoginPage && !isLandingPage && !user.company_id) {
        window.location.href = 'onboarding.html';
        return;
    }
}

checkAuth();

// Login
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
        if (data.token) window.setToken(data.token);
        sessionStorage.setItem('currentUser', JSON.stringify(data.user));
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Server connection failed' };
    }
}

// Register
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
        if (data.token) window.setToken(data.token);
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
    sessionStorage.removeItem('currentCompany');
    window.clearToken();
    window.location.href = 'login.html';
}

function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

// Update UI with user info
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

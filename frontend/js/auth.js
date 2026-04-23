// Auth state management — Supabase + HttpOnly cookie session
const _supabase = supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);

// ── Session Establishment ─────────────────────────────────────────────────────
// Exchanges a Supabase access_token for a secure HttpOnly cookie.
// Returns the UserOut object on success, or null on failure.
async function _establishSession(accessToken) {
    try {
        const resp = await fetch(window.getApiUrl('/api/auth/session'), {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: accessToken }),
        });
        if (!resp.ok) return null;
        const userData = await resp.json();
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        return userData;
    } catch {
        return null;
    }
}

// ── Page Guard ────────────────────────────────────────────────────────────────
async function checkAuth() {
    const { data: { session } } = await _supabase.auth.getSession();
    const user = session?.user;
    const path = window.location.pathname;

    const isLoginPage      = path.includes('login');
    const isRegisterPage   = path.includes('register');
    const isLandingPage    = path === '/' || path.endsWith('index.html');
    const isOnboardingPage = path.includes('onboarding');
    const isCallbackPage   = path.includes('auth-callback');

    if (user && !sessionStorage.getItem('currentUser')) {
        // Supabase session exists but no local profile — establish HttpOnly cookie + fetch profile
        await _establishSession(session.access_token);
    }

    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));

    if (!user && !isLoginPage && !isRegisterPage && !isLandingPage && !isCallbackPage) {
        window.location.href = 'login.html';
        return;
    }

    if (user && isLoginPage) {
        window.location.href = 'upload.html';
        return;
    }

    if (currentUser && !isOnboardingPage && !isRegisterPage && !isLoginPage && !isLandingPage && !isCallbackPage && !currentUser.company_id) {
        window.location.href = 'onboarding.html';
        return;
    }
}

checkAuth();

// ── Auth State Listener ───────────────────────────────────────────────────────
_supabase.auth.onAuthStateChange(async (event, session) => {
    if (event === 'TOKEN_REFRESHED' && session) {
        // Supabase auto-refreshed the JWT — keep the HttpOnly cookie in sync
        await _establishSession(session.access_token);
    } else if (event === 'SIGNED_OUT') {
        sessionStorage.clear();
        window.clearToken();
        window.location.href = 'login.html';
    }
});

// ── Login ─────────────────────────────────────────────────────────────────────
async function login(email, password) {
    try {
        const { data, error } = await _supabase.auth.signInWithPassword({ email, password });
        if (error) return { success: false, message: error.message };

        const userData = await _establishSession(data.session.access_token);
        if (!userData) return { success: false, message: 'Failed to establish session. Please try again.' };

        return { success: true };
    } catch {
        return { success: false, message: 'Connection failed' };
    }
}

// ── Google OAuth ──────────────────────────────────────────────────────────────
async function loginWithGoogle() {
    try {
        const { error } = await _supabase.auth.signInWithOAuth({
            provider: 'google',
            options: { redirectTo: window.location.origin + '/auth-callback.html' },
        });
        if (error) {
            console.error('Google login error:', error.message);
            alert('Could not log in with Google. Please try again.');
        }
    } catch (err) {
        console.error('Connection failed:', err);
    }
}

// ── Register ──────────────────────────────────────────────────────────────────
async function register(name, email, password, role) {
    try {
        const { data, error } = await _supabase.auth.signUp({
            email,
            password,
            options: {
                emailRedirectTo: window.location.origin + '/auth-callback.html',
                data: { full_name: name, role: role || 'owner' },
            },
        });
        if (error) return { success: false, message: error.message };

        // If email confirmation is disabled, a session is returned immediately
        if (data.session) {
            const userData = await _establishSession(data.session.access_token);
            if (!userData) return { success: false, message: 'Failed to establish session.' };
            return { success: true };
        }

        return { success: true, message: 'Check your email to confirm your account' };
    } catch {
        return { success: false, message: 'Connection failed' };
    }
}

// ── Logout ────────────────────────────────────────────────────────────────────
async function logout() {
    // 1. Clear backend HttpOnly cookie
    try { await window.apiFetch(window.getApiUrl('/api/logout'), { method: 'POST' }); } catch {}
    // 2. Sign out from Supabase (clears its internal storage)
    await _supabase.auth.signOut();
    // 3. Clear all local state
    window.clearToken();
    sessionStorage.clear();
    window.location.href = 'login.html';
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    if (user) {
        document.querySelectorAll('.display-user-name').forEach(el => {
            el.textContent = `${user.name} (${user.role.toUpperCase()})`;
        });
    }
    document.querySelectorAll('.logout-trigger').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            await logout();
        });
    });
});

// Auth state management using Supabase
const supabase = supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);

async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession();
    const user = session?.user;
    const path = window.location.pathname;

    const isLoginPage     = path.includes('login');
    const isRegisterPage  = path.includes('register');
    const isLandingPage   = path === '/' || path.endsWith('index.html');
    const isOnboardingPage = path.includes('onboarding');

    if (user) {
        // Sync local storage with Supabase session
        window.setToken(session.access_token);
        
        // Fetch profile from our backend to check company_id
        if (!sessionStorage.getItem('currentUser')) {
            try {
                const resp = await apiFetch(getApiUrl('/api/me'));
                if (resp.ok) {
                    const userData = await resp.json();
                    sessionStorage.setItem('currentUser', JSON.stringify(userData));
                    if (userData.company_id) {
                         // Fetch company info if needed
                    }
                }
            } catch (e) { console.error("Sync error", e); }
        }
    }

    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));

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
    if (currentUser && !isOnboardingPage && !isRegisterPage && !isLoginPage && !isLandingPage && !currentUser.company_id) {
        window.location.href = 'onboarding.html';
        return;
    }
}

// Initial check
checkAuth();

// Listen for auth changes
supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN') {
        window.setToken(session.access_token);
    } else if (event === 'SIGNED_OUT') {
        window.clearToken();
        sessionStorage.clear();
        window.location.href = 'login.html';
    }
});


// Login
async function login(email, password) {
    try {
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) return { success: false, message: error.message };

        window.setToken(data.session.access_token);
        // Backend will sync on the first /api/me call
        const resp = await apiFetch(getApiUrl('/api/me'));
        if (resp.ok) {
            const userData = await resp.json();
            sessionStorage.setItem('currentUser', JSON.stringify(userData));
        }

        return { success: true };
    } catch (error) {
        return { success: false, message: 'Connection failed' };
    }
}

// Register
async function register(name, email, password, role) {
    try {
        const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                data: {
                    full_name: name,
                    role: role || 'owner'
                }
            }
        });


        if (error) return { success: false, message: error.message };

        if (data.session) {
            window.setToken(data.session.access_token);
            const resp = await apiFetch(getApiUrl('/api/me'));
            if (resp.ok) {
                const userData = await resp.json();
                sessionStorage.setItem('currentUser', JSON.stringify(userData));
            }
        } else {
            return { success: true, message: 'Check your email for confirmation link' };
        }

        return { success: true };
    } catch (error) {
        return { success: false, message: 'Connection failed' };
    }
}

async function logout() {
    await supabase.auth.signOut();
    window.clearToken();
    sessionStorage.clear();
    window.location.href = 'login.html';
}

function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

// Update UI with user info
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    
    if (user) {
        const userNameDisplays = document.querySelectorAll('.display-user-name');
        userNameDisplays.forEach(el => {
            el.textContent = `${user.name} (${user.role.toUpperCase()})`;
        });
    }

    const logoutBtns = document.querySelectorAll('.logout-trigger');
    logoutBtns.forEach(btn => btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await logout();
    }));
});


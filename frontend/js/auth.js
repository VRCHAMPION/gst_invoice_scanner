const DEFAULT_USER = {
    username: "admin",
    password: "admin123",
    name: "Admin User"
};

// Initialize default user
if (!localStorage.getItem('users')) {
    localStorage.setItem('users', JSON.stringify([DEFAULT_USER]));
}

function checkAuth() {
    const user = sessionStorage.getItem('currentUser');
    const path = window.location.pathname;
    const isAuthPage = path.includes('login.html') || path.includes('register.html');

    if (!user && !isAuthPage) {
        window.location.href = 'login.html';
    } else if (user && isAuthPage) {
        window.location.href = 'index.html';
    }
}

// RUN IMMEDIATELY TO PREVENT BLINK
checkAuth();

function login(username, password) {
    const users = JSON.parse(localStorage.getItem('users') || '[]');
    const user = users.find(u => u.username === username && u.password === password);
    
    if (user) {
        sessionStorage.setItem('currentUser', JSON.stringify(user));
        return { success: true };
    }
    return { success: false, message: 'Invalid credentials' };
}

function register(name, username, password) {
    const users = JSON.parse(localStorage.getItem('users') || '[]');
    if (users.some(u => u.username === username)) {
        return { success: false, message: 'Username already exists' };
    }
    
    users.push({ name, username, password });
    localStorage.setItem('users', JSON.stringify(users));
    return { success: true };
}

function logout() {
    sessionStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}

function getCurrentUser() {
    return JSON.parse(sessionStorage.getItem('currentUser'));
}

// Global UI Updates
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

// Format Indian Currency
function formatCurrency(amount) {
    if (amount === undefined || amount === null) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2
    }).format(amount);
}

// Format Date
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

// Counter Animation
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

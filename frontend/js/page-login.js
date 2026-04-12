function togglePassword() {
    const pwd = document.getElementById('password');
    const toggle = document.querySelector('.toggle-password');
    if (pwd.type === 'password') {
        pwd.type = 'text';
        toggle.textContent = 'Hide';
    } else {
        pwd.type = 'password';
        toggle.textContent = 'Show';
    }
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const pass = document.getElementById('password').value;
    const remember = document.getElementById('rememberMe').checked;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (remember) {
        localStorage.setItem('rememberedUser', email);
    } else {
        localStorage.removeItem('rememberedUser');
    }

    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;

    const result = await login(email, pass);
    if (result.success) {
        window.location.href = 'upload.html';
    } else {
        const error = document.getElementById('errorMessage');
        error.textContent = result.message;
        error.style.display = 'block';
        submitBtn.textContent = 'Sign in';
        submitBtn.disabled = false;
    }
});

window.onload = () => {
    const saved = localStorage.getItem('rememberedUser');
    if (saved) {
        document.getElementById('email').value = saved;
        document.getElementById('rememberMe').checked = true;
    }
};

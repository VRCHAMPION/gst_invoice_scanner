const roleBtns = document.querySelectorAll('.role-btn');
const roleInput = document.getElementById('role');

roleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        roleBtns.forEach(b => {
            b.classList.remove('active');
            b.style.background = 'transparent';
            b.style.color = 'var(--muted)';
        });
        btn.classList.add('active');
        btn.style.background = 'var(--blue)';
        btn.style.color = 'white';
        roleInput.value = btn.dataset.role;
    });
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const pass = document.getElementById('password').value;
    const role = roleInput.value;
    const confirmPass = document.getElementById('confirmPassword').value;
    const error = document.getElementById('errorMessage');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (pass !== confirmPass) {
        error.textContent = 'Passwords do not match';
        error.style.display = 'block';
        return;
    }

    submitBtn.textContent = 'Getting started...';
    submitBtn.disabled = true;

    const result = await register(name, email, pass, role);
    if (result.success) {
        sessionStorage.setItem('intendedRole', role);
        window.location.href = 'upload.html';
    } else {
        error.textContent = result.message;
        error.style.display = 'block';
        submitBtn.textContent = 'Get started';
        submitBtn.disabled = false;
    }
});

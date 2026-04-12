document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    if (!user) return;

    const intendedRole = sessionStorage.getItem('intendedRole') || user.role;

    if (intendedRole === 'owner') {
        document.getElementById('ownerView').classList.add('active');
    } else {
        checkPendingStatus();
    }
});

async function checkPendingStatus() {
    try {
        const res = await apiFetch(getApiUrl('/api/join-request/status'));
        if (!res.ok) {
            document.getElementById('employeeView').classList.add('active');
            return;
        }
        const data = await res.json();

        if (data.status === 'approved') {
            const compRes = await apiFetch(getApiUrl('/api/companies'));
            const comps = await compRes.json();
            if (comps.length > 0) {
                sessionStorage.setItem('currentCompany', JSON.stringify(comps[0]));
                const user = getCurrentUser();
                user.company_id = comps[0].id;
                user.role = 'employee';
                sessionStorage.setItem('currentUser', JSON.stringify(user));
            }
            sessionStorage.removeItem('intendedRole');
            window.location.href = 'upload.html';
        } else if (data.status === 'pending') {
            showPendingView(data.company_name);
            startPolling();
        } else {
            document.getElementById('employeeView').classList.add('active');
        }
    } catch {
        document.getElementById('employeeView').classList.add('active');
    }
}

function showPendingView(companyName) {
    document.getElementById('employeeView').classList.remove('active');
    document.getElementById('pendingView').classList.add('active');
    document.getElementById('stepDot2').classList.add('active');
    if (companyName) {
        document.getElementById('pendingMsg').textContent =
            `Your request to join "${companyName}" has been sent. You'll be redirected automatically once the owner approves you.`;
    }
}

let pollInterval = null;
function startPolling() {
    if (pollInterval) return;
    pollInterval = setInterval(async () => {
        try {
            const res = await apiFetch(getApiUrl('/api/join-request/status'));
            const data = await res.json();
            if (data.status === 'approved') {
                clearInterval(pollInterval);
                const compRes = await apiFetch(getApiUrl('/api/companies'));
                const comps = await compRes.json();
                if (comps.length > 0) {
                    sessionStorage.setItem('currentCompany', JSON.stringify(comps[0]));
                    const user = getCurrentUser();
                    user.company_id = comps[0].id;
                    user.role = 'employee';
                    sessionStorage.setItem('currentUser', JSON.stringify(user));
                }
                sessionStorage.removeItem('intendedRole');
                window.location.href = 'upload.html';
            }
        } catch {}
    }, 10000);
}

document.getElementById('createCompanyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('compName').value;
    const gstin = document.getElementById('compGstin').value;
    const btn = e.target.querySelector('button');
    btn.textContent = 'Creating...';
    btn.disabled = true;
    try {
        const res = await apiFetch(getApiUrl('/api/companies'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, gstin })
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Creation failed'); }
        const company = await res.json();
        sessionStorage.setItem('currentCompany', JSON.stringify(company));
        const user = getCurrentUser();
        user.company_id = company.id;
        sessionStorage.setItem('currentUser', JSON.stringify(user));
        sessionStorage.removeItem('intendedRole');
        window.location.href = 'upload.html';
    } catch (err) {
        const box = document.getElementById('errorBox');
        box.textContent = err.message;
        box.style.display = 'block';
        btn.textContent = 'Create workspace';
        btn.disabled = false;
    }
});

document.getElementById('joinCompanyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const companyName = document.getElementById('joinCompName').value;
    const btn = e.target.querySelector('button');
    btn.textContent = 'Sending request...';
    btn.disabled = true;
    try {
        const res = await apiFetch(getApiUrl('/api/join-request'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ company_name: companyName })
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Request failed'); }
        showPendingView(companyName);
        startPolling();
    } catch (err) {
        const box = document.getElementById('errorBox');
        box.textContent = err.message;
        box.style.display = 'block';
        btn.textContent = 'Send join request';
        btn.disabled = false;
    }
});

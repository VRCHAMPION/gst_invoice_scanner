// Team panel logic for upload page (owners only)
(function () {
    const _user = getCurrentUser();
    if (_user && _user.role === 'owner') {
        document.getElementById('teamPanel').style.display = 'block';
        loadTeamPanel();
        setInterval(loadTeamPanel, 30000);
    }

    async function loadTeamPanel() {
        try {
            const usersRes = await apiFetch(getApiUrl('/api/users'), {
                headers: getAuthHeaders()
            });
            if (usersRes.ok) {
                const users = await usersRes.json();
                document.getElementById('empCountBadge').textContent =
                    users.length + ' member' + (users.length !== 1 ? 's' : '');
            }

            const jrRes = await apiFetch(getApiUrl('/api/join-requests'), {
                headers: getAuthHeaders()
            });
            if (!jrRes.ok) return;
            const requests = await jrRes.json();

            const badge = document.getElementById('requestBadge');
            const list = document.getElementById('requestsList');

            if (requests.length === 0) {
                badge.style.display = 'none';
                list.innerHTML = '<div style="padding: 1rem 1.2rem; color: var(--muted); font-size: 0.82rem;">No pending requests</div>';
                return;
            }

            badge.textContent = requests.length;
            badge.style.display = 'inline-block';

            list.innerHTML = requests.map(r => `
                <div class="request-item" id="req-${r.id}">
                    <div>
                        <div class="request-name">${r.name}</div>
                        <div class="request-email">${r.email}</div>
                    </div>
                    <div class="request-actions">
                        <button class="btn-approve" onclick="handleRequest('${r.id}', 'approve')">Approve</button>
                        <button class="btn-reject" onclick="handleRequest('${r.id}', 'reject')">Reject</button>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error('Team panel error', e); }
    }

    window.handleRequest = async function (requestId, action) {
        const row = document.getElementById('req-' + requestId);
        if (row) { row.style.opacity = '0.4'; row.style.pointerEvents = 'none'; }
        try {
            const res = await apiFetch(getApiUrl(`/api/join-requests/${requestId}/${action}`), { 
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                console.log('Request ' + action + 'd successfully:', data.message);
                await loadTeamPanel();
            } else {
                const error = await res.json();
                console.error('Failed to ' + action + ' request:', error.detail);
                alert('Error: ' + (error.detail || 'Failed to ' + action + ' request'));
                if (row) { row.style.opacity = '1'; row.style.pointerEvents = 'auto'; }
            }
        } catch (e) { 
            console.error('Request error:', e);
            alert('Network error. Please try again.');
            if (row) { row.style.opacity = '1'; row.style.pointerEvents = 'auto'; } 
        }
    };
}());

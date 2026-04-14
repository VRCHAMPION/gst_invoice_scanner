document.addEventListener('DOMContentLoaded', () => {
    const companySelect = document.getElementById('companySelect');
    const companyModal = document.getElementById('companyModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const companyForm = document.getElementById('companyForm');

    // Load companies into dropdown
    window.loadCompanies = async () => {
        try {
            const response = await apiFetch(getApiUrl('/api/companies'), {
                headers: getAuthHeaders()
            });
            const companies = await response.json();

            if (!companySelect) return;
            companySelect.innerHTML = '<option value="">SELECT COMPANY...</option>';
            companies.forEach(company => {
                const option = document.createElement('option');
                option.value = company.id;
                option.textContent = `${company.name} (${company.gstin})`;
                companySelect.appendChild(option);
            });

            // Auto-select if only one company exists
            if (companies.length === 1) {
                companySelect.value = companies[0].id;
                window.dispatchEvent(new Event('companySelected'));
            }
        } catch (error) {
            console.error('Error loading companies:', error);
        }
    };

    // Modal logic — only bind if elements exist on this page
    if (openModalBtn) openModalBtn.addEventListener('click', () => {
        companyModal.style.display = 'flex';
    });

    if (closeModalBtn) closeModalBtn.addEventListener('click', () => {
        companyModal.style.display = 'none';
    });

    if (companyForm) companyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            name: document.getElementById('compName').value,
            gstin: document.getElementById('compGstin').value,
            address: document.getElementById('compAddress').value
        };

        try {
            await apiFetch(getApiUrl('/api/companies'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify(data)
            });

            companyModal.style.display = 'none';
            companyForm.reset();
            await loadCompanies();
            alert('COMPANY REGISTERED SUCCESSFULY');
        } catch (error) {
            alert('ERROR: ' + error.message);
        }
    });

    if (companySelect) loadCompanies();

    // ── SETTINGS MODAL LOGIC ──
    const settingsModal = document.getElementById('settingsModal');
    const openSettingsBtn = document.getElementById('openSettingsBtn');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const settingsForm = document.getElementById('settingsForm');
    const settingsWebhookUrl = document.getElementById('settingsWebhookUrl');

    if (openSettingsBtn && settingsModal) {
        openSettingsBtn.addEventListener('click', async () => {
            // Fetch current company settings to pre-fill
            try {
                const response = await apiFetch(getApiUrl('/api/companies'), { headers: getAuthHeaders() });
                const companies = await response.json();
                if (companies.length > 0) {
                    settingsWebhookUrl.value = companies[0].webhook_url || '';
                }
            } catch (err) {
                console.error('Failed to load settings:', err);
            }
            settingsModal.style.display = 'flex';
        });
    }

    if (closeSettingsBtn && settingsModal) {
        closeSettingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });
    }

    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                webhook_url: settingsWebhookUrl.value.trim() || null
            };

            try {
                await apiFetch(getApiUrl('/api/companies/me'), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                    body: JSON.stringify(data)
                });
                alert('Workspace settings saved successfully.');
                settingsModal.style.display = 'none';
            } catch (error) {
                alert('ERROR: ' + error.message);
            }
        });
    }
});

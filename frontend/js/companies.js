document.addEventListener('DOMContentLoaded', () => {
    const companySelect = document.getElementById('companySelect');
    const companyModal = document.getElementById('companyModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const companyForm = document.getElementById('companyForm');

    // Load companies into dropdown
    window.loadCompanies = async () => {
        try {
            const response = await fetch('http://127.0.0.1:8000/api/companies', {
                headers: getAuthHeaders()
            });
            if (!response.ok) throw new Error('Failed to fetch companies');
            const companies = await response.json();

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

    // Modal logic
    openModalBtn.addEventListener('click', () => {
        companyModal.style.display = 'flex';
    });

    closeModalBtn.addEventListener('click', () => {
        companyModal.style.display = 'none';
    });

    companyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            name: document.getElementById('compName').value,
            gstin: document.getElementById('compGstin').value,
            address: document.getElementById('compAddress').value
        };

        try {
            const response = await fetch('http://127.0.0.1:8000/api/companies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to save company');
            }

            companyModal.style.display = 'none';
            companyForm.reset();
            await loadCompanies();
            alert('COMPANY REGISTERED SUCCESSFULY');
        } catch (error) {
            alert('ERROR: ' + error.message);
        }
    });

    loadCompanies();
});

document.addEventListener('DOMContentLoaded', async () => {
    Chart.defaults.color = '#8a8580';
    Chart.defaults.font.family = "'Geist', sans-serif";
    Chart.defaults.borderColor = '#ddd9d2';

    try {
        await Promise.all([
            loadAnalytics(),
            loadItcSummary(),
            loadTeamSize()
        ]);
    } finally {
        const skeleton = document.getElementById('analyticsSkeletonState');
        const content = document.getElementById('analyticsContent');
        if (skeleton) skeleton.style.display = 'none';
        if (content) content.style.display = 'block';
    }
    calculateDeadlines();
});

async function loadTeamSize() {
    const user = getCurrentUser();
    if (user && user.role === 'owner') {
        const company = JSON.parse(sessionStorage.getItem('currentCompany'));
        if (company && company.employee_count !== undefined) {
             animateCounter(document.getElementById('teamSize'), company.employee_count);
        }
        
        // Show management area
        document.getElementById('ownerOnlyTeam').style.display = 'block';
        loadEmployeeList();
    } else {
        const teamCard = document.getElementById('teamSize').closest('.stat-card');
        if (teamCard) teamCard.style.display = 'none';
        
        const mgtArea = document.getElementById('ownerOnlyTeam');
        if (mgtArea) mgtArea.style.display = 'none';
    }
}

async function loadEmployeeList() {
    try {
        const res = await apiFetch(getApiUrl('/api/users'), { headers: getAuthHeaders() });
        const users = await res.json();
        const container = document.getElementById('employeeList');
        container.innerHTML = '';
        
        users.forEach(u => {
            const card = document.createElement('div');
            card.style.cssText = 'padding: 1rem; background: var(--surface-light); border-radius: var(--radius-sm); border: 1px solid var(--border-color);';
            card.innerHTML = `
                <div style="font-weight: 800; font-size: 0.9rem;">${u.name.toUpperCase()}</div>
                <div style="font-size: 0.8rem; color: var(--muted);">${u.email}</div>
                <div style="margin-top: 0.8rem; display: flex; align-items: center; justify-content: space-between;">
                    <span class="status-pill ${u.role==='owner'?'pill-success':'pill-processing'}">${u.role.toUpperCase()}</span>
                    ${u.role !== 'owner' ? `<button onclick="removeEmployee('${u.id}')" style="background:none; border:none; color:var(--red); font-size:0.75rem; font-weight:800; cursor:pointer; font-family: var(--display); letter-spacing: 0.5px;">REMOVE ✕</button>` : ''}
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) { console.error(e); }
}

window.removeEmployee = async (userId) => {
    if (!confirm("Are you sure you want to remove this employee from your workspace? They will lose access immediately.")) return;
    try {
        const res = await apiFetch(getApiUrl(`/api/users/${userId}/remove`), {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (res.ok) {
            alert('Employee removed successfully.');
            await loadEmployeeList();
            await loadTeamSize();
        } else {
            const error = await res.json();
            alert('Error: ' + error.detail);
        }
    } catch (e) {
        console.error(e);
        alert('Failed to remove employee.');
    }
};

window.openInvitePrompt = () => {
    document.getElementById('inviteModal').style.display = 'flex';
};

window.sendInvite = (method) => {
    const company = JSON.parse(sessionStorage.getItem('currentCompany'));
    if (!company) return;
    
    const message = `Join my workspace on GST Invoice Scanner!\n\n1. Go to the portal\n2. Register an account as an EMPLOYEE\n3. Request to join this exact company name: ${company.name}\n\nSee you there!`;
    const encodedMessage = encodeURIComponent(message);
    
    if (method === 'whatsapp') {
        window.open(`https://wa.me/?text=${encodedMessage}`, '_blank');
    } else if (method === 'email') {
        window.location.href = `mailto:?subject=Join my GST Workspace&body=${encodedMessage}`;
    }
    
    document.getElementById('inviteModal').style.display = 'none';
};

async function loadAnalytics() {
    try {
        const response = await apiFetch(getApiUrl('/api/analytics'), {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error('FAILED TO FETCH ANALYTICS');
        const data = await response.json();

        // Populate summary cards
        animateCounter(document.getElementById('totalInvoices'), data.total_invoices);
        animateCounterValue('totalSpend', data.total_spend);
        animateCounterValue('totalTax', data.total_tax);

        // Render Charts
        renderSpendChart(data.monthly_spend);
        renderSuppliersChart(data.top_suppliers);
        renderVolumeChart(data.monthly_invoice_count);
    } catch (error) {
        console.error(error);
    }
}

async function loadItcSummary() {
    try {
        const response = await apiFetch(getApiUrl('/api/itc-summary'), {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error('FAILED TO FETCH ITC');
        const data = await response.json();

        animateCounterValue('totalItc', data.current_month.total_itc);
        animateCounterValue('currentMonthItc', data.current_month.total_itc);

        const trendEl = document.getElementById('itcTrend');
        const change = data.percentage_change;
        trendEl.textContent = `${change > 0 ? '+' : ''}${change}%`;
        trendEl.style.color = change >= 0 ? 'var(--success)' : 'var(--danger)';

        document.getElementById('itcDisclaimer').textContent = data.disclaimer;

        const tbody = document.getElementById('itcTableBody');
        tbody.innerHTML = '';
        data.supplier_breakdown.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 700;">${row.seller_name.toUpperCase()}</td>
                <td class="data-font text-muted">${row.seller_gstin}</td>
                <td class="data-font">${formatCurrency(row.cgst)}</td>
                <td class="data-font">${formatCurrency(row.sgst)}</td>
                <td class="data-font">${formatCurrency(row.igst)}</td>
                <td class="data-font" style="color: var(--accent); font-weight: 500;">${formatCurrency(row.total_itc)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error(error);
    }
}

function renderSpendChart(monthlyData) {
    const ctx = document.getElementById('spendChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: monthlyData.map(d => d.month),
            datasets: [
                {
                    label: 'TOTAL SPEND',
                    data: monthlyData.map(d => d.total),
                    backgroundColor: '#2d6a4f',
                    hoverBackgroundColor: '#52b788'
                },
                {
                    label: 'TAX PAID',
                    data: monthlyData.map(d => d.tax),
                    backgroundColor: '#c87941',
                    hoverBackgroundColor: '#e8956d'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#1c1c24' }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        font: { weight: '800', size: 10 }
                    }
                }
            }
        }
    });
}

function renderSuppliersChart(suppliers) {
    const ctx = document.getElementById('suppliersChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: suppliers.map(s => s.name),
            datasets: [{
                data: suppliers.map(s => s.total_spend),
                backgroundColor: ['#2d6a4f', '#2c5f8a', '#c87941', '#7b5ea7', '#c0392b'],
                borderWidth: 0,
                hoverOffset: 20
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 6,
                        font: { size: 10, weight: '600' }
                    }
                }
            }
        }
    });
}

function renderVolumeChart(volumeData) {
    const ctx = document.getElementById('volumeChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: volumeData.map(d => d.month),
            datasets: [{
                label: 'INVOICES SCANNED',
                data: volumeData.map(d => d.count),
                borderColor: '#2c5f8a',
                backgroundColor: 'rgba(44,95,138,0.08)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#2c5f8a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                    grid: { color: '#ddd9d2' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function calculateDeadlines() {
    const today = new Date();
    const currentMonth = today.getMonth();
    const currentYear = today.getFullYear();

    const deadlines = [
        { id: 'gstr1Days', day: 11 },
        { id: 'gstr3bDays', day: 20 },
        { id: 'gstr2bDays', day: 14 }
    ];

    deadlines.forEach(dl => {
        let deadlineDate = new Date(currentYear, currentMonth, dl.day);
        if (today.getDate() > dl.day) {
            // If passed, next month deadline
            deadlineDate = new Date(currentYear, currentMonth + 1, dl.day);
        }

        const diffTime = deadlineDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        document.getElementById(dl.id).textContent = diffDays;
    });
}

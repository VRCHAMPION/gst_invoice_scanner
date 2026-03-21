document.addEventListener('DOMContentLoaded', async () => {
    // Set chart defaults for dark theme
    Chart.defaults.color = '#52526b';
    Chart.defaults.font.family = "'Outfit', sans-serif";
    Chart.defaults.borderColor = '#1c1c24';

    await loadAnalytics();
    await loadItcSummary();
    calculateDeadlines();
});

async function loadAnalytics() {
    try {
        const response = await fetch('http://127.0.0.1:8000/analytics', {
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
        const response = await fetch('http://127.0.0.1:8000/itc-summary', {
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
                <td class="data-font" style="color: var(--primary-accent); font-weight: 700;">${formatCurrency(row.total_itc)}</td>
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
                    backgroundColor: '#00ff88',
                    hoverBackgroundColor: '#ffffff'
                },
                {
                    label: 'TAX PAID',
                    data: monthlyData.map(d => d.tax),
                    backgroundColor: '#ff6b00',
                    hoverBackgroundColor: '#ffffff'
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
                backgroundColor: ['#00ff88', '#00c3ff', '#ff6b00', '#ff3355', '#52526b'],
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
                borderColor: '#00c3ff',
                backgroundColor: 'rgba(0, 195, 255, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#00c3ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                    grid: { color: '#1c1c24' }
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

function animateCounterValue(id, target) {
    const el = document.getElementById(id);
    el.dataset.type = 'currency';
    animateCounter(el, target);
}

document.addEventListener('DOMContentLoaded', () => {
    const rawData = JSON.parse(sessionStorage.getItem('lastScanResults'));
    if (!rawData) {
        window.location.href = 'index.html';
        return;
    }

    const isBatch = Array.from(Array.isArray(rawData) ? rawData : [rawData]).length > 1 || Array.isArray(rawData);
    const results = Array.isArray(rawData) ? rawData : [rawData];
    let currentIndex = 0;

    if (isBatch) {
        const batchNav = document.getElementById('batchNav');
        const batchIndicator = document.getElementById('batchIndicator');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        batchNav.style.display = 'flex';

        const updateBatchUI = () => {
            batchIndicator.textContent = `${currentIndex + 1} / ${results.length}`;
            prevBtn.disabled = currentIndex === 0;
            nextBtn.disabled = currentIndex === results.length - 1;
            populateData(results[currentIndex]);
            setupActions(results[currentIndex]);
        };

        prevBtn.addEventListener('click', () => {
            if (currentIndex > 0) {
                currentIndex--;
                updateBatchUI();
            }
        });

        nextBtn.addEventListener('click', () => {
            if (currentIndex < results.length - 1) {
                currentIndex++;
                updateBatchUI();
            }
        });

        updateBatchUI();
    } else {
        populateData(results[0]);
        setupActions(results[0]);
    }
});

function populateData(data) {
    // Header info
    document.getElementById('invoiceId').textContent = data.id || 'N/A';
    document.getElementById('processedTime').textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    // Entities
    document.getElementById('sellerName').textContent = (data.seller_name || 'UNKNOWN').toUpperCase();
    document.getElementById('sellerGstin').textContent = data.seller_gstin || 'NOT DETECTED';
    document.getElementById('buyerName').textContent = (data.buyer_name || 'UNKNOWN').toUpperCase();
    document.getElementById('buyerGstin').textContent = data.buyer_gstin || 'NOT DETECTED';

    // Invoice details
    document.getElementById('invoiceNumber').textContent = data.invoice_number || '---';
    document.getElementById('invoiceDate').textContent = formatDate(data.invoice_date);
    document.getElementById('itemCount').textContent = data.items ? data.items.length : 0;

    // Items table
    const tableBody = document.getElementById('itemsTableBody');
    tableBody.innerHTML = '';
    if (data.items && data.items.length > 0) {
        data.items.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="font-weight: 600;">${(item.description || 'Item').toUpperCase()}</td>
                <td class="data-font">${item.quantity || 0}</td>
                <td class="data-font">${formatCurrency(item.rate)}</td>
                <td class="data-font" style="color: var(--primary-accent); font-weight: 700;">${formatCurrency(item.amount)}</td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">NO LINE ITEMS DETECTED</td></tr>';
    }

    // Health Score
    const health = data.health_score || { score: 0, grade: 'F', status: 'Incomplete', issues: [], warnings: [], summary: 'No health data available' };

    // Animate score
    animateCounter(document.getElementById('scoreValue'), health.score);

    document.getElementById('gradeBadge').textContent = health.grade;
    document.getElementById('healthStatus').textContent = `HEALTH: ${health.status.toUpperCase()}`;
    document.getElementById('scoreSummary').textContent = health.summary;

    // Issues & Warnings
    const issuesContainer = document.getElementById('issuesContainer');
    issuesContainer.innerHTML = '';

    health.issues.forEach(issue => {
        const div = document.createElement('div');
        div.className = 'issue-card';
        div.innerHTML = `<span style="color: var(--danger); font-weight: 1000;">●</span> ${issue.toUpperCase()}`;
        issuesContainer.appendChild(div);
    });

    health.warnings.forEach(warning => {
        const div = document.createElement('div');
        div.className = 'warning-card';
        div.innerHTML = `<span style="color: var(--secondary-accent); font-weight: 1000;">●</span> ${warning.toUpperCase()}`;
        issuesContainer.appendChild(div);
    });

    // Tax Summary
    animateCounterValue('subtotalValue', data.subtotal || 0);
    animateCounterValue('cgstValue', data.cgst || 0);
    animateCounterValue('sgstValue', data.sgst || 0);
    animateCounterValue('igstValue', data.igst || 0);
    animateCounterValue('totalValue', data.total || 0);
}

function setupActions(data) {
    // Clone buttons to clear existing listeners (important for batch navigation)
    const exportBtn = document.getElementById('exportBtn');
    const newExportBtn = exportBtn.cloneNode(true);
    exportBtn.parentNode.replaceChild(newExportBtn, exportBtn);

    const whatsappBtn = document.getElementById('whatsappBtn');
    const newWhatsappBtn = whatsappBtn.cloneNode(true);
    whatsappBtn.parentNode.replaceChild(newWhatsappBtn, whatsappBtn);

    newExportBtn.addEventListener('click', async () => {
        try {
            const response = await apiFetch(getApiUrl('/api/export'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('EXPORT FAILED');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `invoice_${data.invoice_number || 'export'}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (error) {
            alert('ERROR EXPORTING: ' + error.message);
        }
    });

    newWhatsappBtn.addEventListener('click', () => {
        const text = `Invoice Report: ${data.invoice_number}\nTotal: ${formatCurrency(data.total)}\nHealth Score: ${data.health_score.score}/100`;
        window.open('https://wa.me/?text=' + encodeURIComponent(text));
    });
}

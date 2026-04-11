document.addEventListener('DOMContentLoaded', () => {
    const rawData = JSON.parse(sessionStorage.getItem('lastScanResults'));
    if (!rawData) {
        window.location.href = 'index.html';
        return;
    }

    const isBatch = Array.from(Array.isArray(rawData) ? rawData : [rawData]).length > 1 || Array.isArray(rawData);
    const results = Array.isArray(rawData) ? rawData : [rawData];
    let currentIndex = 0;
    let editMode = false;
    let currentData = null;

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
            currentData = results[currentIndex];
            populateData(currentData);
            setupActions(currentData);
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
        currentData = results[0];
        populateData(currentData);
        setupActions(currentData);
    }

    // Edit Mode Toggle
    const editBtn = document.getElementById('editBtn');
    const exitEditBtn = document.getElementById('exitEditBtn');
    const editModeBanner = document.getElementById('editModeBanner');

    editBtn.addEventListener('click', () => {
        editMode = true;
        editModeBanner.style.display = 'flex';
        editBtn.style.display = 'none';
        enableEditMode();
    });

    exitEditBtn.addEventListener('click', () => {
        editMode = false;
        editModeBanner.style.display = 'none';
        editBtn.style.display = 'inline-block';
        disableEditMode();
    });

    function enableEditMode() {
        // Make fields editable
        makeEditable('sellerName', 'seller_name');
        makeEditable('sellerGstin', 'seller_gstin');
        makeEditable('buyerName', 'buyer_name');
        makeEditable('buyerGstin', 'buyer_gstin');
        makeEditable('invoiceNumber', 'invoice_number');
        makeEditable('invoiceDate', 'invoice_date');
        makeEditable('subtotalValue', 'subtotal', true);
        makeEditable('cgstValue', 'cgst', true);
        makeEditable('sgstValue', 'sgst', true);
        makeEditable('igstValue', 'igst', true);
        makeEditable('totalValue', 'total', true);
    }

    function disableEditMode() {
        document.querySelectorAll('.editable-field').forEach(el => {
            el.classList.remove('editable-field');
            el.onclick = null;
        });
    }

    function makeEditable(elementId, dataKey, isCurrency = false) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.classList.add('editable-field');
        element.title = 'Click to edit';

        element.onclick = () => {
            if (!editMode) return;

            const currentValue = isCurrency 
                ? currentData[dataKey] || 0 
                : currentData[dataKey] || '';

            const input = document.createElement('input');
            input.type = isCurrency ? 'number' : 'text';
            input.value = currentValue;
            input.className = 'field-input';
            input.step = isCurrency ? '0.01' : undefined;

            element.classList.add('editing');
            const originalHTML = element.innerHTML;
            element.innerHTML = '';
            element.appendChild(input);
            input.focus();
            input.select();

            const saveEdit = () => {
                const newValue = isCurrency ? parseFloat(input.value) || 0 : input.value.trim();
                currentData[dataKey] = newValue;
                
                // Update session storage
                if (isBatch) {
                    results[currentIndex] = currentData;
                    sessionStorage.setItem('lastScanResults', JSON.stringify(results));
                } else {
                    sessionStorage.setItem('lastScanResults', JSON.stringify(currentData));
                }

                element.classList.remove('editing');
                populateData(currentData);
            };

            input.onblur = saveEdit;
            input.onkeydown = (e) => {
                if (e.key === 'Enter') saveEdit();
                if (e.key === 'Escape') {
                    element.classList.remove('editing');
                    element.innerHTML = originalHTML;
                }
            };
        };
    }
});

function populateData(data) {
    // Header info
    document.getElementById('invoiceId').textContent = data.id || 'N/A';
    document.getElementById('processedTime').textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    // Show duplicate warning if this is a duplicate invoice
    const duplicateWarningBanner = document.getElementById('duplicateWarningBanner');
    const duplicateWarningMessage = document.getElementById('duplicateWarningMessage');
    const viewOriginalBtn = document.getElementById('viewOriginalBtn');
    
    if (data.is_duplicate && data.status === 'FAILED') {
        duplicateWarningBanner.style.display = 'flex';
        duplicateWarningMessage.textContent = data.error_message || 'This invoice is a duplicate of an existing invoice.';
        
        // Set up link to original invoice
        viewOriginalBtn.href = `results.html?id=${data.is_duplicate}`;
        viewOriginalBtn.onclick = async (e) => {
            e.preventDefault();
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.is_duplicate}`), {
                    headers: { ...getAuthHeaders() }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to load original invoice');
                }
                
                const originalInvoice = await response.json();
                sessionStorage.setItem('lastScanResults', JSON.stringify(originalInvoice));
                window.location.href = 'results.html';
            } catch (error) {
                alert('ERROR: Could not load original invoice. ' + error.message);
            }
        };
    } else {
        duplicateWarningBanner.style.display = 'none';
    }

    // Show approval status badge
    const statusBadge = document.getElementById('approvalStatusBadge');
    if (statusBadge) {
        const status = data.status || 'PENDING_REVIEW';
        statusBadge.textContent = status.replace('_', ' ');
        statusBadge.className = 'status-badge status-' + status.toLowerCase();
        statusBadge.style.display = 'inline-block';
    }

    // Show/hide approval buttons based on status
    const approvalActions = document.getElementById('approvalActions');
    if (approvalActions) {
        if (data.status === 'PENDING_REVIEW') {
            approvalActions.style.display = 'flex';
        } else {
            approvalActions.style.display = 'none';
        }
    }

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

    // Setup approval buttons
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');
    
    if (approveBtn) {
        const newApproveBtn = approveBtn.cloneNode(true);
        approveBtn.parentNode.replaceChild(newApproveBtn, approveBtn);
        
        newApproveBtn.addEventListener('click', async () => {
            if (!confirm('Approve this invoice?')) return;
            
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.id}/approve`), {
                    method: 'POST',
                    headers: { ...getAuthHeaders() }
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Approval failed');
                }
                
                alert('Invoice approved successfully!');
                data.status = 'APPROVED';
                populateData(data);
            } catch (error) {
                alert('ERROR: ' + error.message);
            }
        });
    }
    
    if (rejectBtn) {
        const newRejectBtn = rejectBtn.cloneNode(true);
        rejectBtn.parentNode.replaceChild(newRejectBtn, rejectBtn);
        
        newRejectBtn.addEventListener('click', async () => {
            if (!confirm('Reject this invoice?')) return;
            
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.id}/reject`), {
                    method: 'POST',
                    headers: { ...getAuthHeaders() }
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Rejection failed');
                }
                
                alert('Invoice rejected successfully!');
                data.status = 'REJECTED';
                populateData(data);
            } catch (error) {
                alert('ERROR: ' + error.message);
            }
        });
    }

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

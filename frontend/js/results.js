document.addEventListener('DOMContentLoaded', () => {
    const rawData = JSON.parse(sessionStorage.getItem('lastScanResults'));
    if (!rawData) {
        window.location.href = 'index.html';
        return;
    }

    const isBatch = Array.isArray(rawData) && rawData.length > 1;
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
            if (currentIndex > 0) { currentIndex--; updateBatchUI(); }
        });
        nextBtn.addEventListener('click', () => {
            if (currentIndex < results.length - 1) { currentIndex++; updateBatchUI(); }
        });

        updateBatchUI();
    } else {
        currentData = results[0];
        populateData(currentData);
        setupActions(currentData);
    }

    // ── Edit Mode ────────────────────────────────────────────────────
    const editBtn = document.getElementById('editBtn');
    const exitEditBtn = document.getElementById('exitEditBtn');
    const saveEditBtn = document.getElementById('saveEditBtn');
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

    if (saveEditBtn) {
        saveEditBtn.addEventListener('click', async () => {
            if (!currentData || !currentData.id) {
                alert('Cannot save — invoice ID is missing.');
                return;
            }

            const payload = {
                invoice_number: currentData.invoice_number || null,
                invoice_date: currentData.invoice_date || null,
                seller_name: currentData.seller_name || null,
                seller_gstin: currentData.seller_gstin || null,
                buyer_name: currentData.buyer_name || null,
                buyer_gstin: currentData.buyer_gstin || null,
                subtotal: currentData.subtotal || null,
                cgst: currentData.cgst || null,
                sgst: currentData.sgst || null,
                igst: currentData.igst || null,
                total: currentData.total || null};

            saveEditBtn.disabled = true;
            saveEditBtn.textContent = 'Saving...';

            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${currentData.id}`), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)});

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Save failed');
                }

                // Update sessionStorage with persisted data
                if (isBatch) {
                    results[currentIndex] = currentData;
                    sessionStorage.setItem('lastScanResults', JSON.stringify(results));
                } else {
                    sessionStorage.setItem('lastScanResults', JSON.stringify(currentData));
                }

                editMode = false;
                editModeBanner.style.display = 'none';
                editBtn.style.display = 'inline-block';
                disableEditMode();
                alert('Changes saved successfully.');
            } catch (error) {
                alert('ERROR SAVING: ' + error.message);
            } finally {
                saveEditBtn.disabled = false;
                saveEditBtn.textContent = 'Save Changes';
            }
        });
    }

    function enableEditMode() {
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
            el.title = '';
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
                ? (currentData[dataKey] || 0)
                : (currentData[dataKey] || '');

            const input = document.createElement('input');
            input.type = isCurrency ? 'number' : 'text';
            input.value = currentValue;
            input.className = 'field-input';
            if (isCurrency) input.step = '0.01';

            element.classList.add('editing');
            const originalHTML = element.innerHTML;
            element.innerHTML = '';
            element.appendChild(input);
            input.focus();
            input.select();

            const saveEdit = () => {
                const newValue = isCurrency
                    ? (parseFloat(input.value) || 0)
                    : input.value.trim();
                currentData[dataKey] = newValue;
                element.classList.remove('editing');
                populateData(currentData);
                // Re-enable edit mode after repopulate clears it
                enableEditMode();
            };

            input.onblur = saveEdit;
            input.onkeydown = (e) => {
                if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
                if (e.key === 'Escape') {
                    element.classList.remove('editing');
                    element.innerHTML = originalHTML;
                }
            };
        };
    }
});

// ── Populate ─────────────────────────────────────────────────────────
function populateData(data) {
    document.getElementById('invoiceId').textContent = data.id || 'N/A';
    document.getElementById('processedTime').textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    // Duplicate warning
    const duplicateWarningBanner = document.getElementById('duplicateWarningBanner');
    const duplicateWarningMessage = document.getElementById('duplicateWarningMessage');
    const viewOriginalBtn = document.getElementById('viewOriginalBtn');

    // Case 1: Backend detected duplicate (FAILED status with is_duplicate)
    if (data.is_duplicate && data.status === 'FAILED') {
        duplicateWarningBanner.style.display = 'flex';
        duplicateWarningBanner.style.borderColor = 'var(--red)';
        duplicateWarningBanner.style.background = 'linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%)';
        duplicateWarningMessage.textContent = data.error_message || 'This invoice is a duplicate of an existing invoice.';

        viewOriginalBtn.style.display = 'inline-block';
        viewOriginalBtn.onclick = async (e) => {
            e.preventDefault();
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.is_duplicate}`), {
                    
                });
                if (!response.ok) throw new Error('Failed to load original invoice');
                const originalInvoice = await response.json();
                sessionStorage.setItem('lastScanResults', JSON.stringify(originalInvoice));
                window.location.href = 'results.html';
            } catch (error) {
                alert('ERROR: Could not load original invoice. ' + error.message);
            }
        };
    }
    // Case 2: User accepted the duplicate and chose to keep it
    else if (data._user_accepted_duplicate || data._duplicate_info) {
        const dupInfo = data._duplicate_info || {};
        duplicateWarningBanner.style.display = 'flex';
        duplicateWarningBanner.style.borderColor = 'var(--amber, #f59e0b)';
        duplicateWarningBanner.style.background = 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)';
        duplicateWarningBanner.querySelector('strong').style.color = 'var(--amber, #d97706)';
        duplicateWarningBanner.querySelector('strong').textContent = 'Possible Duplicate — Kept by User';
        duplicateWarningMessage.textContent = dupInfo.message
            || `This invoice may be a duplicate. Originally uploaded${dupInfo.original_upload_date ? ' on ' + dupInfo.original_upload_date : ''}${dupInfo.original_uploader ? ' by ' + dupInfo.original_uploader : ''}.`;

        if (dupInfo.original_invoice_id) {
            viewOriginalBtn.style.display = 'inline-block';
            viewOriginalBtn.onclick = async (e) => {
                e.preventDefault();
                try {
                    const response = await apiFetch(getApiUrl(`/api/invoices/${dupInfo.original_invoice_id}`), {
                        
                    });
                    if (!response.ok) throw new Error('Failed to load original invoice');
                    const originalInvoice = await response.json();
                    sessionStorage.setItem('lastScanResults', JSON.stringify(originalInvoice));
                    window.location.href = 'results.html';
                } catch (error) {
                    alert('ERROR: Could not load original invoice. ' + error.message);
                }
            };
        } else {
            viewOriginalBtn.style.display = 'none';
        }
    }
    // No duplicate
    else {
        duplicateWarningBanner.style.display = 'none';
    }

    // Retry button — show only for FAILED non-duplicate invoices
    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
        if (data.status === 'FAILED' && !data.is_duplicate) {
            retryBtn.style.display = 'inline-block';
            retryBtn.onclick = async () => {
                if (!confirm('This will delete the failed record so you can re-upload the file. Continue?')) return;
                retryBtn.disabled = true;
                retryBtn.textContent = 'Removing...';
                try {
                    const response = await apiFetch(getApiUrl(`/api/invoices/${data.id}/retry`), {
                        method: 'POST'});
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.detail || 'Retry failed');
                    }
                    sessionStorage.removeItem('lastScanResults');
                    alert('Record removed. Please re-upload the invoice file.');
                    window.location.href = 'upload.html';
                } catch (error) {
                    alert('ERROR: ' + error.message);
                    retryBtn.disabled = false;
                    retryBtn.textContent = 'Retry';
                }
            };
        } else {
            retryBtn.style.display = 'none';
        }
    }

    // Status badge
    const statusBadge = document.getElementById('approvalStatusBadge');
    if (statusBadge) {
        const status = data.status || 'PENDING_REVIEW';
        statusBadge.textContent = status.replace(/_/g, ' ');
        statusBadge.className = 'status-badge status-' + status.toLowerCase();
        statusBadge.style.display = 'inline-block';
    }

    // Approval buttons
    const approvalActions = document.getElementById('approvalActions');
    if (approvalActions) {
        approvalActions.style.display = data.status === 'PENDING_REVIEW' ? 'flex' : 'none';
    }

    // Edit button — only show for editable statuses
    const editBtn = document.getElementById('editBtn');
    if (editBtn) {
        editBtn.style.display = (data.status === 'PENDING_REVIEW' || data.status === 'FAILED') ? 'inline-block' : 'none';
    }

    // Entities
    document.getElementById('sellerName').textContent = (data.seller_name || 'UNKNOWN').toUpperCase();
    document.getElementById('sellerGstin').textContent = data.seller_gstin || 'NOT DETECTED';
    document.getElementById('buyerName').textContent = (data.buyer_name || 'UNKNOWN').toUpperCase();
    document.getElementById('buyerGstin').textContent = data.buyer_gstin || 'NOT DETECTED';

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
    animateCounter(document.getElementById('scoreValue'), health.score);
    const scoreCircle = document.querySelector('.score-circle');
    if (scoreCircle) {
        scoreCircle.style.setProperty('--score', health.score);
    }
    document.getElementById('gradeBadge').textContent = health.grade;
    document.getElementById('healthStatus').textContent = `HEALTH: ${health.status.toUpperCase()}`;
    document.getElementById('scoreSummary').textContent = health.summary;

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

    // Tax summary
    animateCounterValue('subtotalValue', data.subtotal || 0);
    animateCounterValue('cgstValue', data.cgst || 0);
    animateCounterValue('sgstValue', data.sgst || 0);
    animateCounterValue('igstValue', data.igst || 0);
    animateCounterValue('totalValue', data.total || 0);
}

// ── Actions ──────────────────────────────────────────────────────────
function setupActions(data) {
    // Clone to clear old listeners
    ['exportBtn', 'whatsappBtn', 'approveBtn', 'rejectBtn'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const clone = el.cloneNode(true);
        el.parentNode.replaceChild(clone, el);
    });

    const approveBtn = document.getElementById('approveBtn');
    if (approveBtn) {
        approveBtn.addEventListener('click', async () => {
            if (!confirm('Approve this invoice?')) return;
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.id}/approve`), {
                    method: 'POST'});
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Approval failed');
                }
                data.status = 'APPROVED';
                populateData(data);
            } catch (error) {
                alert('ERROR: ' + error.message);
            }
        });
    }

    const rejectBtn = document.getElementById('rejectBtn');
    if (rejectBtn) {
        rejectBtn.addEventListener('click', async () => {
            if (!confirm('Reject this invoice?')) return;
            try {
                const response = await apiFetch(getApiUrl(`/api/invoices/${data.id}/reject`), {
                    method: 'POST'});
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Rejection failed');
                }
                data.status = 'REJECTED';
                populateData(data);
            } catch (error) {
                alert('ERROR: ' + error.message);
            }
        });
    }

    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            try {
                const response = await apiFetch(getApiUrl('/api/export'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json'},
                    body: JSON.stringify(data)});
                if (!response.ok) throw new Error('EXPORT FAILED');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `invoice_${data.invoice_number || 'export'}.csv`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } catch (error) {
                alert('ERROR EXPORTING: ' + error.message);
            }
        });
    }

    const whatsappBtn = document.getElementById('whatsappBtn');
    if (whatsappBtn) {
        whatsappBtn.addEventListener('click', () => {
            const score = (data.health_score && data.health_score.score) || 0;
            const text = `Invoice Report: ${data.invoice_number || 'N/A'}\nTotal: ${formatCurrency(data.total)}\nHealth Score: ${score}/100`;
            window.open('https://wa.me/?text=' + encodeURIComponent(text));
        });
    }
}

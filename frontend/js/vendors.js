/**
 * vendors.js — Vendor management page logic.
 * Depends on: config.js, utils.js, auth.js (loaded via HTML)
 */

let allVendors = [];
let currentVendorId = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadVendors();
});

async function loadVendors() {
    const loadingState = document.getElementById('loadingState');
    const vendorsGrid = document.getElementById('vendorsGrid');
    const emptyState = document.getElementById('emptyState');

    loadingState.style.display = 'grid';
    vendorsGrid.style.display = 'none';
    emptyState.style.display = 'none';

    const response = await apiFetch(getApiUrl('/api/vendors'));

    if (!response.ok) {
        loadingState.style.display = 'none';
        emptyState.style.display = 'block';
        emptyState.innerHTML = `<div style="color: var(--red);">Failed to load vendors</div>`;
        return;
    }

    allVendors = await response.json();
    loadingState.style.display = 'none';

    if (allVendors.length === 0) {
        emptyState.style.display = 'block';
    } else {
        vendorsGrid.style.display = 'grid';
        renderVendors();
    }
}

function renderVendors() {
    const vendorsGrid = document.getElementById('vendorsGrid');

    vendorsGrid.innerHTML = allVendors.map((vendor, index) => `
        <div class="vendor-card animate-fade-up stagger-${Math.min(index + 1, 4)}" 
             onclick="showVendorDetail('${vendor.id}')">
            <div class="vendor-name">${vendor.name}</div>
            <div class="vendor-gstin">${vendor.gstin}</div>
            <div class="vendor-stats">
                <div class="vendor-stat">
                    <div class="vendor-stat-label">Invoices</div>
                    <div class="vendor-stat-value">${vendor.total_invoices}</div>
                </div>
                <div class="vendor-stat">
                    <div class="vendor-stat-label">Total</div>
                    <div class="vendor-stat-value amount">${formatCurrency(vendor.total_amount)}</div>
                </div>
            </div>
            ${renderTrustBadge(vendor.trust_score, vendor.trust_label, true)}
        </div>
    `).join('');
}

async function showVendorDetail(vendorId) {
    currentVendorId = vendorId;
    const modal = document.getElementById('vendorDetailModal');

    modal.style.display = 'flex';
    document.getElementById('vendorInvoicesTable').innerHTML = `
        <tr>
            <td colspan="4" style="text-align: center; padding: 2rem;">
                <div class="loading-spinner" style="margin: 0 auto;"></div>
            </td>
        </tr>
    `;

    const detailResponse = await apiFetch(getApiUrl(`/api/vendors/${vendorId}`));

    if (!detailResponse.ok) {
        document.getElementById('vendorInvoicesTable').innerHTML = `
            <tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--red);">Failed to load vendor details</td></tr>
        `;
        return;
    }

    const vendorDetail = await detailResponse.json();

    document.getElementById('modalVendorName').textContent = vendorDetail.name;
    
    const modalTrustScore = document.getElementById('modalTrustScore');
    if (vendorDetail.trust_label) {
        modalTrustScore.innerHTML = renderTrustBadge(vendorDetail.trust_score, vendorDetail.trust_label, false);
        modalTrustScore.style.display = 'inline-flex';
    } else {
        modalTrustScore.style.display = 'none';
    }
    
    document.getElementById('modalVendorGstin').textContent = vendorDetail.gstin;
    document.getElementById('modalTotalInvoices').textContent = vendorDetail.total_invoices;
    document.getElementById('modalTotalAmount').textContent = formatCurrency(vendorDetail.total_amount);
    document.getElementById('modalPendingInvoices').textContent = vendorDetail.pending_invoices;

    const invoicesResponse = await apiFetch(getApiUrl(`/api/vendors/${vendorId}/invoices`));

    if (!invoicesResponse.ok) {
        document.getElementById('vendorInvoicesTable').innerHTML = `
            <tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--red);">Failed to load invoices</td></tr>
        `;
        return;
    }

    const data = await invoicesResponse.json();
    const invoices = data.invoices || [];

    const tableBody = document.getElementById('vendorInvoicesTable');
    const noInvoices = document.getElementById('noInvoices');

    if (invoices.length === 0) {
        tableBody.innerHTML = '';
        noInvoices.style.display = 'block';
    } else {
        noInvoices.style.display = 'none';
        tableBody.innerHTML = invoices.map(invoice => `
            <tr onclick="window.location.href='results.html?id=${invoice.id}'" style="cursor: pointer;">
                <td class="data-font">${invoice.invoice_number || 'N/A'}</td>
                <td>${formatDate(invoice.invoice_date)}</td>
                <td class="data-font" style="font-weight: 700;">${formatCurrency(invoice.total)}</td>
                <td>${renderStatusBadge(invoice.status)}</td>
            </tr>
        `).join('');
    }
}

function closeVendorDetail() {
    document.getElementById('vendorDetailModal').style.display = 'none';
    currentVendorId = null;
}

function renderStatusBadge(status) {
    const statusMap = {
        'PENDING_REVIEW': { class: 'status-pending_review', label: 'Pending' },
        'APPROVED': { class: 'status-approved', label: 'Approved' },
        'REJECTED': { class: 'status-rejected', label: 'Rejected' },
        'PROCESSING': { class: 'status-processing', label: 'Processing' },
        'FAILED': { class: 'status-failed', label: 'Failed' }};

    const statusInfo = statusMap[status] || { class: 'status-processing', label: status };
    return `<span class="status-badge ${statusInfo.class}">${statusInfo.label}</span>`;
}

function renderTrustBadge(score, label, showBar = false) {
    if (!label) return '';
    
    let colorClass, trustIcon;
    if (label === 'Trusted') {
        colorClass = 'trust-trusted';
        trustIcon = '✅';
    } else if (label === 'Caution') {
        colorClass = 'trust-caution';
        trustIcon = '⚠️';
    } else if (label === 'Red Flag') {
        colorClass = 'trust-redflag';
        trustIcon = '🚩';
    } else {
        colorClass = 'trust-new';
        trustIcon = '🆕';
    }

    let barHtml = '';
    if (showBar && score !== null && score !== undefined) {
        let barColor = 'var(--blue)';
        if (score >= 80) barColor = 'var(--green)';
        else if (score >= 60) barColor = '#B45309';
        else barColor = 'var(--red)';
        
        barHtml = `
            <div class="trust-score-bar">
                <div class="trust-score-fill" style="width: ${score}%; background: ${barColor};"></div>
            </div>
        `;
    }

    return `
        <div style="margin-top: ${showBar ? '1rem' : '0'}; display: flex; flex-direction: column;">
            <span class="trust-badge ${colorClass}">
                ${trustIcon} ${label} ${score !== null ? `(${score})` : ''}
            </span>
            ${barHtml}
        </div>
    `;
}

// Close modal on backdrop click or Escape
document.addEventListener('click', (e) => {
    if (e.target === document.getElementById('vendorDetailModal')) {
        closeVendorDetail();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeVendorDetail();
});

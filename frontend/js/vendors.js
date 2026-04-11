/**
 * vendors.js - Vendor management functionality
 */

let allVendors = [];
let currentVendorId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadVendors();
});

/**
 * Load all vendors from API
 */
async function loadVendors() {
    const loadingState = document.getElementById('loadingState');
    const vendorsGrid = document.getElementById('vendorsGrid');
    const emptyState = document.getElementById('emptyState');

    try {
        loadingState.style.display = 'block';
        vendorsGrid.style.display = 'none';
        emptyState.style.display = 'none';

        const response = await apiFetch(getApiUrl('/api/vendors'), {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to load vendors');
        }

        allVendors = await response.json();

        loadingState.style.display = 'none';

        if (allVendors.length === 0) {
            emptyState.style.display = 'block';
        } else {
            vendorsGrid.style.display = 'grid';
            renderVendors();
        }
    } catch (error) {
        console.error('Error loading vendors:', error);
        loadingState.style.display = 'none';
        emptyState.style.display = 'block';
        emptyState.innerHTML = `
            <div style="color: var(--red);">Failed to load vendors</div>
            <p style="font-size: 0.9rem; margin-top: 1rem; text-transform: none; font-weight: 500;">
                ${error.message}
            </p>
        `;
    }
}

/**
 * Render vendor cards
 */
function renderVendors() {
    const vendorsGrid = document.getElementById('vendorsGrid');
    
    vendorsGrid.innerHTML = allVendors.map((vendor, index) => `
        <div class="vendor-card animate-fade-up stagger-${Math.min(index + 1, 4)}" 
             onclick="showVendorDetail('${vendor.id}')">
            <div class="vendor-name">${escapeHtml(vendor.name)}</div>
            <div class="vendor-gstin">${escapeHtml(vendor.gstin)}</div>
            <div class="vendor-stats">
                <div class="vendor-stat">
                    <div class="vendor-stat-label">Invoices</div>
                    <div class="vendor-stat-value">${vendor.total_invoices}</div>
                </div>
                <div class="vendor-stat">
                    <div class="vendor-stat-label">Total</div>
                    <div class="vendor-stat-value amount">₹${formatAmount(vendor.total_amount)}</div>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Show vendor detail modal
 */
async function showVendorDetail(vendorId) {
    currentVendorId = vendorId;
    const modal = document.getElementById('vendorDetailModal');
    
    try {
        // Show modal with loading state
        modal.style.display = 'flex';
        document.getElementById('vendorInvoicesTable').innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 2rem;">
                    <div class="loading-spinner" style="margin: 0 auto;"></div>
                </td>
            </tr>
        `;

        // Fetch vendor details
        const detailResponse = await apiFetch(getApiUrl(`/api/vendors/${vendorId}`), {
            headers: getAuthHeaders()
        });

        if (!detailResponse.ok) {
            throw new Error('Failed to load vendor details');
        }

        const vendorDetail = await detailResponse.json();

        // Update modal header
        document.getElementById('modalVendorName').textContent = vendorDetail.name;
        document.getElementById('modalVendorGstin').textContent = vendorDetail.gstin;
        document.getElementById('modalTotalInvoices').textContent = vendorDetail.total_invoices;
        document.getElementById('modalTotalAmount').textContent = `₹${formatAmount(vendorDetail.total_amount)}`;
        document.getElementById('modalPendingInvoices').textContent = vendorDetail.pending_invoices;

        // Fetch vendor invoices
        const invoicesResponse = await apiFetch(getApiUrl(`/api/vendors/${vendorId}/invoices`), {
            headers: getAuthHeaders()
        });

        if (!invoicesResponse.ok) {
            throw new Error('Failed to load vendor invoices');
        }

        const data = await invoicesResponse.json();
        const invoices = data.invoices || [];

        // Render invoices table
        const tableBody = document.getElementById('vendorInvoicesTable');
        const noInvoices = document.getElementById('noInvoices');

        if (invoices.length === 0) {
            tableBody.innerHTML = '';
            noInvoices.style.display = 'block';
        } else {
            noInvoices.style.display = 'none';
            tableBody.innerHTML = invoices.map(invoice => `
                <tr onclick="window.location.href='results.html?id=${invoice.id}'" style="cursor: pointer;">
                    <td class="data-font">${escapeHtml(invoice.invoice_number || 'N/A')}</td>
                    <td>${formatDate(invoice.invoice_date)}</td>
                    <td class="data-font" style="font-weight: 700;">₹${formatAmount(invoice.total)}</td>
                    <td>${renderStatusBadge(invoice.status)}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading vendor detail:', error);
        document.getElementById('vendorInvoicesTable').innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 2rem; color: var(--red);">
                    Failed to load vendor details: ${error.message}
                </td>
            </tr>
        `;
    }
}

/**
 * Close vendor detail modal
 */
function closeVendorDetail() {
    const modal = document.getElementById('vendorDetailModal');
    modal.style.display = 'none';
    currentVendorId = null;
}

/**
 * Render status badge
 */
function renderStatusBadge(status) {
    const statusMap = {
        'PENDING_REVIEW': { class: 'status-pending_review', label: 'Pending' },
        'APPROVED': { class: 'status-approved', label: 'Approved' },
        'REJECTED': { class: 'status-rejected', label: 'Rejected' },
        'PROCESSING': { class: 'status-processing', label: 'Processing' },
        'FAILED': { class: 'status-failed', label: 'Failed' },
        'SUCCESS': { class: 'status-approved', label: 'Success' }
    };

    const statusInfo = statusMap[status] || { class: 'status-processing', label: status };
    return `<span class="status-badge ${statusInfo.class}">${statusInfo.label}</span>`;
}

/**
 * Format amount with commas
 */
function formatAmount(amount) {
    if (!amount && amount !== 0) return '0.00';
    return parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('vendorDetailModal');
    if (e.target === modal) {
        closeVendorDetail();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeVendorDetail();
    }
});

let allInvoices = [];
let filteredInvoices = [];
let sortCol = 'created_at';
let sortDesc = true;
let vendors = [];

document.addEventListener('DOMContentLoaded', async () => {
    await fetchVendors();
    await fetchInvoices();
    setupFilters();
    setupSorting();
    setupBulkExport();
    setupAdvancedFilters();
});

async function fetchVendors() {
    try {
        const response = await apiFetch(getApiUrl('/api/vendors'), {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            console.error('Failed to fetch vendors');
            return;
        }
        
        vendors = await response.json();
        populateVendorDropdown();
    } catch (error) {
        console.error('Error fetching vendors:', error);
    }
}

function populateVendorDropdown() {
    const vendorFilter = document.getElementById('vendorFilter');
    
    // Clear existing options except the first one
    while (vendorFilter.options.length > 1) {
        vendorFilter.remove(1);
    }
    
    // Add vendor options
    vendors.forEach(vendor => {
        const option = document.createElement('option');
        option.value = vendor.gstin;
        option.textContent = `${vendor.name} (${vendor.gstin})`;
        vendorFilter.appendChild(option);
    });
}

async function fetchInvoices() {
    try {
        // Build query parameters from filters
        const params = new URLSearchParams();
        
        const searchQuery = document.getElementById('searchInput')?.value.trim();
        if (searchQuery) {
            params.append('q', searchQuery);
        }
        
        const statusFilter = document.getElementById('statusFilter')?.value;
        if (statusFilter) {
            params.append('status', statusFilter);
        }
        
        const vendorFilter = document.getElementById('vendorFilter')?.value;
        if (vendorFilter) {
            params.append('vendor', vendorFilter);
        }
        
        const dateFrom = document.getElementById('dateFromFilter')?.value;
        if (dateFrom) {
            params.append('date_from', dateFrom);
        }
        
        const dateTo = document.getElementById('dateToFilter')?.value;
        if (dateTo) {
            params.append('date_to', dateTo);
        }
        
        const amountMin = document.getElementById('amountMinFilter')?.value;
        if (amountMin) {
            params.append('amount_min', amountMin);
        }
        
        const amountMax = document.getElementById('amountMaxFilter')?.value;
        if (amountMax) {
            params.append('amount_max', amountMax);
        }
        
        // Set high limit to get all results for client-side operations
        params.append('limit', '1000');
        
        const url = getApiUrl('/api/invoices') + '?' + params.toString();
        const response = await apiFetch(url, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('FAILED TO FETCH INVOICES');
        
        const payload = await response.json();
        // /api/invoices returns a paginated object {items, total, page, pages}
        const data = Array.isArray(payload) ? payload : (payload.items || []);
        
        // Trust backend payload entirely. Database determines FAILED/SUCCESS natively now.
        allInvoices = data.map(inv => {
            return { ...inv, status: inv.status || 'PROCESSING' };
        });
        
        filteredInvoices = [...allInvoices];
        updateStats();
        renderTable();
    } catch (error) {
        console.error(error);
        alert('ERROR LOADING HISTORY: ' + error.message);
    }
}

function updateStats() {
    const statTotal = document.getElementById('statTotal');
    const statSuccess = document.getElementById('statSuccess');
    const statFailed = document.getElementById('statFailed');
    
    const total = allInvoices.length;
    const failedCount = allInvoices.filter(i => i.status === 'FAILED').length;
    const successCount = allInvoices.filter(i => i.status === 'SUCCESS').length;
    
    statTotal.textContent = total;
    statFailed.textContent = failedCount;
    
    const rate = total === 0 ? 0 : Math.round((successCount / total) * 100);
    statSuccess.textContent = `${rate}%`;
}

function renderTable() {
    const tbody = document.getElementById('historyTableBody');
    const emptyState = document.getElementById('emptyState');
    const recordCount = document.getElementById('recordCount');
    const tableEl = document.getElementById('historyTable');
    
    tbody.innerHTML = '';
    recordCount.textContent = filteredInvoices.length;

    if (filteredInvoices.length === 0) {
        tableEl.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    tableEl.style.display = 'table';
    emptyState.style.display = 'none';

    // Apply Sorting
    filteredInvoices.sort((a, b) => {
        let valA = a[sortCol];
        let valB = b[sortCol];
        
        if (sortCol === 'total') {
            valA = parseFloat(valA);
            valB = parseFloat(valB);
        }

        if (valA < valB) return sortDesc ? 1 : -1;
        if (valA > valB) return sortDesc ? -1 : 1;
        return 0;
    });

    filteredInvoices.forEach(inv => {
        const row = document.createElement('tr');
        row.dataset.id = inv.id;
        
        // Status Pill HTML - handle all status types
        let pillClass = '';
        let statusText = inv.status;
        
        if (inv.status === 'SUCCESS' || inv.status === 'APPROVED') {
            pillClass = 'pill-success';
            statusText = inv.status === 'APPROVED' ? 'APPROVED' : 'SUCCESS';
        } else if (inv.status === 'FAILED' || inv.status === 'REJECTED') {
            pillClass = 'pill-failed';
            statusText = inv.status === 'REJECTED' ? 'REJECTED' : 'FAILED';
        } else if (inv.status === 'PROCESSING' || inv.status === 'PENDING_REVIEW') {
            pillClass = 'pill-processing';
            statusText = inv.status === 'PENDING_REVIEW' ? 'PENDING' : 'PROCESSING';
        }
        
        const pillHtml = `<span class="status-pill ${pillClass}">
            ${(inv.status === 'SUCCESS' || inv.status === 'APPROVED') ? '✓ ' : ''}${(inv.status === 'FAILED' || inv.status === 'REJECTED') ? '✖ ' : ''}${(inv.status === 'PROCESSING' || inv.status === 'PENDING_REVIEW') ? '⏳ ' : ''}${statusText}
        </span>`;

        row.innerHTML = `
            <td class="data-font" style="color: var(--blue); font-weight: 800;">#${inv.id}</td>
            <td style="font-weight: 800; font-family: var(--display); font-size: 1.1rem; color: var(--ink);">${(inv.seller_name || 'UNKNOWN').toUpperCase()}</td>
            <td class="data-font" style="color: var(--ink); font-weight: 800;">${formatCurrency(inv.total)}</td>
            <td>${pillHtml}</td>
            <td class="data-font" style="color: var(--muted);">${formatDate(inv.invoice_date)}</td>
            <td class="data-font" style="color: var(--muted); font-size: 0.85rem;">${new Date(inv.created_at).toLocaleString('en-IN')}</td>
        `;
        
        // Only allow viewing if not failed
        if (inv.status !== 'FAILED') {
            row.addEventListener('click', () => viewInvoiceDetail(inv));
        } else {
            row.style.opacity = '0.7';
            row.style.cursor = 'not-allowed';
            row.addEventListener('click', () => alert('CANNOT VIEW FAILED SCANS. RECORD BLOCK HAS BEEN QUARANTINED.'));
        }
        
        tbody.appendChild(row);
    });
}

function setupFilters() {
    const input = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const vendorFilter = document.getElementById('vendorFilter');
    const dateFromFilter = document.getElementById('dateFromFilter');
    const dateToFilter = document.getElementById('dateToFilter');
    const amountMinFilter = document.getElementById('amountMinFilter');
    const amountMaxFilter = document.getElementById('amountMaxFilter');

    // Debounce function to avoid too many API calls
    let debounceTimer;
    function debounceFilter() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchInvoices();
        }, 500);
    }

    // Attach event listeners
    input.addEventListener('input', debounceFilter);
    statusFilter.addEventListener('change', () => fetchInvoices());
    vendorFilter.addEventListener('change', () => fetchInvoices());
    dateFromFilter.addEventListener('change', () => fetchInvoices());
    dateToFilter.addEventListener('change', () => fetchInvoices());
    amountMinFilter.addEventListener('input', debounceFilter);
    amountMaxFilter.addEventListener('input', debounceFilter);
}

function setupAdvancedFilters() {
    const toggleBtn = document.getElementById('toggleFiltersBtn');
    const advancedPanel = document.getElementById('advancedFilters');
    const clearBtn = document.getElementById('clearFiltersBtn');
    
    toggleBtn.addEventListener('click', () => {
        if (advancedPanel.style.display === 'none') {
            advancedPanel.style.display = 'block';
            toggleBtn.textContent = '🔧 Hide Filters';
        } else {
            advancedPanel.style.display = 'none';
            toggleBtn.textContent = '🔧 More Filters';
        }
    });
    
    clearBtn.addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        document.getElementById('statusFilter').value = '';
        document.getElementById('vendorFilter').value = '';
        document.getElementById('dateFromFilter').value = '';
        document.getElementById('dateToFilter').value = '';
        document.getElementById('amountMinFilter').value = '';
        document.getElementById('amountMaxFilter').value = '';
        fetchInvoices();
    });
}

function setupSorting() {
    const headers = document.querySelectorAll('.sortable');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const col = header.dataset.sort;
            if (sortCol === col) {
                sortDesc = !sortDesc;
            } else {
                sortCol = col;
                sortDesc = true;
            }
            
            headers.forEach(h => h.querySelector('.sort-icon').textContent = '▼');
            header.querySelector('.sort-icon').textContent = sortDesc ? '▼' : '▲';
            
            renderTable();
        });
    });
}

function setupBulkExport() {
    const bulkExportBtn = document.getElementById('bulkExportBtn');
    
    bulkExportBtn.addEventListener('click', async () => {
        if (filteredInvoices.length === 0) {
            alert('NO INVOICES TO EXPORT');
            return;
        }

        const confirmed = confirm(`Export ${filteredInvoices.length} invoice(s) to CSV?`);
        if (!confirmed) return;

        bulkExportBtn.disabled = true;
        bulkExportBtn.textContent = 'Exporting...';

        try {
            // Create CSV content
            const csvRows = [];
            
            // Header
            csvRows.push([
                'Invoice ID',
                'Invoice Number',
                'Seller Name',
                'Seller GSTIN',
                'Buyer Name',
                'Buyer GSTIN',
                'Invoice Date',
                'Subtotal',
                'CGST',
                'SGST',
                'IGST',
                'Total',
                'Status',
                'Scanned At'
            ].join(','));

            // Data rows
            filteredInvoices.forEach(inv => {
                const row = [
                    inv.id || '',
                    `"${(inv.invoice_number || '').replace(/"/g, '""')}"`,
                    `"${(inv.seller_name || '').replace(/"/g, '""')}"`,
                    inv.seller_gstin || '',
                    `"${(inv.buyer_name || '').replace(/"/g, '""')}"`,
                    inv.buyer_gstin || '',
                    inv.invoice_date || '',
                    inv.subtotal || 0,
                    inv.cgst || 0,
                    inv.sgst || 0,
                    inv.igst || 0,
                    inv.total || 0,
                    inv.status || '',
                    new Date(inv.created_at).toISOString()
                ];
                csvRows.push(row.join(','));
            });

            const csvContent = csvRows.join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            
            const today = new Date().toISOString().split('T')[0];
            const filename = `invoices_export_${today}.csv`;
            
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Export error:', error);
            alert('EXPORT FAILED: ' + error.message);
        } finally {
            bulkExportBtn.disabled = false;
            bulkExportBtn.textContent = '📥 Export All';
        }
    });
}

async function viewInvoiceDetail(invoiceSummary) {
    const partialData = {
        ...invoiceSummary,
        health_score: { score: 100, grade: '-', status: 'Verified', issues: [], warnings: [], summary: 'Record retrieved from archive. Full item-level verification details persist in local nodes.' }
    };
    sessionStorage.setItem('lastScanResults', JSON.stringify(partialData));
    window.location.href = 'results.html';
}

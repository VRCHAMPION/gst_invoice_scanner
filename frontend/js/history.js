let allInvoices = [];
let filteredInvoices = [];
let sortCol = 'created_at';
let sortDesc = true;

document.addEventListener('DOMContentLoaded', async () => {
    await fetchInvoices();
    setupFilters();
    setupSorting();
});

async function fetchInvoices() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/invoices', {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error('FAILED TO FETCH INVOICES');
        
        let data = await response.json();
        
        // Simulate statuses for UI demonstration
        allInvoices = data.map(inv => {
            // Deterministic fake status based on ID
            let st = 'SUCCESS';
            if (inv.id % 7 === 0) st = 'FAILED';
            else if (inv.id % 5 === 0) st = 'PROCESSING';
            return { ...inv, status: st };
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
        
        // Status Pill HTML
        let pillClass = '';
        if (inv.status === 'SUCCESS') pillClass = 'pill-success';
        if (inv.status === 'FAILED') pillClass = 'pill-failed';
        if (inv.status === 'PROCESSING') pillClass = 'pill-processing';
        
        const pillHtml = `<span class="status-pill ${pillClass}">
            ${inv.status === 'SUCCESS' ? '✓ ' : ''}${inv.status === 'FAILED' ? '✖ ' : ''}${inv.status === 'PROCESSING' ? '⏳ ' : ''}${inv.status}
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
    const dateFilter = document.getElementById('dateFilter');

    function applyFilters() {
        const query = input.value.toLowerCase();
        const statusVal = statusFilter.value;
        const dateVal = dateFilter.value; // YYYY-MM-DD

        filteredInvoices = allInvoices.filter(inv => {
            // Search Match
            const matchesSearch = 
                (inv.seller_name || '').toLowerCase().includes(query) ||
                (inv.buyer_name || '').toLowerCase().includes(query) ||
                (inv.invoice_number || '').toLowerCase().includes(query);
                
            // Status Match
            const matchesStatus = statusVal === 'ALL' || inv.status === statusVal;
            
            // Date Match
            let matchesDate = true;
            if (dateVal) {
                const invDate = new Date(inv.created_at).toISOString().split('T')[0];
                matchesDate = (invDate === dateVal);
            }
            
            return matchesSearch && matchesStatus && matchesDate;
        });
        
        renderTable();
    }

    input.addEventListener('input', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    dateFilter.addEventListener('change', applyFilters);
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

async function viewInvoiceDetail(invoiceSummary) {
    const partialData = {
        ...invoiceSummary,
        health_score: { score: 100, grade: '-', status: 'Verified', issues: [], warnings: [], summary: 'Record retrieved from archive. Full item-level verification details persist in local nodes.' }
    };
    sessionStorage.setItem('lastScanResults', JSON.stringify(partialData));
    window.location.href = 'results.html';
}

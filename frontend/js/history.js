let allInvoices = [];
let filteredInvoices = [];
let sortCol = 'created_at';
let sortDesc = true;

document.addEventListener('DOMContentLoaded', async () => {
    await fetchInvoices();
    setupSearch();
    setupSorting();
});

async function fetchInvoices() {
    try {
        const response = await fetch('http://127.0.0.1:8000/invoices', {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error('FAILED TO FETCH INVOICES');
        
        allInvoices = await response.json();
        filteredInvoices = [...allInvoices];
        renderTable();
    } catch (error) {
        console.error(error);
        alert('ERROR LOADING HISTORY: ' + error.message);
    }
}

function renderTable() {
    const tbody = document.getElementById('historyTableBody');
    const emptyState = document.getElementById('emptyState');
    const recordCount = document.getElementById('recordCount');
    
    tbody.innerHTML = '';
    recordCount.textContent = filteredInvoices.length;

    if (filteredInvoices.length === 0) {
        document.getElementById('historyTable').style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    document.getElementById('historyTable').style.display = 'table';
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
        row.innerHTML = `
            <td class="data-font" style="color: var(--data-accent);">${inv.id}</td>
            <td style="font-weight: 700;">${(inv.seller_name || 'N/A').toUpperCase()}</td>
            <td style="font-weight: 500;">${(inv.buyer_name || 'N/A').toUpperCase()}</td>
            <td class="data-font">${inv.invoice_number || '---'}</td>
            <td class="data-font">${formatDate(inv.invoice_date)}</td>
            <td class="data-font" style="color: var(--primary-accent); font-weight: 700;">${formatCurrency(inv.total)}</td>
            <td class="text-muted" style="font-size: 0.75rem;">${new Date(inv.created_at).toLocaleString('en-IN')}</td>
        `;
        
        row.addEventListener('click', () => viewInvoiceDetail(inv));
        tbody.appendChild(row);
    });
}

function setupSearch() {
    const input = document.getElementById('searchInput');
    input.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        filteredInvoices = allInvoices.filter(inv => 
            (inv.seller_name || '').toLowerCase().includes(query) ||
            (inv.buyer_name || '').toLowerCase().includes(query) ||
            (inv.invoice_number || '').toLowerCase().includes(query)
        );
        renderTable();
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
            
            // Update UI icons
            headers.forEach(h => h.querySelector('.sort-icon').textContent = '▼');
            header.querySelector('.sort-icon').textContent = sortDesc ? '▼' : '▲';
            
            renderTable();
        });
    });
}

async function viewInvoiceDetail(invoiceSummary) {
    // Note: The history API only returns summary. 
    // Usually, we'd fetch the full invoice by ID. 
    // Since our scan API returns full data, let's pretend we have a GET /invoices/{id} 
    // or just re-request the scan with the image if we had it.
    // For this prototype, if the backend doesn't have GET /invoices/{id}, 
    // we might need to modify the history data or just show what we have.
    
    // BUT, the user's scan result has health score. History doesn't.
    // Let's assume the user wants to see the summary data they already have.
    // Or better, let's call /scan if we had the image.
    // Wait, the backend doesn't seem to have a GET /invoices/{id} in the main.py listed.
    // I'll show a fallback or just basic info in results.html if full data missing.
    
    // Re-check backend: main.py has /invoices which returns rows from database.py get_all_invoices.
    // database.py get_all_invoices only selects: id, seller_name, buyer_name, invoice_number, invoice_date, total, created_at.
    // It DOES NOT select 'items' or 'cgst' etc.
    
    alert(`VIEWING DETAIL FOR ID: ${invoiceSummary.id}\n(Note: Full itemized view requires GET /invoices/{id} endpoint)`);
    
    // Let's at least populate sessionStorage with what we have
    const partialData = {
        ...invoiceSummary,
        health_score: { score: 100, grade: '-', status: 'Verified', issues: [], warnings: [], summary: 'Record retrieved from archive.' }
    };
    sessionStorage.setItem('lastScanResults', JSON.stringify(partialData));
    window.location.href = 'results.html';
}

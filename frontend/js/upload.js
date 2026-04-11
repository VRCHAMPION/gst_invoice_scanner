document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const scanBtn = document.getElementById('scanBtn');
    const previewContainer = document.getElementById('previewContainer');
    const uploadQueueContainer = document.getElementById('uploadQueueContainer');
    const uploadQueue = document.getElementById('uploadQueue');
    const queueCount = document.getElementById('queueCount');
    const clearQueueBtn = document.getElementById('clearQueueBtn');
    const processQueueBtn = document.getElementById('processQueueBtn');
    
    const overlay = document.getElementById('overlay');
    const processStatus = document.getElementById('processStatus');
    const uploadProgress = document.getElementById('uploadProgress');

    let fileQueue = [];
    const MAX_FILES = 20;

    loadRecentScans();

    dropZone.addEventListener('click', (e) => {
        if (e.target.closest('#uploadQueueContainer')) return;
        fileInput.click();
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, () => dropZone.classList.remove('drag-over'));
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        const files = Array.from(e.dataTransfer.files);
        handleMultipleFiles(files);
    });

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleMultipleFiles(files);
    });

    clearQueueBtn.addEventListener('click', () => {
        if (confirm('Clear all files from queue?')) {
            fileQueue = [];
            updateQueueUI();
        }
    });

    processQueueBtn.addEventListener('click', () => {
        if (fileQueue.length === 0) return;
        processAllFiles();
    });

    function handleMultipleFiles(files) {
        const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
        const validFiles = files.filter(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            return allowedTypes.includes(file.type) || ['pdf', 'jpg', 'jpeg', 'png'].includes(ext);
        });

        if (validFiles.length === 0) {
            alert('PLEASE SELECT VALID FILES (JPG, PNG, PDF)');
            return;
        }

        const remainingSlots = MAX_FILES - fileQueue.length;
        if (validFiles.length > remainingSlots) {
            alert(`MAXIMUM ${MAX_FILES} FILES ALLOWED. Adding first ${remainingSlots} files.`);
            validFiles.splice(remainingSlots);
        }

        validFiles.forEach(file => {
            fileQueue.push({
                id: Date.now() + Math.random(),
                file: file,
                status: 'pending',
                jobId: null,
                result: null
            });
        });

        updateQueueUI();
        fileInput.value = '';
    }

    function updateQueueUI() {
        if (fileQueue.length === 0) {
            uploadQueueContainer.style.display = 'none';
            previewContainer.style.display = 'none';
            scanBtn.style.opacity = '0.5';
            scanBtn.style.pointerEvents = 'none';
            return;
        }

        uploadQueueContainer.style.display = 'block';
        previewContainer.style.display = 'none';
        scanBtn.style.display = 'none';
        queueCount.textContent = fileQueue.length;

        uploadQueue.innerHTML = '';
        fileQueue.forEach((item, index) => {
            const queueItem = createQueueItem(item, index);
            uploadQueue.appendChild(queueItem);
        });
    }

    function createQueueItem(item, index) {
        const div = document.createElement('div');
        div.className = 'queue-item';
        div.dataset.id = item.id;

        if (item.status === 'processing') div.classList.add('processing');
        if (item.status === 'success') div.classList.add('success');
        if (item.status === 'failed') div.classList.add('failed');

        const fileSize = item.file.size > 1024 * 1024 
            ? `${(item.file.size / 1024 / 1024).toFixed(2)} MB`
            : `${(item.file.size / 1024).toFixed(2)} KB`;

        let statusBadge = '';
        if (item.status === 'pending') {
            statusBadge = '<span class="queue-item-status" style="background: var(--bg2); color: var(--muted);">PENDING</span>';
        } else if (item.status === 'processing') {
            statusBadge = '<span class="queue-item-status" style="background: var(--blue); color: white;">PROCESSING...</span>';
        } else if (item.status === 'success') {
            statusBadge = '<span class="queue-item-status" style="background: var(--green); color: white;">✓ SUCCESS</span>';
        } else if (item.status === 'failed') {
            statusBadge = '<span class="queue-item-status" style="background: var(--red); color: white;">✖ FAILED</span>';
        }

        div.innerHTML = `
            <div class="queue-item-icon">📄</div>
            <div class="queue-item-info">
                <div class="queue-item-name">${item.file.name}</div>
                <div class="queue-item-size">${fileSize}</div>
            </div>
            ${statusBadge}
            ${item.status === 'pending' ? `<button class="queue-item-remove" onclick="removeFromQueue(${index})">×</button>` : ''}
        `;

        return div;
    }

    window.removeFromQueue = (index) => {
        fileQueue.splice(index, 1);
        updateQueueUI();
    };

    async function processAllFiles() {
        overlay.style.display = 'flex';
        processStatus.textContent = `PROCESSING ${fileQueue.length} INVOICES...`;
        uploadProgress.style.width = '10%';

        const results = [];
        let processed = 0;

        for (let i = 0; i < fileQueue.length; i++) {
            const item = fileQueue[i];
            if (item.status !== 'pending') continue;

            item.status = 'processing';
            updateQueueUI();

            try {
                const user = JSON.parse(sessionStorage.getItem('currentUser'));
                const companyId = user ? user.company_id : null;
                
                if (!companyId) {
                    throw new Error("NO COMPANY ASSOCIATED");
                }

                const formData = new FormData();
                formData.append('file', item.file);
                formData.append('company_id', companyId);

                const response = await apiFetch(getApiUrl('/api/scan'), {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: formData
                });

                if (!response.ok) throw new Error(`UPLOAD FAILED`);

                const data = await response.json();
                item.jobId = data.job_id;

                // Poll for result
                const result = await pollJobStatusSync(data.job_id);
                
                if (result.status === 'completed') {
                    item.status = 'success';
                    item.result = result;
                    results.push(result);
                } else {
                    item.status = 'failed';
                }

            } catch (error) {
                console.error('Processing error:', error);
                item.status = 'failed';
            }

            processed++;
            const progress = 10 + (processed / fileQueue.length) * 85;
            uploadProgress.style.width = `${progress}%`;
            updateQueueUI();
        }

        uploadProgress.style.width = '100%';
        processStatus.textContent = `COMPLETE! PROCESSED ${results.length}/${fileQueue.length} INVOICES`;

        setTimeout(() => {
            overlay.style.display = 'none';
            
            if (results.length > 0) {
                sessionStorage.setItem('lastScanResults', JSON.stringify(results));
                window.location.href = 'results.html';
            } else {
                alert('ALL UPLOADS FAILED. PLEASE TRY AGAIN.');
            }
        }, 1000);
    }

    async function pollJobStatusSync(jobId) {
        const MAX_POLLS = 30;
        let pollCount = 0;

        while (pollCount < MAX_POLLS) {
            try {
                const res = await apiFetch(getApiUrl(`/api/scan/status/${jobId}`), {
                    headers: getAuthHeaders()
                });
                
                if (!res.ok) throw new Error("Status check failed");
                
                const job = await res.json();

                if (job.status === "completed" || job.status === "failed") {
                    return job;
                }

                await new Promise(resolve => setTimeout(resolve, 2000));
                pollCount++;
            } catch (err) {
                console.error("Polling error:", err);
                pollCount++;
            }
        }

        return { status: 'failed', error: 'Timeout' };
    }

    // Legacy single file support (kept for backward compatibility)
    scanBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        if (fileQueue.length === 1) {
            processAllFiles();
        }
    });

    async function loadRecentScans() {
        const container = document.getElementById('recentScansContainer');
        if (!container) return;
        
        try {
            const response = await apiFetch(getApiUrl('/api/invoices'), {
                headers: getAuthHeaders()
            });
            if (!response.ok) throw new Error('Fetch failed');
            const payload = await response.json();
            const invoices = Array.isArray(payload) ? payload : (payload.items || []);
            
            container.innerHTML = '';
            
            const recent = invoices.slice(0, 3);
            
            if (recent.length === 0) {
                container.innerHTML = '<div style="color: var(--muted); font-size: 0.85rem; text-align: center; padding: 1rem;">NO RECENT SCANS</div>';
                return;
            }

            recent.forEach(inv => {
                const st = inv.status || 'PROCESSING';
                let pillClass = 'st-processing';
                if (st === 'SUCCESS')    pillClass = 'st-success';
                else if (st === 'FAILED') pillClass = 'st-failed';

                const fileName = inv.seller_name ? `${inv.seller_name}_${inv.invoice_number || inv.id}` : `SCAN_DATA_${inv.id}`;
                
                const itemHTML = `
                    <div class="recent-item">
                        <div class="recent-title" title="${fileName}">${fileName}</div>
                        <div class="status-pill ${pillClass}">${st}</div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', itemHTML);
            });
            
        } catch (error) {
            console.error('Recent scans error:', error);
            container.innerHTML = '<div style="color: var(--red); font-size: 0.85rem; text-align: center; padding: 1rem;">ARCHIVE OFFLINE</div>';
        }
    }
});

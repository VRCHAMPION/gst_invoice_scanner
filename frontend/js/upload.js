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
            statusBadge = '<span class="queue-item-status" style="background: var(--green); color: white;">SUCCESS</span>';
        } else if (item.status === 'failed') {
            statusBadge = '<span class="queue-item-status" style="background: var(--red); color: white;">FAILED</span>';
        }

        div.innerHTML = `
            <div class="queue-item-icon" style="font-size: 0.7rem; font-weight: 700; color: var(--muted); font-family: var(--mono);">FILE</div>
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
                                        body: formData
                });

                if (!response.ok) throw new Error(`UPLOAD FAILED`);

                const data = await response.json();
                item.jobId = data.job_id;

                // Poll for result
                const result = await pollJobStatusSync(data.job_id);
                
                if (result.status === 'PENDING_REVIEW' || result.status === 'APPROVED' || result.status === 'SUCCESS' || result.status === 'COMPLETED') {
                    // Check for duplicate after successful extraction
                    const dupInfo = await checkDuplicateFromResult(result);
                    if (dupInfo && dupInfo.is_duplicate) {
                        result._duplicate_info = dupInfo;
                    }
                    item.status = 'success';
                    item.result = result;
                    results.push(result);
                } else if (result.is_duplicate) {
                    // Backend already detected duplicate during processing
                    overlay.style.display = 'none';
                    const userChoice = await showDuplicateAlert(item.file.name, result);
                    overlay.style.display = 'flex';

                    if (userChoice === 'keep') {
                        // User chose to keep — mark result as a flagged duplicate but still show it
                        result._user_accepted_duplicate = true;
                        result.status = 'completed';
                        item.status = 'success';
                        item.result = result;
                        results.push(result);
                    } else {
                        // User chose to discard
                        item.status = 'failed';
                        item.discarded = true;
                    }
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
        const discardedCount = fileQueue.filter(f => f.discarded).length;
        const successMsg = discardedCount > 0
            ? `COMPLETE! PROCESSED ${results.length}/${fileQueue.length} INVOICES (${discardedCount} DUPLICATES DISCARDED)`
            : `COMPLETE! PROCESSED ${results.length}/${fileQueue.length} INVOICES`;
        processStatus.textContent = successMsg;

        setTimeout(() => {
            overlay.style.display = 'none';
            
            if (results.length > 0) {
                sessionStorage.setItem('lastScanResults', JSON.stringify(results));
                window.location.href = 'results.html';
            } else {
                alert('ALL UPLOADS FAILED OR WERE DISCARDED. PLEASE TRY AGAIN.');
            }
        }, 1000);
    }

    /**
     * Check if a completed scan result is a duplicate by calling the backend endpoint.
     */
    async function checkDuplicateFromResult(result) {
        if (!result.invoice_number) return null;
        try {
            const res = await apiFetch(getApiUrl('/api/invoices/check-duplicate'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    invoice_number: result.invoice_number,
                    seller_gstin: result.seller_gstin || null})});
            if (!res.ok) return null;
            return await res.json();
        } catch {
            return null;
        }
    }

    /**
     * Show a styled duplicate warning modal and return 'keep' or 'discard'.
     */
    function showDuplicateAlert(fileName, result) {
        return new Promise((resolve) => {
            // Create modal overlay
            const modal = document.createElement('div');
            modal.id = 'duplicateModal';
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.6); backdrop-filter: blur(6px);
                z-index: 3000; display: flex; justify-content: center; align-items: center;
                animation: fadeIn 0.2s ease;
            `;

            const errorMsg = result.error_message || 'This invoice appears to be a duplicate.';
            const invoiceNum = result.invoice_number || result.raw_json?.invoice_number || 'Unknown';
            const sellerName = result.seller_name || result.raw_json?.seller_name || '';
            const sellerGstin = result.seller_gstin || result.raw_json?.seller_gstin || '';

            modal.innerHTML = `
                <div style="
                    background: white; border-radius: 16px; padding: 2.5rem;
                    max-width: 520px; width: 90%; box-shadow: 0 25px 60px rgba(0,0,0,0.3);
                    animation: slideUp 0.3s ease;
                ">
                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                        <div style="
                            width: 56px; height: 56px; border-radius: 50%;
                            background: linear-gradient(135deg, #fff5f5, #ffe0e0);
                            display: flex; align-items: center; justify-content: center;
                            font-size: 1.8rem; flex-shrink: 0;
                        ">⚠️</div>
                        <div>
                            <h2 style="font-size: 1.4rem; font-weight: 800; color: #dc2626; margin: 0; line-height: 1.2;">
                                Duplicate Invoice Detected
                            </h2>
                            <p style="font-size: 0.8rem; color: #888; margin-top: 4px; font-family: monospace;">
                                ${fileName}
                            </p>
                        </div>
                    </div>

                    <div style="
                        background: linear-gradient(135deg, #fef2f2, #fef9f9);
                        border: 1px solid #fecaca; border-left: 4px solid #dc2626;
                        border-radius: 8px; padding: 1.2rem; margin-bottom: 1.5rem;
                    ">
                        <p style="margin: 0; font-size: 0.9rem; color: #333; line-height: 1.5;">
                            ${errorMsg}
                        </p>
                    </div>

                    <div style="
                        background: #f8f8f6; border-radius: 8px; padding: 1rem;
                        margin-bottom: 1.5rem; border: 1px solid #e5e5e5;
                    ">
                        <div style="font-size: 0.7rem; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">
                            Invoice Details
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <div>
                                <div style="font-size: 0.7rem; color: #aaa;">Invoice #</div>
                                <div style="font-weight: 700; font-family: monospace; font-size: 0.9rem;">${invoiceNum}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.7rem; color: #aaa;">Seller</div>
                                <div style="font-weight: 700; font-size: 0.9rem;">${sellerName || sellerGstin || 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    <p style="font-size: 0.85rem; color: #666; margin-bottom: 1.5rem; line-height: 1.5;">
                        This invoice looks like a duplicate. <strong>Are you sure you want to keep it?</strong>
                    </p>

                    <div style="display: flex; gap: 0.8rem;">
                        <button id="dupDiscardBtn" style="
                            flex: 1; padding: 0.9rem; border: 2px solid #e5e5e5; background: white;
                            border-radius: 10px; font-weight: 700; font-size: 0.85rem;
                            cursor: pointer; transition: all 0.2s; color: #333;
                        ">Discard</button>
                        <button id="dupKeepBtn" style="
                            flex: 1.3; padding: 0.9rem; border: none;
                            background: linear-gradient(135deg, #dc2626, #b91c1c);
                            color: white; border-radius: 10px; font-weight: 700;
                            font-size: 0.85rem; cursor: pointer; transition: all 0.2s;
                            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
                        ">Keep Anyway</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Add animation keyframes if not present
            if (!document.getElementById('dupModalStyles')) {
                const style = document.createElement('style');
                style.id = 'dupModalStyles';
                style.textContent = `
                    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                    @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
                    #dupDiscardBtn:hover { background: #f3f3f3; border-color: #ccc; }
                    #dupKeepBtn:hover { box-shadow: 0 6px 20px rgba(220, 38, 38, 0.4); transform: translateY(-1px); }
                `;
                document.head.appendChild(style);
            }

            modal.querySelector('#dupKeepBtn').addEventListener('click', () => {
                modal.remove();
                resolve('keep');
            });

            modal.querySelector('#dupDiscardBtn').addEventListener('click', () => {
                modal.remove();
                resolve('discard');
            });
        });
    }

    async function pollJobStatusSync(jobId) {
        const MAX_POLLS = 60;   // 60 × 3s = 3 minutes max
        let pollCount = 0;

        while (pollCount < MAX_POLLS) {
            try {
                const res = await apiFetch(getApiUrl(`/api/scan/status/${jobId}`));
                
                if (!res.ok) throw new Error("Status check failed");
                
                const job = await res.json();
                const st = (job.status || '').toUpperCase();

                // Terminal states — stop polling
                if (st === 'PENDING_REVIEW' || st === 'APPROVED' || st === 'SUCCESS' ||
                    st === 'COMPLETED' || st === 'FAILED') {
                    job.status = st;   // normalise to uppercase for the rest of the code
                    return job;
                }

                await new Promise(resolve => setTimeout(resolve, 3000));
                pollCount++;
            } catch (err) {
                console.error("Polling error:", err);
                await new Promise(resolve => setTimeout(resolve, 3000));
                pollCount++;
            }
        }

        return { status: 'FAILED', error: 'Timeout — invoice may still be processing. Check History page.' };
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

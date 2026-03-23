document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const scanBtn = document.getElementById('scanBtn');
    const previewContainer = document.getElementById('previewContainer');
    const fileNameDisplay = document.getElementById('fileName');
    const fileSizeDisplay = document.getElementById('fileSize');
    const fileThumbnail = document.getElementById('fileThumbnail');
    const fileTypeIcon = document.getElementById('fileTypeIcon');
    const removeFileBtn = document.getElementById('removeFileBtn');
    
    const overlay = document.getElementById('overlay');
    const processStatus = document.getElementById('processStatus');
    const uploadProgress = document.getElementById('uploadProgress');

    let selectedFile = null;

    // Load dynamic recent widget data
    loadRecentScans();

    // Trigger file input
    dropZone.addEventListener('click', (e) => {
        // Prevent click if clicking the preview container or its children
        if (e.target.closest('#previewContainer')) return;
        fileInput.click();
    });

    // Drag and drop handlers
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
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetSelection();
    });

    function resetSelection() {
        selectedFile = null;
        fileInput.value = '';
        previewContainer.style.display = 'none';
        scanBtn.style.opacity = '0.5';
        scanBtn.style.pointerEvents = 'none';
        dropZone.style.borderColor = 'var(--border)';
    }

    function handleFileSelection(file) {
        const allowedTypes = [
            'image/jpeg', 'image/png', 'application/pdf'
        ];
        
        const ext = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(file.type) && !['pdf', 'jpg', 'jpeg', 'png'].includes(ext)) {
            alert('PLEASE SELECT A VALID FILE (JPG, PNG, PDF)');
            return;
        }
        
        selectedFile = file;
        
        fileNameDisplay.textContent = file.name;
        // Format size to KB or MB
        if (file.size > 1024 * 1024) {
            fileSizeDisplay.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        } else {
            fileSizeDisplay.textContent = `${(file.size / 1024).toFixed(2)} KB`;
        }

        // Handle Thumbnail
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                fileThumbnail.src = e.target.result;
                fileThumbnail.style.display = 'block';
                fileTypeIcon.style.display = 'none';
            };
            reader.readAsDataURL(file);
        } else {
            fileThumbnail.style.display = 'none';
            fileTypeIcon.style.display = 'block';
            fileTypeIcon.textContent = '📄';
        }

        previewContainer.style.display = 'block';
        scanBtn.style.opacity = '1';
        scanBtn.style.pointerEvents = 'auto';
        dropZone.style.borderColor = 'var(--blue)';
    }

    scanBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        overlay.style.display = 'flex';
        uploadProgress.style.width = '10%'; // initial progress
        processStatus.textContent = 'INITIATING SECURE UPLOAD...';

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await fetch('http://127.0.0.1:8000/scan', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });

            if (!response.ok) throw new Error(`UPLOAD FAILED`);

            const data = await response.json();
            if (data.job_id) {
                pollJobStatus(data.job_id);
            } else {
                throw new Error("Invalid response from server");
            }
        } catch (error) {
            console.error(error);
            alert(`CRITICAL ERROR DURING SCAN: ${error.message}`);
            overlay.style.display = 'none';
        }
    });

    let pollingInterval;

    function pollJobStatus(jobId) {
        processStatus.textContent = 'EXTRACTING CONTENT VIA NEURAL OCR...';
        uploadProgress.style.width = '45%';
        
        let pollCount = 0;
        
        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`http://127.0.0.1:8000/scan/status/${jobId}`, {
                    headers: getAuthHeaders()
                });
                if (!res.ok) throw new Error("Status check failed");
                
                const job = await res.json();
                pollCount++;
                
                if (job.status === "completed") {
                    clearInterval(pollingInterval);
                    uploadProgress.style.width = '100%';
                    processStatus.textContent = 'COMPLETE! REDIRECTING...';
                    
                    setTimeout(() => {
                        sessionStorage.setItem('lastScanResults', JSON.stringify(job));
                        window.location.href = 'results.html';
                    }, 500);
                } else if (job.status === "failed") {
                    clearInterval(pollingInterval);
                    alert("OCR FAILED: " + job.error);
                    overlay.style.display = 'none';
                } else {
                    // processing...
                    if (pollCount > 2) {
                        processStatus.textContent = 'VALIDATING GSTIN & COMPUTING TAXES...';
                        uploadProgress.style.width = '75%';
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
                // Don't auto-stop on a single network blip, but log it
            }
        }, 2000);
    }

    async function loadRecentScans() {
        const container = document.getElementById('recentScansContainer');
        if (!container) return;
        
        try {
            const response = await fetch('http://127.0.0.1:8000/invoices', {
                headers: getAuthHeaders()
            });
            if (!response.ok) throw new Error('Fetch failed');
            const invoices = await response.json();
            
            container.innerHTML = '';
            
            // Render top 3 recent
            const recent = invoices.slice(0, 3);
            
            if (recent.length === 0) {
                container.innerHTML = '<div style="color: var(--muted); font-size: 0.85rem; text-align: center; padding: 1rem;">NO RECENT SCANS</div>';
                return;
            }

            recent.forEach(inv => {
                let st = 'SUCCESS';
                let pillClass = 'st-success';
                
                // Matches status simulation from history logic
                if (inv.id % 7 === 0) { st = 'FAILED'; pillClass = 'st-failed'; }
                else if (inv.id % 5 === 0) { st = 'PROCESSING'; pillClass = 'st-processing'; }

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

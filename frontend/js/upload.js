document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const scanBtn = document.getElementById('scanBtn');
    const previewContainer = document.getElementById('previewContainer');
    const fileNameDisplay = document.getElementById('fileName');
    const fileSizeDisplay = document.getElementById('fileSize');
    const overlay = document.getElementById('overlay');
    const processStatus = document.getElementById('processStatus');

    let selectedFiles = [];

    // Trigger file input
    dropZone.addEventListener('click', () => fileInput.click());

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
            handleFilesSelection(files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            handleFilesSelection(files);
        }
    });

    function handleFilesSelection(files) {
        const allowedTypes = [
            'image/jpeg', 'image/png', 'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        
        const validFiles = files.filter(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            return allowedTypes.includes(file.type) || ['pdf', 'doc', 'docx'].includes(ext);
        });

        if (validFiles.length === 0) {
            alert('PLEASE SELECT VALID FILES (JPG, PNG, PDF, or WORD)');
            return;
        }
        
        selectedFiles = validFiles;
        
        if (selectedFiles.length === 1) {
            fileNameDisplay.textContent = selectedFiles[0].name.toUpperCase();
            fileSizeDisplay.textContent = `${(selectedFiles[0].size / 1024).toFixed(2)} KB`;
        } else {
            fileNameDisplay.textContent = `${selectedFiles.length} FILES SELECTED`;
            const totalSize = selectedFiles.reduce((acc, f) => acc + f.size, 0);
            fileSizeDisplay.textContent = `TOTAL: ${(totalSize / 1024).toFixed(2)} KB`;
        }

        previewContainer.style.display = 'block';
        scanBtn.disabled = false;
        dropZone.style.borderColor = 'var(--data-accent)';
    }

    scanBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        overlay.style.display = 'flex';
        const allResults = [];

        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            const batchLabel = selectedFiles.length > 1 ? `[FILE ${i + 1}/${selectedFiles.length}] ` : '';
            
            // Set overlay title to show batch progress
            const overlayTitle = overlay.querySelector('h2');
            overlayTitle.textContent = selectedFiles.length > 1 ? `BATCH SCANNING: ${i + 1}/${selectedFiles.length}` : 'SYSTEM SCANNING...';

            await runSteps(batchLabel);
            
            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('http://127.0.0.1:8000/scan', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error(`SCAN FAILED FOR ${file.name}`);

                const data = await response.json();
                allResults.push(data);
            } catch (error) {
                console.error(error);
                alert(`CRITICAL ERROR DURING BATCH SCAN: ${error.message}`);
            }
        }

        if (allResults.length > 0) {
            // Store results and redirect
            // If batch, store all. If single, store the object.
            sessionStorage.setItem('lastScanResults', JSON.stringify(allResults.length === 1 ? allResults[0] : allResults));
            window.location.href = 'results.html';
        } else {
            overlay.style.display = 'none';
        }
    });

    async function runSteps(prefix = '') {
        const steps = [
            'UPLOADING DOCUMENT TO SECURE NODE...',
            'AI OCR ENGINE: EXTRACTING LINE ITEMS...',
            'VALIDATING GSTIN AND MATHEMATICAL PRECISION...',
            'COMMITTING DATA TO LOCAL REPOSITORY...'
        ];

        // Reset step indicators
        for (let i = 1; i <= 4; i++) {
            const el = document.getElementById(`step${i}`);
            el.classList.remove('active', 'completed');
        }

        for (let i = 0; i < steps.length; i++) {
            const stepEl = document.getElementById(`step${i + 1}`);
            stepEl.classList.add('active');
            processStatus.textContent = `${prefix}${steps[i]}`;
            
            await new Promise(r => setTimeout(r, 600)); // Faster simulation for batches
            
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
        }
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const scanBtn = document.getElementById('scanBtn');
    const previewContainer = document.getElementById('previewContainer');
    const fileNameDisplay = document.getElementById('fileName');
    const fileSizeDisplay = document.getElementById('fileSize');
    const overlay = document.getElementById('overlay');
    const processStatus = document.getElementById('processStatus');

    let selectedFile = null;

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
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    function handleFileSelection(file) {
        if (!file.type.match('image.*')) {
            alert('PLEASE SELECT AN IMAGE FILE (JPG/PNG)');
            return;
        }
        
        selectedFile = file;
        fileNameDisplay.textContent = file.name.toUpperCase();
        fileSizeDisplay.textContent = `${(file.size / 1024).toFixed(2)} KB`;
        previewContainer.style.display = 'block';
        scanBtn.disabled = false;
        
        // Visual feedback
        dropZone.style.borderColor = 'var(--data-accent)';
    }

    scanBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        overlay.style.display = 'flex';
        await runSteps();
        
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await fetch('http://127.0.0.1:8000/scan', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('SCAN FAILED');

            const data = await response.json();
            
            // Store results and redirect
            sessionStorage.setItem('lastScanResults', JSON.stringify(data));
            window.location.href = 'results.html';
        } catch (error) {
            console.error(error);
            alert('CRITICAL ERROR DURING SCAN: ' + error.message);
            overlay.style.display = 'none';
        }
    });

    async function runSteps() {
        const steps = [
            { id: 'step1', text: 'UPLOADING DOCUMENT TO SECURE NODE...' },
            { id: 'step2', text: 'AI OCR ENGINE: EXTRACTING LINE ITEMS...' },
            { id: 'step3', text: 'VALIDATING GSTIN AND MATHEMATICAL PRECISION...' },
            { id: 'step4', text: 'COMMITTING DATA TO LOCAL REPOSITORY...' }
        ];

        for (let i = 0; i < steps.length; i++) {
            const stepEl = document.getElementById(steps[i].id);
            stepEl.classList.add('active');
            processStatus.textContent = steps[i].text;
            
            await new Promise(r => setTimeout(r, 800)); // Simulate processing time
            
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
        }
    }
});

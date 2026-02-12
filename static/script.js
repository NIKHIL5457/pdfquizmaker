// Simple JavaScript for interactions
document.addEventListener('DOMContentLoaded', function() {
    
    // File upload drag & drop
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('file');
    
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#667eea';
            uploadArea.style.background = '#f8f9ff';
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#e0e0e0';
            uploadArea.style.background = 'white';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#e0e0e0';
            uploadArea.style.background = 'white';
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileName(e.dataTransfer.files[0].name);
            }
        });
        
        fileInput.addEventListener('change', function() {
            if (this.files.length) {
                updateFileName(this.files[0].name);
            }
        });
        
        function updateFileName(name) {
            let fileNameDisplay = document.querySelector('.file-name');
            if (!fileNameDisplay) {
                fileNameDisplay = document.createElement('p');
                fileNameDisplay.className = 'file-name mt-2';
                fileNameDisplay.style.color = '#667eea';
                uploadArea.appendChild(fileNameDisplay);
            }
            fileNameDisplay.textContent = `✓ Selected: ${name}`;
        }
    }
    
    // Quiz progress bar
    const questions = document.querySelectorAll('.question');
    const progressBar = document.querySelector('.progress-bar');
    
    if (questions.length && progressBar) {
        function updateProgress() {
            const answered = document.querySelectorAll('input[type="radio"]:checked, input[type="text"]:not([value=""])').length;
            const percentage = (answered / questions.length) * 100;
            progressBar.style.width = `${percentage}%`;
        }
        
        // Listen for answer changes
        document.querySelectorAll('input[type="radio"], input[type="text"]').forEach(input => {
            input.addEventListener('change', updateProgress);
            if (input.type === 'text') {
                input.addEventListener('keyup', updateProgress);
            }
        });
        
        // Initial update
        updateProgress();
    }
    
    // Confirm before reset
    const resetBtn = document.querySelector('.reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to start over?')) {
                e.preventDefault();
            }
        });
    }
    
    // Form validation
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('Please select a PDF file first');
            }
        });
    }
});
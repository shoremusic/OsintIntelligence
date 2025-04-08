/**
 * OSINT Application Main JavaScript
 * Handles form submissions, API configurations, and general UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize API configuration form
    initApiConfigForm();
    
    // Initialize OSINT input form
    initOsintForm();
    
    // Initialize URL scraper
    initUrlScraper();
});

/**
 * Initialize the API configuration form
 */
function initApiConfigForm() {
    const apiConfigForm = document.getElementById('api-config-form');
    if (!apiConfigForm) return;
    
    // Handle RapidAPI key saving
    const saveRapidApiKeyBtn = document.getElementById('save-rapidapi-key');
    if (saveRapidApiKeyBtn) {
        saveRapidApiKeyBtn.addEventListener('click', function() {
            const rapidApiKey = document.getElementById('rapidapi_key').value.trim();
            if (!rapidApiKey) {
                alert('Please enter a RapidAPI key.');
                return;
            }
            
            // Send a request to save the key as an environment variable
            fetch('/save_api_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    key_name: 'RAPIDAPI_KEY',
                    key_value: rapidApiKey
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('RapidAPI key saved successfully!');
                    document.getElementById('rapidapi_key').value = '';
                } else {
                    alert(`Error saving RapidAPI key: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error saving RapidAPI key:', error);
                alert(`Error: ${error.message}`);
            });
        });
    }
    
    apiConfigForm.addEventListener('submit', function(event) {
        // Form validation is handled by Bootstrap
        if (!apiConfigForm.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        apiConfigForm.classList.add('was-validated');
    });
    
    // Initialize API update and delete buttons
    document.querySelectorAll('.btn-update-api').forEach(button => {
        button.addEventListener('click', function() {
            const apiId = this.getAttribute('data-api-id');
            updateApiConfig(apiId);
        });
    });
    
    document.querySelectorAll('.btn-delete-api').forEach(button => {
        button.addEventListener('click', function() {
            const apiId = this.getAttribute('data-api-id');
            deleteApiConfig(apiId);
        });
    });
    
    // Initialize endpoint editor
    const endpointsInput = document.getElementById('endpoints');
    const formatInput = document.getElementById('format');
    
    if (endpointsInput) {
        // Add helper for JSON input
        endpointsInput.addEventListener('blur', function() {
            try {
                if (this.value) {
                    const parsed = JSON.parse(this.value);
                    this.value = JSON.stringify(parsed, null, 2);
                    this.classList.remove('is-invalid');
                }
            } catch (e) {
                this.classList.add('is-invalid');
            }
        });
    }
    
    if (formatInput) {
        // Add helper for JSON input
        formatInput.addEventListener('blur', function() {
            try {
                if (this.value) {
                    const parsed = JSON.parse(this.value);
                    this.value = JSON.stringify(parsed, null, 2);
                    this.classList.remove('is-invalid');
                }
            } catch (e) {
                this.classList.add('is-invalid');
            }
        });
    }
}

/**
 * Update an API configuration
 * @param {string} apiId - The ID of the API to update
 */
function updateApiConfig(apiId) {
    // Get API details from the form
    const apiName = document.getElementById(`api-name-${apiId}`).textContent;
    const apiUrl = document.getElementById(`api-url-${apiId}`).textContent;
    const apiKeyEnv = document.getElementById(`api-key-env-${apiId}`).textContent;
    const description = document.getElementById(`api-description-${apiId}`).textContent;
    const endpoints = document.getElementById(`api-endpoints-${apiId}`).textContent;
    const format = document.getElementById(`api-format-${apiId}`).textContent;
    
    // Create modal with form for updating
    const modalHtml = `
    <div class="modal fade" id="updateApiModal" tabindex="-1" aria-labelledby="updateApiModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="updateApiModalLabel">Update API Configuration</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="update-api-form" class="needs-validation" novalidate>
                        <div class="mb-3">
                            <label for="update-api-name" class="form-label">API Name</label>
                            <input type="text" class="form-control" id="update-api-name" value="${apiName}" required>
                            <div class="invalid-feedback">Please provide an API name.</div>
                        </div>
                        <div class="mb-3">
                            <label for="update-api-url" class="form-label">API URL</label>
                            <input type="url" class="form-control" id="update-api-url" value="${apiUrl}" required>
                            <div class="invalid-feedback">Please provide a valid URL.</div>
                        </div>
                        <div class="mb-3">
                            <label for="update-api-key-env" class="form-label">API Key Environment Variable</label>
                            <input type="text" class="form-control" id="update-api-key-env" value="${apiKeyEnv}">
                            <div class="form-text">Name of the environment variable that contains the API key.</div>
                        </div>
                        <div class="mb-3">
                            <label for="update-description" class="form-label">Description</label>
                            <textarea class="form-control" id="update-description" rows="2">${description}</textarea>
                        </div>
                        <div class="mb-3">
                            <label for="update-endpoints" class="form-label">Endpoints (JSON)</label>
                            <textarea class="form-control" id="update-endpoints" rows="5">${endpoints}</textarea>
                            <div class="form-text">
                                JSON object defining the API endpoints.
                                Example: {"users": {"path": "/api/users", "method": "GET", "auth_type": "header"}}
                            </div>
                            <div class="invalid-feedback">Please provide valid JSON for endpoints.</div>
                        </div>
                        <div class="mb-3">
                            <label for="update-format" class="form-label">Format (JSON)</label>
                            <textarea class="form-control" id="update-format" rows="3">${format}</textarea>
                            <div class="form-text">JSON object defining the API response format.</div>
                            <div class="invalid-feedback">Please provide valid JSON for format.</div>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="save-api-update">Save Changes</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // Add modal to the page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Initialize the modal
    const modal = new bootstrap.Modal(document.getElementById('updateApiModal'));
    modal.show();
    
    // Add event listener for saving changes
    document.getElementById('save-api-update').addEventListener('click', function() {
        const form = document.getElementById('update-api-form');
        
        // Validate endpoints and format JSON
        let endpointsValid = true;
        let formatValid = true;
        
        try {
            const endpointsValue = document.getElementById('update-endpoints').value;
            if (endpointsValue) {
                JSON.parse(endpointsValue);
            }
        } catch (e) {
            endpointsValid = false;
            document.getElementById('update-endpoints').classList.add('is-invalid');
        }
        
        try {
            const formatValue = document.getElementById('update-format').value;
            if (formatValue) {
                JSON.parse(formatValue);
            }
        } catch (e) {
            formatValid = false;
            document.getElementById('update-format').classList.add('is-invalid');
        }
        
        // Form validation
        if (!form.checkValidity() || !endpointsValid || !formatValid) {
            event.preventDefault();
            event.stopPropagation();
            form.classList.add('was-validated');
            return;
        }
        
        // Get updated values
        const updatedApi = {
            api_name: document.getElementById('update-api-name').value,
            api_url: document.getElementById('update-api-url').value,
            api_key_env: document.getElementById('update-api-key-env').value,
            description: document.getElementById('update-description').value,
            endpoints: document.getElementById('update-endpoints').value,
            format: document.getElementById('update-format').value
        };
        
        // Send update request
        fetch(`/api_config/${apiId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedApi)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Close modal and reload page
                modal.hide();
                document.getElementById('updateApiModal').remove();
                window.location.reload();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error updating API:', error);
            alert(`Error: ${error.message}`);
        });
    });
    
    // Clean up when modal is closed
    document.getElementById('updateApiModal').addEventListener('hidden.bs.modal', function() {
        document.getElementById('updateApiModal').remove();
    });
}

/**
 * Delete an API configuration
 * @param {string} apiId - The ID of the API to delete
 */
function deleteApiConfig(apiId) {
    if (confirm('Are you sure you want to delete this API configuration?')) {
        fetch(`/api_config/${apiId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.reload();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error deleting API:', error);
            alert(`Error: ${error.message}`);
        });
    }
}

/**
 * Initialize the OSINT input form
 */
function initOsintForm() {
    const osintForm = document.getElementById('osint-form');
    if (!osintForm) return;
    
    // Handle primary image input change
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('image-preview');
    
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.classList.remove('d-none');
                    document.getElementById('image-preview-container').classList.remove('d-none');
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.src = '';
                imagePreview.classList.add('d-none');
                document.getElementById('image-preview-container').classList.add('d-none');
            }
        });
    }
    
    // Secondary image handling has been removed as per requirements
    
    // Form validation - ensure at least one field is filled
    osintForm.addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent form submission initially
        
        // Check if at least one field has a value
        const name = document.getElementById('name').value.trim();
        const phone = document.getElementById('phone').value.trim();
        const email = document.getElementById('email').value.trim();
        const socialMedia = document.getElementById('social_media').value.trim();
        const location = document.getElementById('location').value.trim();
        const vehicle = document.getElementById('vehicle').value.trim();
        const additionalInfo = document.getElementById('additional_info').value.trim();
        const hasImage = imageInput && imageInput.files && imageInput.files.length > 0;
        
        const hasAtLeastOneField = name || phone || email || socialMedia || location || 
                                  vehicle || additionalInfo || hasImage;
        
        if (!hasAtLeastOneField) {
            // Show error message
            if (!document.getElementById('validation-error')) {
                const errorDiv = document.createElement('div');
                errorDiv.id = 'validation-error';
                errorDiv.className = 'alert alert-danger mt-3';
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Please fill in at least one field to begin the OSINT investigation.';
                osintForm.insertBefore(errorDiv, document.getElementById('submit-osint').parentNode);
            }
        } else {
            // Remove error message if it exists
            const errorDiv = document.getElementById('validation-error');
            if (errorDiv) {
                errorDiv.remove();
            }
            
            // Show loading animation
            document.getElementById('osint-loading').classList.remove('d-none');
            document.getElementById('submit-osint').disabled = true;
            
            // Simulate progress
            let progress = 0;
            const progressBar = document.getElementById('osint-progress');
            const progressInterval = setInterval(() => {
                progress += 3;
                if (progress >= 90) {
                    clearInterval(progressInterval);
                }
                progressBar.style.width = progress + '%';
                progressBar.setAttribute('aria-valuenow', progress);
            }, 300);
            
            // Continue with form submission
            osintForm.submit();
        }
    });
}

/**
 * Initialize the URL scraper functionality
 */
function initUrlScraper() {
    const scrapeUrlForm = document.getElementById('scrape-url-form');
    if (!scrapeUrlForm) return;
    
    scrapeUrlForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const urlInput = document.getElementById('scrape-url');
        const url = urlInput.value.trim();
        
        if (!url) {
            urlInput.classList.add('is-invalid');
            return;
        }
        
        // Show loading indicator with network animation
        document.getElementById('scrape-loading').classList.remove('d-none');
        document.getElementById('scrape-results').classList.add('d-none');
        
        // Disable the form while loading
        urlInput.disabled = true;
        scrapeUrlForm.querySelector('button[type="submit"]').disabled = true;
        
        // Send request to scrape URL
        fetch('/scrape_url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator and re-enable form
            document.getElementById('scrape-loading').classList.add('d-none');
            urlInput.disabled = false;
            scrapeUrlForm.querySelector('button[type="submit"]').disabled = false;
            
            if (data.status === 'success') {
                // Display results
                document.getElementById('scrape-results').classList.remove('d-none');
                document.getElementById('scraped-content').value = data.content;
                
                // Add to additional info if the button is clicked
                document.getElementById('add-to-info').addEventListener('click', function() {
                    const additionalInfo = document.getElementById('additional_info');
                    if (additionalInfo) {
                        additionalInfo.value += '\n\n--- Scraped from ' + url + ' ---\n' + data.content;
                    }
                });
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            document.getElementById('scrape-loading').classList.add('d-none');
            urlInput.disabled = false;
            scrapeUrlForm.querySelector('button[type="submit"]').disabled = false;
            console.error('Error scraping URL:', error);
            alert(`Error: ${error.message}`);
        });
    });
}

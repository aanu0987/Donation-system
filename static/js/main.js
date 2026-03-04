// Main JavaScript file for Blood & Organ Donation System

// Notification system
class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.checkInterval = 30000; // Check every 30 seconds
        this.init();
    }

    init() {
        this.loadNotifications();
        setInterval(() => this.loadNotifications(), this.checkInterval);
    }

    loadNotifications() {
        fetch('/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    this.notifications = data;
                    this.displayNotifications();
                }
            })
            .catch(error => console.error('Error loading notifications:', error));
    }

    displayNotifications() {
        const container = document.getElementById('notificationsList');
        if (!container) return;

        if (this.notifications.length > 0) {
            let html = '';
            this.notifications.forEach(n => {
                html += `
                    <div class="alert alert-info" onclick="markAsRead('${n.id}')">
                        ${n.message}
                        <small>${n.created_at}</small>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    }
}

// Search functionality
class DonorSearch {
    constructor() {
        this.searchForm = document.getElementById('searchForm');
        if (this.searchForm) {
            this.searchForm.addEventListener('submit', (e) => this.handleSearch(e));
        }
    }

    handleSearch(e) {
        e.preventDefault();
        
        const formData = new FormData(this.searchForm);
        const searchData = {
            blood_group: formData.get('blood_group'),
            organ_type: formData.get('organ_type'),
            city: formData.get('city')
        };

        fetch('/search-donors', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchData)
        })
        .then(response => response.json())
        .then(results => this.displayResults(results))
        .catch(error => console.error('Error searching donors:', error));
    }

    displayResults(results) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;

        if (results.length === 0) {
            resultsContainer.innerHTML = '<p class="alert alert-info">No donors found matching your criteria</p>';
            return;
        }

        let html = '';
        results.forEach(donor => {
            html += `
                <div class="card" style="margin-bottom: 1rem;">
                    <div class="card-body">
                        <h4>${donor.name}</h4>
                        <p>City: ${donor.city}</p>
                        <p>${donor.blood_group ? 'Blood Group: ' + donor.blood_group : 'Organ: ' + donor.organ}</p>
                        <button class="btn btn-primary btn-sm" onclick="requestDonation('${donor.id}', '${donor.type}')">
                            Request Donation
                        </button>
                    </div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
    }
}

// Donation request
function requestDonation(donorId, type) {
    const data = {
        donor_id: donorId,
        type: type
    };

    fetch('/request-donation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Donation request sent successfully!', 'success');
        } else {
            showAlert('Error sending request. Please try again.', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred. Please try again.', 'danger');
    });
}

// Alert system
function showAlert(message, type) {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type}`;
    alertContainer.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertContainer, container.firstChild);
    
    setTimeout(() => {
        alertContainer.remove();
    }, 5000);
}

// Modal handling
class Modal {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.closeBtn = this.modal?.querySelector('.close');
        this.init();
    }

    init() {
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.hide());
        }
        
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    show() {
        this.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    hide() {
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Form validation
class FormValidator {
    constructor(formId) {
        this.form = document.getElementById(formId);
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.validate(e));
        }
    }

    validate(e) {
        const inputs = this.form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showError(input, 'This field is required');
                isValid = false;
            } else {
                this.clearError(input);
            }

            // Email validation
            if (input.type === 'email' && input.value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(input.value)) {
                    this.showError(input, 'Please enter a valid email address');
                    isValid = false;
                }
            }

            // Password validation
            if (input.type === 'password' && input.value && input.value.length < 6) {
                this.showError(input, 'Password must be at least 6 characters');
                isValid = false;
            }
        });

        if (!isValid) {
            e.preventDefault();
        }
    }

    showError(input, message) {
        const formGroup = input.closest('.form-group');
        let errorDiv = formGroup.querySelector('.error-message');
        
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.color = 'var(--danger-color)';
            errorDiv.style.fontSize = '0.875rem';
            errorDiv.style.marginTop = '0.25rem';
            formGroup.appendChild(errorDiv);
        }
        
        errorDiv.textContent = message;
        input.style.borderColor = 'var(--danger-color)';
    }

    clearError(input) {
        const formGroup = input.closest('.form-group');
        const errorDiv = formGroup.querySelector('.error-message');
        
        if (errorDiv) {
            errorDiv.remove();
        }
        
        input.style.borderColor = '#ddd';
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in by checking for logout link
    const logoutLink = document.querySelector('.nav-links a[href="/logout"]');
    if (logoutLink) {
        new NotificationSystem();
    }
    
    // Initialize search
    new DonorSearch();
    
    // Initialize form validators
    new FormValidator('registrationForm');
    new FormValidator('loginForm');
    
    // Initialize modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        new Modal(modal.id);
    });

    // Blood group calculator
    const bloodGroupSelect = document.getElementById('bloodGroup');
    if (bloodGroupSelect) {
        bloodGroupSelect.addEventListener('change', function() {
            showCompatibleBloodGroups(this.value);
        });
    }
});

// Blood group compatibility
function showCompatibleBloodGroups(bloodGroup) {
    const compatibility = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    };

    const compatible = compatibility[bloodGroup] || [];
    const container = document.getElementById('compatibleGroups');
    
    if (container && compatible.length > 0) {
        let html = '<p>Compatible blood groups for donation:</p><div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">';
        compatible.forEach(group => {
            html += `<span class="badge badge-success">${group}</span>`;
        });
        html += '</div>';
        container.innerHTML = html;
    }
}

// Export functionality
function exportReport(format) {
    const data = {
        format: format,
        type: document.getElementById('reportType')?.value || 'donations'
    };

    fetch('/export-report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(error => console.error('Error exporting report:', error));
}

// Emergency alert toggle
function toggleEmergencyAlert() {
    const banner = document.getElementById('emergencyBanner');
    if (banner) {
        banner.style.display = banner.style.display === 'none' ? 'block' : 'none';
    }
}

// Check eligibility for blood donation
function checkEligibility(lastDonationDate) {
    if (!lastDonationDate) return true;
    
    const lastDonation = new Date(lastDonationDate);
    const today = new Date();
    const daysDiff = Math.floor((today - lastDonation) / (1000 * 60 * 60 * 24));
    
    return daysDiff >= 90; // 90 days gap required
}

// Update last donation date
function updateLastDonation() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('lastDonationDate').value = today;
    
    // Check eligibility
    if (!checkEligibility(today)) {
        showAlert('You need to wait 90 days before your next donation.', 'warning');
    }
}
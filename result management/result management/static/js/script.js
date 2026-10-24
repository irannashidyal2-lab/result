// ==================== DOCUMENT READY ====================
$(document).ready(function() {
    // Initialize all animations and interactions
    initAnimations();
    initFormValidation();
    initTableInteractions();
    initScrollEffects();
    initNavbarEffects();
});

// ==================== ANIMATIONS ====================
function initAnimations() {
    // Fade in elements on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe all animated elements
    $('.animated-card, .feature-card, .stat-card, .quick-action-card').each(function() {
        $(this).css({
            'opacity': '0',
            'transform': 'translateY(20px)',
            'transition': 'all 0.6s ease'
        });
        observer.observe(this);
    });
}

// ==================== FORM VALIDATION ====================
function initFormValidation() {
    $('form').on('submit', function(e) {
        let isValid = true;
        const form = this;

        // Check required fields
        $(form).find('input[required], select[required]').each(function() {
            if (!$(this).val()) {
                isValid = false;
                $(this).addClass('is-invalid');
                
                // Shake animation
                $(this).css('animation', 'shake 0.5s');
                setTimeout(() => {
                    $(this).css('animation', '');
                }, 500);
            } else {
                $(this).removeClass('is-invalid');
            }
        });

        // Validate email format
        $(form).find('input[type="email"]').each(function() {
            const email = $(this).val();
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (email && !emailRegex.test(email)) {
                isValid = false;
                $(this).addClass('is-invalid');
            }
        });

        // Validate numeric fields
        $(form).find('input[type="number"]').each(function() {
            const min = parseFloat($(this).attr('min'));
            const max = parseFloat($(this).attr('max'));
            const value = parseFloat($(this).val());

            if (min !== undefined && value < min) {
                isValid = false;
                $(this).addClass('is-invalid');
            }
            if (max !== undefined && value > max) {
                isValid = false;
                $(this).addClass('is-invalid');
            }
        });

        if (!isValid) {
            e.preventDefault();
            showAlert('Please fix the errors in the form', 'error');
        }
    });

    // Clear validation on input
    $('input, select').on('input', function() {
        $(this).removeClass('is-invalid');
    });
}

// ==================== TABLE INTERACTIONS ====================
function initTableInteractions() {
    // Add hover effects to table rows
    $('table tbody tr').on('mouseenter', function() {
        $(this).css('cursor', 'pointer');
    });

    // Add click to select functionality
    $('table tbody tr').on('click', function() {
        $(this).toggleClass('table-active');
    });

    // Add sorting indicator
    $('table thead th').on('click', function() {
        const icon = $(this).find('i');
        if (icon.length) {
            icon.toggleClass('fa-sort-up fa-sort-down');
        }
    });
}

// ==================== SCROLL EFFECTS ====================
function initScrollEffects() {
    // Navbar background on scroll
    $(window).on('scroll', function() {
        const scrollTop = $(this).scrollTop();
        if (scrollTop > 50) {
            $('.navbar').addClass('navbar-scrolled');
        } else {
            $('.navbar').removeClass('navbar-scrolled');
        }
    });

    // Smooth scroll for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 500);
        }
    });

    // Back to top button
    const backToTop = $('<button>', {
        class: 'btn btn-primary back-to-top',
        html: '<i class="fas fa-arrow-up"></i>',
        css: {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            display: 'none',
            zIndex: '1000',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            padding: '0'
        }
    });

    $('body').append(backToTop);

    $(window).on('scroll', function() {
        if ($(this).scrollTop() > 300) {
            backToTop.fadeIn();
        } else {
            backToTop.fadeOut();
        }
    });

    backToTop.on('click', function() {
        $('html, body').animate({ scrollTop: 0 }, 500);
    });
}

// ==================== NAVBAR EFFECTS ====================
function initNavbarEffects() {
    // Mobile menu toggle animation
    $('.navbar-toggler').on('click', function() {
        $(this).toggleClass('active');
    });

    // Dropdown animation
    $('.dropdown').on('show.bs.dropdown', function() {
        $(this).find('.dropdown-menu').first().stop(true, true).slideDown(300);
    });

    $('.dropdown').on('hide.bs.dropdown', function() {
        $(this).find('.dropdown-menu').first().stop(true, true).slideUp(300);
    });
}

// ==================== ALERT SYSTEM ====================
function showAlert(message, type = 'info') {
    const alertClass = type === 'error' ? 'danger' : type;
    const icon = type === 'success' ? 'fa-check-circle' : 
                 type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';

    const alert = $(`
        <div class="alert alert-${alertClass} alert-dismissible fade show animated-alert" role="alert">
            <i class="fas ${icon} me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);

    $('.container').first().prepend(alert);

    setTimeout(() => {
        alert.alert('close');
    }, 5000);
}

// ==================== LOADING INDICATOR ====================
function showLoading(element) {
    const originalText = element.text();
    element.data('original-text', originalText);
    element.html('<span class="loading me-2"></span> Loading...');
    element.prop('disabled', true);
}

function hideLoading(element) {
    const originalText = element.data('original-text');
    element.text(originalText);
    element.prop('disabled', false);
}

// ==================== CONFIRMATION DIALOG ====================
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ==================== SEARCH FUNCTIONALITY ====================
function initSearch(searchInput, tableId) {
    $(searchInput).on('keyup', function() {
        const value = $(this).val().toLowerCase();
        $(tableId + ' tbody tr').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
    });
}

// ==================== EXPORT FUNCTIONALITY ====================
function exportTableToCSV(tableId, filename) {
    const csv = [];
    const rows = $(tableId + ' tr');

    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            row.push(cols[j].innerText);
        }
        
        csv.push(row.join(','));
    }

    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// ==================== PRINT FUNCTIONALITY ====================
function printElement(elementId) {
    const element = document.getElementById(elementId);
    const originalContents = document.body.innerHTML;

    document.body.innerHTML = element.innerHTML;
    window.print();
    document.body.innerHTML = originalContents;

    // Reinitialize scripts
    location.reload();
}

// ==================== CHART INITIALIZATION ====================
function initChart(canvasId, chartType, data, options) {
    // This function can be used with Chart.js if needed
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: chartType,
        data: data,
        options: options
    });
}

// ==================== REAL-TIME VALIDATION ====================
function validateField(field, validationRules) {
    const value = field.val();
    let isValid = true;
    let errorMessage = '';

    for (const rule of validationRules) {
        if (rule.required && !value) {
            isValid = false;
            errorMessage = 'This field is required';
            break;
        }

        if (rule.minLength && value.length < rule.minLength) {
            isValid = false;
            errorMessage = `Minimum length is ${rule.minLength} characters`;
            break;
        }

        if (rule.maxLength && value.length > rule.maxLength) {
            isValid = false;
            errorMessage = `Maximum length is ${rule.maxLength} characters`;
            break;
        }

        if (rule.pattern && !rule.pattern.test(value)) {
            isValid = false;
            errorMessage = rule.message || 'Invalid format';
            break;
        }
    }

    if (!isValid) {
        field.addClass('is-invalid');
        field.next('.invalid-feedback').text(errorMessage).show();
    } else {
        field.removeClass('is-invalid');
        field.next('.invalid-feedback').hide();
    }

    return isValid;
}

// ==================== KEYBOARD SHORTCUTS ====================
function initKeyboardShortcuts() {
    $(document).on('keydown', function(e) {
        // Ctrl/Cmd + S to save (prevent default)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            // Trigger save if on a form
            $('form').submit();
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            $('.modal').modal('hide');
        }
    });
}

// ==================== TOOLTIP INITIALIZATION ====================
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ==================== PROGRESS BAR ANIMATION ====================
function animateProgressBar(progressBar, targetValue) {
    progressBar.width('0%');
    progressBar.animate({
        width: targetValue + '%'
    }, {
        duration: 1000,
        easing: 'swing'
    });
}

// ==================== COUNTER ANIMATION ====================
function animateCounter(element, targetValue, duration = 2000) {
    $({ count: 0 }).animate({
        count: targetValue
    }, {
        duration: duration,
        easing: 'swing',
        step: function() {
            element.text(Math.floor(this.count));
        },
        complete: function() {
            element.text(targetValue);
        }
    });
}

// ==================== LAZY LOADING IMAGES ====================
function initLazyLoading() {
    const images = $('img[data-src]');
    
    images.each(function() {
        const $img = $(this);
        const src = $img.data('src');
        
        $img.on('load', function() {
            $img.removeClass('lazy-loading');
        });
        
        $img.attr('src', src).addClass('lazy-loading');
    });
}

// ==================== DARK MODE TOGGLE ====================
function toggleDarkMode() {
    $('body').toggleClass('dark-mode');
    localStorage.setItem('darkMode', $('body').hasClass('dark-mode'));
}

function initDarkMode() {
    if (localStorage.getItem('darkMode') === 'true') {
        $('body').addClass('dark-mode');
    }
}

// ==================== NOTIFICATION SYSTEM ====================
function showNotification(title, message, type = 'info') {
    if (!('Notification' in window)) {
        console.log('This browser does not support desktop notification');
        return;
    }

    if (Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/images/icon.png'
        });
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(function(permission) {
            if (permission === 'granted') {
                new Notification(title, {
                    body: message,
                    icon: '/static/images/icon.png'
                });
            }
        });
    }
}

// ==================== UTILITY FUNCTIONS ====================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==================== INITIALIZATION ====================
// Initialize additional features
$(document).ready(function() {
    initKeyboardShortcuts();
    initTooltips();
    initDarkMode();
    initLazyLoading();
});

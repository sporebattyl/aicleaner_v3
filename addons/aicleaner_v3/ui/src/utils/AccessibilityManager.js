/**
 * Accessibility Manager
 * Comprehensive accessibility utilities and enhancements for WCAG compliance
 */

class AccessibilityManager {
    constructor() {
        this.focusTrap = null;
        this.announcementQueue = [];
        this.keyboardListeners = new Map();
        this.lastFocusedElement = null;
        this.setupAccessibilityFeatures();
    }

    setupAccessibilityFeatures() {
        // Setup high contrast mode detection
        this.setupHighContrastMode();
        
        // Setup reduced motion detection
        this.setupReducedMotion();
        
        // Setup focus management
        this.setupFocusManagement();
        
        // Setup keyboard navigation
        this.setupGlobalKeyboardHandlers();
        
        // Setup screen reader announcements
        this.setupScreenReaderAnnouncements();
    }

    /**
     * High Contrast Mode Support
     */
    setupHighContrastMode() {
        const mediaQuery = window.matchMedia('(prefers-contrast: high)');
        this.applyHighContrastMode(mediaQuery.matches);
        
        mediaQuery.addEventListener('change', (e) => {
            this.applyHighContrastMode(e.matches);
        });

        // Manual high contrast toggle
        const savedContrast = localStorage.getItem('aicleaner_high_contrast');
        if (savedContrast) {
            this.applyHighContrastMode(savedContrast === 'true');
        }
    }

    applyHighContrastMode(enabled) {
        document.body.classList.toggle('high-contrast', enabled);
        document.documentElement.style.setProperty('--accessibility-mode', enabled ? 'high-contrast' : 'normal');
        
        if (enabled) {
            document.documentElement.style.setProperty('--text-color', '#000000');
            document.documentElement.style.setProperty('--background-color', '#ffffff');
            document.documentElement.style.setProperty('--link-color', '#0000ff');
            document.documentElement.style.setProperty('--button-color', '#000000');
            document.documentElement.style.setProperty('--border-color', '#000000');
        } else {
            document.documentElement.style.removeProperty('--text-color');
            document.documentElement.style.removeProperty('--background-color');
            document.documentElement.style.removeProperty('--link-color');
            document.documentElement.style.removeProperty('--button-color');
            document.documentElement.style.removeProperty('--border-color');
        }
    }

    toggleHighContrastMode() {
        const isEnabled = document.body.classList.contains('high-contrast');
        this.applyHighContrastMode(!isEnabled);
        localStorage.setItem('aicleaner_high_contrast', (!isEnabled).toString());
        this.announce(isEnabled ? 'High contrast disabled' : 'High contrast enabled');
    }

    /**
     * Reduced Motion Support
     */
    setupReducedMotion() {
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        this.applyReducedMotion(mediaQuery.matches);
        
        mediaQuery.addEventListener('change', (e) => {
            this.applyReducedMotion(e.matches);
        });
    }

    applyReducedMotion(enabled) {
        document.body.classList.toggle('reduced-motion', enabled);
        document.documentElement.style.setProperty('--animation-duration', enabled ? '0.01ms' : '0.3s');
        document.documentElement.style.setProperty('--transition-duration', enabled ? '0.01ms' : '0.15s');
    }

    /**
     * Focus Management
     */
    setupFocusManagement() {
        // Track focus for restoration
        document.addEventListener('focusout', (e) => {
            if (e.target && e.target !== document.body) {
                this.lastFocusedElement = e.target;
            }
        });

        // Enhanced focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    /**
     * Focus Trap for Modals
     */
    trapFocus(container) {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements.length === 0) return;

        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        const handleTabKey = (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstFocusable) {
                        lastFocusable.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastFocusable) {
                        firstFocusable.focus();
                        e.preventDefault();
                    }
                }
            }
        };

        container.addEventListener('keydown', handleTabKey);
        firstFocusable.focus();

        this.focusTrap = {
            container,
            handleTabKey,
            release: () => {
                container.removeEventListener('keydown', handleTabKey);
                this.focusTrap = null;
                if (this.lastFocusedElement) {
                    this.lastFocusedElement.focus();
                }
            }
        };

        return this.focusTrap;
    }

    releaseFocusTrap() {
        if (this.focusTrap) {
            this.focusTrap.release();
        }
    }

    /**
     * Keyboard Navigation
     */
    setupGlobalKeyboardHandlers() {
        document.addEventListener('keydown', (e) => {
            // Skip navigation (common accessibility feature)
            if (e.key === 'Tab' && e.ctrlKey) {
                this.handleSkipNavigation(e);
            }
            
            // Escape key handling
            if (e.key === 'Escape') {
                this.handleEscapeKey(e);
            }

            // Arrow key navigation for components
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                this.handleArrowNavigation(e);
            }
        });
    }

    handleSkipNavigation(e) {
        const skipLinks = document.querySelectorAll('.skip-link');
        if (skipLinks.length > 0) {
            e.preventDefault();
            skipLinks[0].focus();
        }
    }

    handleEscapeKey(e) {
        // Close modals
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const closeButton = openModal.querySelector('.btn-close, [data-bs-dismiss="modal"]');
            if (closeButton) {
                closeButton.click();
            }
        }

        // Release focus trap
        this.releaseFocusTrap();
    }

    handleArrowNavigation(e) {
        const activeElement = document.activeElement;
        
        // Handle navigation within groups (like tab panels, lists)
        if (activeElement.getAttribute('role') === 'tab') {
            this.handleTabNavigation(e, activeElement);
        } else if (activeElement.closest('[role="listbox"], [role="menu"]')) {
            this.handleMenuNavigation(e, activeElement);
        }
    }

    handleTabNavigation(e, activeTab) {
        const tabList = activeTab.closest('[role="tablist"]');
        if (!tabList) return;

        const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
        const currentIndex = tabs.indexOf(activeTab);

        let newIndex;
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
        }

        if (newIndex !== undefined) {
            e.preventDefault();
            tabs[newIndex].focus();
            tabs[newIndex].click();
        }
    }

    handleMenuNavigation(e, activeItem) {
        const menu = activeItem.closest('[role="listbox"], [role="menu"]');
        if (!menu) return;

        const items = Array.from(menu.querySelectorAll('[role="option"], [role="menuitem"]'));
        const currentIndex = items.indexOf(activeItem);

        let newIndex;
        if (e.key === 'ArrowUp') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        } else if (e.key === 'ArrowDown') {
            newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        }

        if (newIndex !== undefined) {
            e.preventDefault();
            items[newIndex].focus();
        }
    }

    /**
     * Screen Reader Announcements
     */
    setupScreenReaderAnnouncements() {
        // Create announcement container
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'accessibility-announcer';
        document.body.appendChild(announcer);

        this.announcer = announcer;
    }

    announce(message, priority = 'polite') {
        if (!message || !this.announcer) return;

        // Clear previous announcement
        this.announcer.textContent = '';
        this.announcer.setAttribute('aria-live', priority);

        // Queue announcement to ensure it's read
        setTimeout(() => {
            this.announcer.textContent = message;
        }, 100);

        // Clear after announcement
        setTimeout(() => {
            this.announcer.textContent = '';
        }, 1000);
    }

    announcePageChange(title) {
        this.announce(`Navigated to ${title} page`);
    }

    announceFormError(fieldName, error) {
        this.announce(`Error in ${fieldName}: ${error}`, 'assertive');
    }

    announceSuccess(message) {
        this.announce(`Success: ${message}`);
    }

    /**
     * ARIA Utilities
     */
    setAriaExpanded(element, expanded) {
        element.setAttribute('aria-expanded', expanded.toString());
    }

    setAriaSelected(element, selected) {
        element.setAttribute('aria-selected', selected.toString());
    }

    setAriaChecked(element, checked) {
        element.setAttribute('aria-checked', checked.toString());
    }

    setAriaHidden(element, hidden) {
        element.setAttribute('aria-hidden', hidden.toString());
    }

    /**
     * Form Accessibility
     */
    enhanceFormAccessibility(form) {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Associate labels
            const label = form.querySelector(`label[for="${input.id}"]`) || 
                         input.closest('.form-group')?.querySelector('label');
            
            if (label && !input.getAttribute('aria-labelledby')) {
                if (!label.id) {
                    label.id = `label-${input.id || Date.now()}`;
                }
                input.setAttribute('aria-labelledby', label.id);
            }

            // Add required indicators
            if (input.required && !input.getAttribute('aria-required')) {
                input.setAttribute('aria-required', 'true');
            }

            // Error associations
            const errorElement = form.querySelector(`[data-error-for="${input.id}"]`);
            if (errorElement) {
                if (!errorElement.id) {
                    errorElement.id = `error-${input.id}`;
                }
                input.setAttribute('aria-describedby', errorElement.id);
                input.setAttribute('aria-invalid', 'true');
            }
        });
    }

    /**
     * Component Enhancement
     */
    enhanceButton(button, label, description) {
        if (label) {
            button.setAttribute('aria-label', label);
        }
        if (description) {
            const descId = `desc-${Date.now()}`;
            const descElement = document.createElement('span');
            descElement.id = descId;
            descElement.className = 'sr-only';
            descElement.textContent = description;
            button.appendChild(descElement);
            button.setAttribute('aria-describedby', descId);
        }
    }

    enhanceTable(table) {
        // Add table caption if missing
        if (!table.querySelector('caption')) {
            const caption = document.createElement('caption');
            caption.className = 'sr-only';
            caption.textContent = 'Data table';
            table.insertBefore(caption, table.firstChild);
        }

        // Enhance headers
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            if (!header.id) {
                header.id = `header-${index}`;
            }
            if (!header.getAttribute('scope')) {
                header.setAttribute('scope', 'col');
            }
        });

        // Associate cells with headers
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                const header = headers[index];
                if (header && !cell.getAttribute('headers')) {
                    cell.setAttribute('headers', header.id);
                }
            });
        });
    }

    /**
     * Skip Links
     */
    addSkipLinks() {
        const skipLinks = document.createElement('div');
        skipLinks.className = 'skip-links';
        skipLinks.innerHTML = `
            <a href="#main-content" class="skip-link">Skip to main content</a>
            <a href="#navigation" class="skip-link">Skip to navigation</a>
        `;
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.focusTrap) {
            this.focusTrap.release();
        }
        
        this.keyboardListeners.forEach((listener, element) => {
            element.removeEventListener('keydown', listener);
        });
        
        if (this.announcer) {
            this.announcer.remove();
        }
    }
}

// Create singleton instance
const accessibilityManager = new AccessibilityManager();

// React hook for accessibility features
export const useAccessibility = () => {
    const [highContrast, setHighContrast] = React.useState(
        document.body.classList.contains('high-contrast')
    );

    React.useEffect(() => {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    setHighContrast(document.body.classList.contains('high-contrast'));
                }
            });
        });

        observer.observe(document.body, { attributes: true });
        return () => observer.disconnect();
    }, []);

    return {
        highContrast,
        toggleHighContrast: accessibilityManager.toggleHighContrastMode.bind(accessibilityManager),
        announce: accessibilityManager.announce.bind(accessibilityManager),
        trapFocus: accessibilityManager.trapFocus.bind(accessibilityManager),
        releaseFocusTrap: accessibilityManager.releaseFocusTrap.bind(accessibilityManager),
        enhanceFormAccessibility: accessibilityManager.enhanceFormAccessibility.bind(accessibilityManager)
    };
};

export default accessibilityManager;
/* =============================================================================
   static/js/components.js - Composants partagés SIRH RAG
   ============================================================================= */

// Composants réutilisables
const Components = {
    
    // Modal générique
    Modal: {
        create(title, content, options = {}) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="modal-content bg-white rounded-lg shadow-xl max-w-md w-full mx-4 fade-in">
                    <div class="modal-header p-6 border-b">
                        <div class="flex justify-between items-center">
                            <h3 class="text-lg font-semibold">${title}</h3>
                            <button class="modal-close text-gray-400 hover:text-gray-600 text-xl">×</button>
                        </div>
                    </div>
                    <div class="modal-body p-6">
                        ${content}
                    </div>
                    ${options.actions ? `
                        <div class="modal-footer p-6 border-t bg-gray-50 rounded-b-lg">
                            ${options.actions}
                        </div>
                    ` : ''}
                </div>
            `;
            
            // Event listeners
            modal.querySelector('.modal-close').addEventListener('click', () => this.close(modal));
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.close(modal);
            });
            
            // ESC key
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    this.close(modal);
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
            
            document.body.appendChild(modal);
            return modal;
        },
        
        close(modal) {
            modal.classList.add('fade-out');
            setTimeout(() => {
                if (modal.parentElement) {
                    modal.remove();
                }
            }, 200);
        },
        
        confirm(message, onConfirm, onCancel = null) {
            const actions = `
                <div class="flex justify-end space-x-3">
                    <button class="modal-cancel action-button secondary">Annuler</button>
                    <button class="modal-confirm action-button primary">Confirmer</button>
                </div>
            `;
            
            const modal = this.create('Confirmation', message, { actions });
            
            modal.querySelector('.modal-cancel').addEventListener('click', () => {
                this.close(modal);
                if (onCancel) onCancel();
            });
            
            modal.querySelector('.modal-confirm').addEventListener('click', () => {
                this.close(modal);
                if (onConfirm) onConfirm();
            });
            
            return modal;
        }
    },
    
    // Toast notifications
    Toast: {
        container: null,
        
        init() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.className = 'toast-container fixed top-4 right-4 z-50 space-y-2';
                document.body.appendChild(this.container);
            }
        },
        
        show(message, type = 'info', duration = 4000) {
            this.init();
            
            const toast = document.createElement('div');
            toast.className = `toast ${type} fade-in bg-white rounded-lg shadow-lg border-l-4 p-4 max-w-sm`;
            
            const colors = {
                info: 'border-blue-500',
                success: 'border-green-500',
                warning: 'border-yellow-500',
                error: 'border-red-500'
            };
            
            const icons = {
                info: 'ℹ️',
                success: '✅',
                warning: '⚠️',
                error: '❌'
            };
            
            toast.classList.add(colors[type] || colors.info);
            
            toast.innerHTML = `
                <div class="flex items-start">
                    <span class="text-lg mr-3">${icons[type] || icons.info}</span>
                    <div class="flex-1">
                        <p class="text-sm text-gray-800">${message}</p>
                    </div>
                    <button class="toast-close ml-2 text-gray-400 hover:text-gray-600">×</button>
                </div>
            `;
            
            // Event listener pour fermer
            toast.querySelector('.toast-close').addEventListener('click', () => {
                this.remove(toast);
            });
            
            this.container.appendChild(toast);
            
            // Auto-remove
            if (duration > 0) {
                setTimeout(() => this.remove(toast), duration);
            }
            
            return toast;
        },
        
        remove(toast) {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 200);
        },
        
        success(message) { return this.show(message, 'success'); },
        warning(message) { return this.show(message, 'warning'); },
        error(message) { return this.show(message, 'error'); },
        info(message) { return this.show(message, 'info'); }
    },
    
    // Loading spinner
    Spinner: {
        create(text = 'Chargement...', size = 'md') {
            const sizes = {
                sm: 'w-4 h-4',
                md: 'w-6 h-6',
                lg: 'w-8 h-8'
            };
            
            const spinner = document.createElement('div');
            spinner.className = 'flex items-center justify-center space-x-2';
            spinner.innerHTML = `
                <div class="loading-spin border-2 border-gray-200 border-t-blue-600 rounded-full ${sizes[size]}"></div>
                <span class="text-gray-600">${text}</span>
            `;
            
            return spinner;
        },
        
        overlay(text = 'Chargement...') {
            const overlay = document.createElement('div');
            overlay.className = 'spinner-overlay fixed inset-0 bg-white bg-opacity-75 flex items-center justify-center z-50';
            overlay.appendChild(this.create(text, 'lg'));
            document.body.appendChild(overlay);
            return overlay;
        }
    },
    
    // Graphiques simples
    Chart: {
        createProgressRing(percentage, size = 100, color = '#2563eb') {
            const radius = (size - 10) / 2;
            const circumference = 2 * Math.PI * radius;
            const strokeDasharray = circumference;
            const strokeDashoffset = circumference - (percentage / 100) * circumference;
            
            return `
                <div class="relative inline-flex items-center justify-center">
                    <svg width="${size}" height="${size}" class="transform -rotate-90">
                        <circle
                            cx="${size / 2}"
                            cy="${size / 2}"
                            r="${radius}"
                            stroke="#e5e7eb"
                            stroke-width="8"
                            fill="none"
                        />
                        <circle
                            cx="${size / 2}"
                            cy="${size / 2}"
                            r="${radius}"
                            stroke="${color}"
                            stroke-width="8"
                            fill="none"
                            stroke-dasharray="${strokeDasharray}"
                            stroke-dashoffset="${strokeDashoffset}"
                            stroke-linecap="round"
                            class="transition-all duration-300"
                        />
                    </svg>
                    <span class="absolute text-sm font-semibold">${percentage}%</span>
                </div>
            `;
        },
        
        createBarChart(data, options = {}) {
            const maxValue = Math.max(...data.map(d => d.value));
            const height = options.height || 200;
            const barColor = options.color || '#2563eb';
            
            return `
                <div class="bar-chart" style="height: ${height}px;">
                    <div class="flex items-end justify-between h-full space-x-1">
                        ${data.map(item => {
                            const barHeight = (item.value / maxValue) * height * 0.8;
                            return `
                                <div class="flex flex-col items-center">
                                    <div 
                                        class="bg-blue-500 transition-all duration-500 hover:bg-blue-600 rounded-t"
                                        style="width: 40px; height: ${barHeight}px; background-color: ${barColor};"
                                        title="${item.label}: ${item.value}"
                                    ></div>
                                    <div class="text-xs mt-2 text-center">${item.label}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }
    },
    
    // Formulaires
    Form: {
        createField(type, name, label, options = {}) {
            const fieldId = `field-${name}`;
            const required = options.required ? 'required' : '';
            const placeholder = options.placeholder || '';
            const value = options.value || '';
            
            let inputHtml = '';
            
            switch (type) {
                case 'text':
                case 'email':
                case 'password':
                    inputHtml = `
                        <input 
                            type="${type}" 
                            id="${fieldId}" 
                            name="${name}" 
                            value="${value}"
                            placeholder="${placeholder}"
                            class="form-input w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            ${required}
                        >
                    `;
                    break;
                    
                case 'textarea':
                    inputHtml = `
                        <textarea 
                            id="${fieldId}" 
                            name="${name}" 
                            placeholder="${placeholder}"
                            rows="${options.rows || 3}"
                            class="form-input w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            ${required}
                        >${value}</textarea>
                    `;
                    break;
                    
                case 'select':
                    const optionsHtml = (options.options || []).map(opt => 
                        `<option value="${opt.value}" ${opt.value === value ? 'selected' : ''}>${opt.label}</option>`
                    ).join('');
                    inputHtml = `
                        <select 
                            id="${fieldId}" 
                            name="${name}"
                            class="form-input w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            ${required}
                        >
                            ${optionsHtml}
                        </select>
                    `;
                    break;
            }
            
            return `
                <div class="form-field mb-4">
                    <label for="${fieldId}" class="block text-sm font-medium text-gray-700 mb-1">
                        ${label} ${options.required ? '<span class="text-red-500">*</span>' : ''}
                    </label>
                    ${inputHtml}
                    ${options.help ? `<p class="text-xs text-gray-500 mt-1">${options.help}</p>` : ''}
                </div>
            `;
        },
        
        validate(form) {
            const inputs = form.querySelectorAll('input, textarea, select');
            let isValid = true;
            
            inputs.forEach(input => {
                this.removeFieldError(input);
                
                if (input.hasAttribute('required') && !input.value.trim()) {
                    this.showFieldError(input, 'Ce champ est requis');
                    isValid = false;
                }
                
                if (input.type === 'email' && input.value) {
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailRegex.test(input.value)) {
                        this.showFieldError(input, 'Email invalide');
                        isValid = false;
                    }
                }
            });
            
            return isValid;
        },
        
        showFieldError(input, message) {
            input.classList.add('border-red-500');
            
            let errorDiv = input.parentElement.querySelector('.field-error');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'field-error text-red-500 text-xs mt-1';
                input.parentElement.appendChild(errorDiv);
            }
            errorDiv.textContent = message;
        },
        
        removeFieldError(input) {
            input.classList.remove('border-red-500');
            const errorDiv = input.parentElement.querySelector('.field-error');
            if (errorDiv) {
                errorDiv.remove();
            }
        }
    },
    
    // Tableaux
    Table: {
        create(data, columns, options = {}) {
            const tableClass = options.className || 'min-w-full divide-y divide-gray-200';
            const headerClass = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
            const cellClass = 'px-6 py-4 whitespace-nowrap text-sm text-gray-900';
            
            const headerHtml = columns.map(col => 
                `<th class="${headerClass}">${col.label}</th>`
            ).join('');
            
            const rowsHtml = data.map(row => {
                const cellsHtml = columns.map(col => {
                    let value = row[col.key];
                    if (col.render) {
                        value = col.render(value, row);
                    }
                    return `<td class="${cellClass}">${value}</td>`;
                }).join('');
                
                return `<tr class="hover:bg-gray-50">${cellsHtml}</tr>`;
            }).join('');
            
            return `
                <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
                    <table class="${tableClass}">
                        <thead class="bg-gray-50">
                            <tr>${headerHtml}</tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            `;
        }
    }
};

// Utilitaires globaux
const GlobalUtils = {
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            ...options
        };
        return new Date(date).toLocaleDateString('fr-FR', defaultOptions);
    },

    formatTime(date) {
        return new Date(date).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    formatNumber(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    },

    formatCurrency(amount, currency = 'XPF') {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    throttle(func, limit) {
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
    },

    generateId() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    },

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            Components.Toast.success('Copié dans le presse-papiers');
        }).catch(() => {
            // Fallback pour les navigateurs plus anciens
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            Components.Toast.success('Copié dans le presse-papiers');
        });
    },

    downloadFile(content, filename, type = 'text/plain') {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

// Système de gestion d'état simple
const StateManager = {
    state: {},
    listeners: {},

    set(key, value) {
        const oldValue = this.state[key];
        this.state[key] = value;
        
        if (this.listeners[key]) {
            this.listeners[key].forEach(callback => {
                callback(value, oldValue);
            });
        }
    },

    get(key) {
        return this.state[key];
    },

    subscribe(key, callback) {
        if (!this.listeners[key]) {
            this.listeners[key] = [];
        }
        this.listeners[key].push(callback);
        
        // Retourner une fonction de désabonnement
        return () => {
            const index = this.listeners[key].indexOf(callback);
            if (index > -1) {
                this.listeners[key].splice(index, 1);
            }
        };
    },

    reset() {
        this.state = {};
        this.listeners = {};
    }
};

// Gestionnaire de thème
const ThemeManager = {
    init() {
        // Détecter le thème préféré
        const savedTheme = localStorage.getItem('sirh-theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        this.setTheme(theme);
        
        // Écouter les changements de préférence système
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('sirh-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('sirh-theme', theme);
        StateManager.set('theme', theme);
    },

    toggle() {
        const currentTheme = this.getCurrentTheme();
        this.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    },

    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }
};

// Gestionnaire de raccourcis clavier
const KeyboardManager = {
    shortcuts: {},

    init() {
        document.addEventListener('keydown', this.handleKeydown.bind(this));
    },

    register(combination, callback, description = '') {
        this.shortcuts[combination] = { callback, description };
    },

    unregister(combination) {
        delete this.shortcuts[combination];
    },

    handleKeydown(e) {
        const combination = this.getCombination(e);
        const shortcut = this.shortcuts[combination];
        
        if (shortcut && this.shouldTrigger(e)) {
            e.preventDefault();
            shortcut.callback(e);
        }
    },

    getCombination(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        if (e.metaKey) parts.push('meta');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    },

    shouldTrigger(e) {
        // Ne pas déclencher si on est dans un input/textarea
        const activeElement = document.activeElement;
        return !['INPUT', 'TEXTAREA', 'SELECT'].includes(activeElement.tagName) &&
               !activeElement.contentEditable;
    },

    getRegisteredShortcuts() {
        return Object.entries(this.shortcuts).map(([combination, data]) => ({
            combination,
            description: data.description
        }));
    }
};

// Gestionnaire de performance
const PerformanceMonitor = {
    metrics: {
        pageLoadTime: 0,
        firstContentfulPaint: 0,
        domContentLoaded: 0,
        apiCalls: 0,
        errors: 0
    },

    init() {
        this.measurePageLoad();
        this.measureWebVitals();
        this.setupErrorTracking();
    },

    measurePageLoad() {
        window.addEventListener('load', () => {
            const navigation = performance.getEntriesByType('navigation')[0];
            this.metrics.pageLoadTime = navigation.loadEventEnd - navigation.loadEventStart;
            this.metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
        });
    },

    measureWebVitals() {
        // Mesurer First Contentful Paint
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.name === 'first-contentful-paint') {
                    this.metrics.firstContentfulPaint = entry.startTime;
                }
            }
        });
        observer.observe({ entryTypes: ['paint'] });
    },

    setupErrorTracking() {
        window.addEventListener('error', () => {
            this.metrics.errors++;
        });

        window.addEventListener('unhandledrejection', () => {
            this.metrics.errors++;
        });
    },

    trackApiCall(duration) {
        this.metrics.apiCalls++;
        StateManager.set('lastApiCall', { timestamp: Date.now(), duration });
    },

    getMetrics() {
        return { ...this.metrics };
    }
};

// Gestionnaire d'accessibilité
const AccessibilityManager = {
    init() {
        this.setupFocusManagement();
        this.setupKeyboardNavigation();
        this.setupScreenReaderSupport();
    },

    setupFocusManagement() {
        // Ajouter des indicateurs de focus visibles
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('using-keyboard');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('using-keyboard');
        });
    },

    setupKeyboardNavigation() {
        // Navigation au clavier pour les éléments interactifs
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                const target = e.target;
                if (target.hasAttribute('role') && target.getAttribute('role') === 'button') {
                    e.preventDefault();
                    target.click();
                }
            }
        });
    },

    setupScreenReaderSupport() {
        // Annoncer les changements dynamiques
        this.createLiveRegion();
    },

    createLiveRegion() {
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'live-region';
        document.body.appendChild(liveRegion);
    },

    announce(message) {
        const liveRegion = document.getElementById('live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
            setTimeout(() => {
                liveRegion.textContent = '';
            }, 1000);
        }
    }
};

// Exposition globale des composants
window.Components = Components;
window.GlobalUtils = GlobalUtils;
window.StateManager = StateManager;
window.ThemeManager = ThemeManager;
window.KeyboardManager = KeyboardManager;
window.PerformanceMonitor = PerformanceMonitor;
window.AccessibilityManager = AccessibilityManager;

// Initialisation automatique
document.addEventListener('DOMContentLoaded', () => {
    console.log('🧩 Initialisation des composants globaux...');
    
    try {
        ThemeManager.init();
        KeyboardManager.init();
        PerformanceMonitor.init();
        AccessibilityManager.init();
        
        // Raccourcis globaux
        KeyboardManager.register('ctrl+k', () => {
            const searchInput = document.querySelector('input[type="text"]');
            if (searchInput) {
                searchInput.focus();
            }
        }, 'Recherche rapide');

        KeyboardManager.register('ctrl+shift+d', () => {
            ThemeManager.toggle();
        }, 'Basculer le thème');

        KeyboardManager.register('?', () => {
            showKeyboardShortcuts();
        }, 'Afficher les raccourcis');
        
        console.log('✅ Composants globaux initialisés');
        
    } catch (error) {
        console.error('❌ Erreur initialisation composants:', error);
    }
});

// Fonction pour afficher les raccourcis clavier
function showKeyboardShortcuts() {
    const shortcuts = KeyboardManager.getRegisteredShortcuts();
    const content = `
        <div class="space-y-3">
            <p class="text-gray-600">Raccourcis clavier disponibles :</p>
            ${shortcuts.map(shortcut => `
                <div class="flex justify-between items-center py-1">
                    <span class="font-mono text-sm bg-gray-100 px-2 py-1 rounded">${shortcut.combination}</span>
                    <span class="text-sm text-gray-600">${shortcut.description}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    Components.Modal.create('Raccourcis clavier', content);
}

// Styles CSS additionnels pour les composants
const componentStyles = `
    .fade-in { animation: fadeIn 0.3s ease-in; }
    .fade-out { animation: fadeOut 0.2s ease-out; }
    .slide-in { animation: slideIn 0.4s ease-out; }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    .using-keyboard *:focus {
        outline: 2px solid #2563eb !important;
        outline-offset: 2px !important;
    }
    
    .toast {
        transform: translateX(100%);
        animation: slideInRight 0.3s ease-out forwards;
    }
    
    .toast.fade-out {
        animation: slideOutRight 0.2s ease-in forwards;
    }
    
    @keyframes slideInRight {
        to { transform: translateX(0); }
    }
    
    @keyframes slideOutRight {
        to { transform: translateX(100%); }
    }
    
    .modal-content {
        animation: modalIn 0.3s ease-out;
    }
    
    @keyframes modalIn {
        from {
            opacity: 0;
            transform: scale(0.95) translateY(-10px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }
    
    [data-theme="dark"] {
        --bg-primary: #1f2937;
        --bg-secondary: #111827;
        --text-primary: #f9fafb;
        --text-secondary: #d1d5db;
        --border-color: #374151;
    }
    
    [data-theme="dark"] body {
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }
    
    [data-theme="dark"] .bg-white {
        background-color: var(--bg-secondary) !important;
    }
    
    [data-theme="dark"] .text-gray-800 {
        color: var(--text-primary) !important;
    }
    
    [data-theme="dark"] .border-gray-200 {
        border-color: var(--border-color) !important;
    }
`;

// Injecter les styles
const styleSheet = document.createElement('style');
styleSheet.textContent = componentStyles;
document.head.appendChild(styleSheet);
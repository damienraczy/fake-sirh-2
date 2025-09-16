/* =============================================================================
   RAG SIRH - Utilitaires partagés
   ============================================================================= */

// Configuration globale
const AppConfig = {
    API_BASE: '',
    MARKDOWN_OPTIONS: {
        html: false,
        breaks: true,
        linkify: true,
        typographer: true
    }
};

// Utilitaires généraux
const Utils = {
    // Initialiser markdown-it
    markdown: window.markdownit(AppConfig.MARKDOWN_OPTIONS),

    // Échapper le HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Rendre le markdown en HTML sécurisé
    renderMarkdown(text) {
        return this.markdown.render(text);
    },

    // Formater les nombres
    formatNumber(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    },

    // Formater les dates
    formatDate(date) {
        return new Date(date).toLocaleDateString('fr-FR');
    },

    // Debounce pour les inputs
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

    // Afficher/masquer un élément
    toggle(element, show) {
        element.classList.toggle('hidden', !show);
    },

    // Afficher une notification simple
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#dc2626' : '#2563eb'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// Gestionnaire d'API
const ApiClient = {
    // Appel générique
    async call(endpoint, options = {}) {
        try {
            const response = await axios({
                url: AppConfig.API_BASE + endpoint,
                method: options.method || 'GET',
                data: options.data,
                ...options
            });
            return response.data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Requête RAG
    async query(question) {
        return this.call('/query', {
            method: 'POST',
            data: { question, include_sources: true }
        });
    },

    // Statut système
    async getStatus() {
        return this.call('/status');
    },

    // Départements
    async getDepartments() {
        return this.call('/departments');
    },

    // Top performers
    async getTopPerformers(limit = 5) {
        return this.call(`/top-performers?limit=${limit}`);
    },

    // Réindexation
    async reindex() {
        return this.call('/reindex', { method: 'POST' });
    }
};

// Gestionnaire d'état simple
const AppState = {
    isLoading: false,
    lastQuery: null,
    stats: null,

    setLoading(loading) {
        this.isLoading = loading;
        document.dispatchEvent(new CustomEvent('loadingChanged', { 
            detail: { loading } 
        }));
    },

    setStats(stats) {
        this.stats = stats;
        document.dispatchEvent(new CustomEvent('statsChanged', { 
            detail: { stats } 
        }));
    }
};

// Animation CSS pour les notifications
const notificationStyles = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;

// Injecter les styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Export des utilitaires globaux
window.Utils = Utils;
window.ApiClient = ApiClient;
window.AppState = AppState;
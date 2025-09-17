/* =============================================================================
   RAG SIRH - Utilitaires avec support mémoire conversationnelle
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

// Utilitaires généraux (inchangés)
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
            background: ${type === 'error' ? '#dc2626' : type === 'warning' ? '#d97706' : '#2563eb'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
            max-width: 300px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// Gestionnaire d'API étendu avec mémoire
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

    // Requête RAG avec session
    async queryWithSession(question, sessionId = null) {
        return this.call('/query', {
            method: 'POST',
            data: { 
                question, 
                session_id: sessionId,
                include_sources: true 
            }
        });
    },

    // Requête RAG (version simple pour compatibilité)
    async query(question) {
        return this.queryWithSession(question);
    },

    // === NOUVELLES MÉTHODES MÉMOIRE ===

    // Récupérer l'historique d'une conversation
    async getConversationHistory(sessionId) {
        return this.call(`/conversations/${sessionId}`);
    },

    // Rechercher dans les conversations
    async searchConversations(query, limit = 10) {
        return this.call(`/conversations/search/${encodeURIComponent(query)}?limit=${limit}`);
    },

    // Statistiques de mémoire
    async getMemoryStats() {
        return this.call('/memory/stats');
    },

    // Nettoyer la mémoire
    async cleanupMemory() {
        return this.call('/memory/cleanup', { method: 'POST' });
    },

    // === MÉTHODES EXISTANTES ===

    // Statut système (mis à jour avec info mémoire)
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
    },

    // Informations système complètes
    async getSystemInfo() {
        return this.call('/system/info');
    }
};

// Gestionnaire d'état étendu avec mémoire
const AppState = {
    isLoading: false,
    lastQuery: null,
    stats: null,
    currentSession: null,
    memoryStats: null,

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
    },

    setCurrentSession(sessionId) {
        this.currentSession = sessionId;
        document.dispatchEvent(new CustomEvent('sessionChanged', { 
            detail: { sessionId } 
        }));
    },

    setMemoryStats(memoryStats) {
        this.memoryStats = memoryStats;
        document.dispatchEvent(new CustomEvent('memoryStatsChanged', { 
            detail: { memoryStats } 
        }));
    }
};

// Gestionnaire de mémoire conversationnelle
const MemoryManager = {
    // Afficher l'historique de la session courante
    async showCurrentHistory() {
        if (!AppState.currentSession) {
            Utils.showNotification('Aucune session active', 'warning');
            return;
        }

        try {
            const history = await ApiClient.getConversationHistory(AppState.currentSession);
            this.displayHistoryModal(history);
        } catch (error) {
            console.error('Erreur récupération historique:', error);
            Utils.showNotification('Erreur récupération historique', 'error');
        }
    },

    // Rechercher dans les conversations
    async searchHistory(query) {
        if (!query.trim()) return;

        try {
            const results = await ApiClient.searchConversations(query);
            this.displaySearchResults(query, results);
        } catch (error) {
            console.error('Erreur recherche:', error);
            Utils.showNotification('Erreur de recherche', 'error');
        }
    },

    // Afficher l'historique dans une modal
    displayHistoryModal(history) {
        const modal = this.createModal('Historique de conversation', `
            <div class="conversation-history">
                <p class="text-sm text-gray-600 mb-4">
                    Session: ${history.session_id.substring(0, 8)}... 
                    (${history.total_messages} messages)
                </p>
                <div class="messages-list max-h-96 overflow-y-auto space-y-3">
                    ${history.messages.map(msg => `
                        <div class="message-item p-3 rounded ${msg.role === 'user' ? 'bg-blue-50' : 'bg-gray-50'}">
                            <div class="font-medium text-sm mb-1">
                                ${msg.role === 'user' ? '👤 Vous' : '🤖 Assistant'}
                                <span class="text-gray-500 font-normal">
                                    ${new Date(msg.timestamp).toLocaleString('fr-FR')}
                                </span>
                            </div>
                            <div class="text-sm">
                                ${msg.content.length > 200 ? msg.content.substring(0, 200) + '...' : msg.content}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `);
    },

    // Afficher les résultats de recherche
    displaySearchResults(query, results) {
        const modal = this.createModal(`Recherche: "${query}"`, `
            <div class="search-results">
                <p class="text-sm text-gray-600 mb-4">
                    ${results.results.length} résultat(s) trouvé(s)
                </p>
                <div class="results-list max-h-96 overflow-y-auto space-y-3">
                    ${results.results.map(result => `
                        <div class="result-item p-3 rounded bg-gray-50 border">
                            <div class="font-medium text-sm mb-1">
                                ${result.role === 'user' ? '👤' : '🤖'} 
                                Session: ${result.session_id.substring(0, 8)}...
                                <span class="text-gray-500 font-normal">
                                    ${new Date(result.timestamp).toLocaleString('fr-FR')}
                                </span>
                            </div>
                            <div class="text-sm">
                                ${this.highlightSearch(result.content, query)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `);
    },

    // Créer une modal simple
    createModal(title, content) {
        const modalHtml = `
            <div class="modal-overlay fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="modal-content bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
                    <div class="modal-header p-4 border-b">
                        <div class="flex justify-between items-center">
                            <h3 class="text-lg font-semibold">${title}</h3>
                            <button class="modal-close text-gray-400 hover:text-gray-600 text-xl">×</button>
                        </div>
                    </div>
                    <div class="modal-body p-4">
                        ${content}
                    </div>
                </div>
            </div>
        `;

        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        const modal = modalDiv.firstElementChild;

        // Event listeners
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // ESC key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);

        document.body.appendChild(modal);
        return modal;
    },

    // Surligner les termes de recherche
    highlightSearch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
    },

    // Nettoyer la mémoire
    async cleanupMemory() {
        if (!confirm('Voulez-vous vraiment nettoyer les anciennes conversations ?')) {
            return;
        }

        try {
            await ApiClient.cleanupMemory();
            Utils.showNotification('Nettoyage de la mémoire effectué');
            
            // Recharger les stats
            this.refreshMemoryStats();
        } catch (error) {
            console.error('Erreur nettoyage:', error);
            Utils.showNotification('Erreur lors du nettoyage', 'error');
        }
    },

    // Rafraîchir les stats de mémoire
    async refreshMemoryStats() {
        try {
            const memoryStats = await ApiClient.getMemoryStats();
            AppState.setMemoryStats(memoryStats);
        } catch (error) {
            console.error('Erreur stats mémoire:', error);
        }
    }
};

// Animation CSS pour les notifications (inchangé)
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

// Raccourcis clavier étendus
document.addEventListener('keydown', (e) => {
    // Ctrl+H pour afficher l'historique
    if (e.ctrlKey && e.key === 'h') {
        e.preventDefault();
        MemoryManager.showCurrentHistory();
    }
    
    // Ctrl+F pour rechercher dans l'historique
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const query = prompt('Rechercher dans les conversations:');
        if (query) {
            MemoryManager.searchHistory(query);
        }
    }
    
    // Ctrl+Shift+C pour nettoyer la mémoire
    if (e.ctrlKey && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        MemoryManager.cleanupMemory();
    }
});

// Export des utilitaires globaux
window.Utils = Utils;
window.ApiClient = ApiClient;
window.AppState = AppState;
window.MemoryManager = MemoryManager;
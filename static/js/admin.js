/* =============================================================================
   RAG SIRH - Logique admin
   ============================================================================= */

class AdminManager {
    constructor() {
        this.refreshInterval = null;
        this.isReindexing = false;
        
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupElements());
        } else {
            this.setupElements();
        }
    }

    setupElements() {
        this.setupEventListeners();
        this.loadAllData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Bouton de réindexation
        const reindexButton = document.getElementById('reindexButton');
        if (reindexButton) {
            reindexButton.addEventListener('click', () => this.reindexDocuments());
        }

        // Rafraîchissement manuel (Ctrl+R)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                this.loadAllData();
                Utils.showNotification('Données rechargées');
            }
        });
    }

    async loadAllData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadDatabaseStats(),
                this.loadRAGStats()
            ]);
        } catch (error) {
            console.error('Erreur lors du chargement des données admin:', error);
            Utils.showNotification('Erreur de chargement des données', 'error');
        }
    }

    async loadSystemStatus() {
        try {
            const status = await ApiClient.getStatus();
            this.updateSystemStatusDisplay(status);
        } catch (error) {
            console.error('Erreur chargement statut système:', error);
            this.showSystemStatusError();
        }
    }

    async loadDatabaseStats() {
        try {
            const departments = await ApiClient.getDepartments();
            const totalEmployees = departments.reduce((sum, dept) => sum + dept.count, 0);
            
            const dbStats = {
                totalEmployees,
                departments: departments.length,
                topDepartment: departments.reduce((prev, current) => 
                    (prev.count > current.count) ? prev : current
                )
            };
            
            this.updateDatabaseStatsDisplay(dbStats);
        } catch (error) {
            console.error('Erreur chargement stats BD:', error);
            this.showDatabaseStatsError();
        }
    }

    async loadRAGStats() {
        try {
            const status = await ApiClient.getStatus();
            const ragStats = {
                documentsIndexed: status.documents_indexed,
                systemReady: status.system_ready,
                lastUpdate: new Date().toLocaleString('fr-FR')
            };
            
            this.updateRAGStatsDisplay(ragStats);
        } catch (error) {
            console.error('Erreur chargement stats RAG:', error);
            this.showRAGStatsError();
        }
    }

    updateSystemStatusDisplay(status) {
        const container = document.getElementById('systemStatus');
        if (!container) return;

        const statusColor = status.system_ready ? 'success' : 'error';
        const statusText = status.system_ready ? 'Opérationnel' : 'En cours d\'init.';

        container.innerHTML = `
            <div class="status-item">
                <div class="status-value ${statusColor}">
                    ${status.system_ready ? '✅' : '⚠️'}
                </div>
                <div class="status-label">Statut système</div>
            </div>
            <div class="status-item">
                <div class="status-value">${status.documents_indexed}</div>
                <div class="status-label">Documents indexés</div>
            </div>
            <div class="status-item">
                <div class="status-value ${statusColor}">${statusText}</div>
                <div class="status-label">État RAG</div>
            </div>
        `;
    }

    updateDatabaseStatsDisplay(stats) {
        const container = document.getElementById('dbStats');
        if (!container) return;

        container.innerHTML = `
            <div class="stats-item">
                <div class="stats-value">${Utils.formatNumber(stats.totalEmployees)}</div>
                <div class="stats-label">Employés total</div>
            </div>
            <div class="stats-item">
                <div class="stats-value">${stats.departments}</div>
                <div class="stats-label">Départements</div>
            </div>
            <div class="stats-item">
                <div class="stats-value">${stats.topDepartment.count}</div>
                <div class="stats-label">Plus gros département<br><small>${stats.topDepartment.department}</small></div>
            </div>
        `;
    }

    updateRAGStatsDisplay(stats) {
        const container = document.getElementById('ragStats');
        if (!container) return;

        container.innerHTML = `
            <div class="stats-item">
                <div class="stats-value">${Utils.formatNumber(stats.documentsIndexed)}</div>
                <div class="stats-label">Documents indexés</div>
            </div>
            <div class="stats-item">
                <div class="stats-value ${stats.systemReady ? 'success' : 'error'}">
                    ${stats.systemReady ? 'Prêt' : 'Init'}
                </div>
                <div class="stats-label">État du système</div>
            </div>
            <div class="stats-item">
                <div class="stats-value" style="font-size: 0.9rem;">
                    ${stats.lastUpdate}
                </div>
                <div class="stats-label">Dernière MAJ</div>
            </div>
        `;
    }

    async reindexDocuments() {
        if (this.isReindexing) return;

        const button = document.getElementById('reindexButton');
        const originalText = button.textContent;
        
        try {
            this.isReindexing = true;
            button.disabled = true;
            button.textContent = '🔄 Réindexation...';
            
            Utils.showNotification('Réindexation démarrée...');
            
            await ApiClient.reindex();
            
            Utils.showNotification('Réindexation terminée avec succès!');
            
            // Recharger les stats après réindexation
            setTimeout(() => {
                this.loadRAGStats();
            }, 1000);
            
        } catch (error) {
            console.error('Erreur lors de la réindexation:', error);
            Utils.showNotification('Erreur lors de la réindexation', 'error');
        } finally {
            this.isReindexing = false;
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    startAutoRefresh() {
        // Rafraîchir les données toutes les 30 secondes
        this.refreshInterval = setInterval(() => {
            this.loadAllData();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showSystemStatusError() {
        const container = document.getElementById('systemStatus');
        if (container) {
            container.innerHTML = '<div class="error">Erreur de chargement du statut système</div>';
        }
    }

    showDatabaseStatsError() {
        const container = document.getElementById('dbStats');
        if (container) {
            container.innerHTML = '<div class="error">Erreur de chargement des statistiques BD</div>';
        }
    }

    showRAGStatsError() {
        const container = document.getElementById('ragStats');
        if (container) {
            container.innerHTML = '<div class="error">Erreur de chargement des statistiques RAG</div>';
        }
    }
}

// Gérer la fermeture de la page
window.addEventListener('beforeunload', () => {
    if (window.adminManager) {
        window.adminManager.stopAutoRefresh();
    }
});

// Initialiser le gestionnaire admin
const adminManager = new AdminManager();

// Export global
window.AdminManager = adminManager;
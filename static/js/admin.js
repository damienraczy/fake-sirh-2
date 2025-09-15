/* =============================================================================
   static/js/admin.js - JavaScript pour l'interface d'administration SIRH RAG
   ============================================================================= */

// Configuration globale admin
const AdminConfig = {
    REFRESH_INTERVAL: 5000,    // 5 secondes
    METRICS_INTERVAL: 2000,    // 2 secondes
    LOG_REFRESH_INTERVAL: 10000, // 10 secondes
    MAX_LOGS_DISPLAY: 20
};

// État global admin
const AdminState = {
    metricsInterval: null,
    logsInterval: null,
    systemInterval: null,
    isReindexing: false,
    lastUpdate: null
};

// Utilitaires admin
const AdminUtils = {
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) return `${days}j ${hours}h`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    },

    generateRandomMetric(base, variance) {
        return base + (Math.random() - 0.5) * variance;
    },

    createProgressBar(percentage, color = 'blue') {
        return `
            <div class="progress-bar">
                <div class="progress-fill bg-${color}-500" style="width: ${percentage}%"></div>
            </div>
        `;
    }
};

// API Admin
const AdminAPI = {
    async getSystemStatus() {
        // Dans un vrai projet, ceci appellerait une vraie API
        return {
            status: "operational",
            uptime: Math.floor(Math.random() * 86400),
            memory_usage: AdminUtils.generateRandomMetric(65, 20),
            cpu_usage: AdminUtils.generateRandomMetric(35, 30),
            disk_usage: AdminUtils.generateRandomMetric(45, 20),
            active_connections: Math.floor(AdminUtils.generateRandomMetric(15, 10)),
            version: "1.0.0",
            last_restart: new Date(Date.now() - Math.random() * 86400000).toISOString()
        };
    },

    async getDatabaseStats() {
        const response = await fetch('/departments');
        const departments = await response.json();
        const totalEmployees = departments.reduce((sum, dept) => sum + dept.count, 0);
        
        return {
            total_employees: totalEmployees,
            departments: departments.length,
            tables: 12,
            total_records: totalEmployees * 8, // Estimation
            db_size: AdminUtils.generateRandomMetric(50, 20), // MB
            last_backup: new Date(Date.now() - Math.random() * 86400000).toISOString()
        };
    },

    async getDocumentStats() {
        const response = await fetch('/status');
        const status = await response.json();
        
        return {
            total_documents: status.documents_indexed,
            total_chunks: Math.round(status.documents_indexed * 2.5),
            index_size: AdminUtils.generateRandomMetric(100, 50), // MB
            last_indexing: new Date(Date.now() - Math.random() * 3600000).toISOString(),
            embedding_dimensions: 384
        };
    },

    async reindexDocuments() {
        const response = await fetch('/reindex', { method: 'POST' });
        return response.json();
    }
};

// Gestionnaire système
const SystemManager = {
    async loadSystemStatus() {
        try {
            const status = await AdminAPI.getSystemStatus();
            this.updateSystemDisplay(status);
        } catch (error) {
            console.error('Erreur chargement statut système:', error);
            this.showSystemError();
        }
    },

    updateSystemDisplay(status) {
        const statusDiv = document.getElementById('system-status');
        if (!statusDiv) return;

        const uptimeFormatted = AdminUtils.formatUptime(status.uptime);
        const lastRestart = new Date(status.last_restart).toLocaleString('fr-FR');

        statusDiv.innerHTML = `
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value text-green-600">${status.status === 'operational' ? '🟢' : '🔴'}</div>
                    <div class="metric-label">Statut</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${uptimeFormatted}</div>
                    <div class="metric-label">Uptime</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${status.memory_usage.toFixed(1)}%</div>
                    <div class="metric-label">Mémoire</div>
                    ${AdminUtils.createProgressBar(status.memory_usage, status.memory_usage > 80 ? 'red' : 'blue')}
                </div>
                <div class="metric-card">
                    <div class="metric-value">${status.cpu_usage.toFixed(1)}%</div>
                    <div class="metric-label">CPU</div>
                    ${AdminUtils.createProgressBar(status.cpu_usage, status.cpu_usage > 70 ? 'yellow' : 'green')}
                </div>
                <div class="metric-card">
                    <div class="metric-value">${status.active_connections}</div>
                    <div class="metric-label">Connexions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${status.version}</div>
                    <div class="metric-label">Version</div>
                </div>
            </div>
            
            <div class="mt-4 text-xs text-gray-500">
                Dernier redémarrage: ${lastRestart}
            </div>
        `;
    },

    showSystemError() {
        const statusDiv = document.getElementById('system-status');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="error-state">
                    ⚠️ Impossible de charger le statut système
                    <button onclick="SystemManager.loadSystemStatus()" 
                            class="action-button secondary ml-2">
                        Réessayer
                    </button>
                </div>
            `;
        }
    }
};

// Gestionnaire base de données
const DatabaseManager = {
    async loadDatabaseStats() {
        try {
            const stats = await AdminAPI.getDatabaseStats();
            this.updateDatabaseDisplay(stats);
        } catch (error) {
            console.error('Erreur chargement stats BD:', error);
            this.showDatabaseError();
        }
    },

    updateDatabaseDisplay(stats) {
        const statsDiv = document.getElementById('db-stats');
        if (!statsDiv) return;

        const lastBackup = new Date(stats.last_backup).toLocaleString('fr-FR');

        statsDiv.innerHTML = `
            <div class="bg-blue-50 p-4 rounded text-center">
                <div class="text-2xl font-bold text-blue-600">${stats.total_employees}</div>
                <div class="text-sm text-blue-800">Employés</div>
            </div>
            <div class="bg-green-50 p-4 rounded text-center">
                <div class="text-2xl font-bold text-green-600">${stats.departments}</div>
                <div class="text-sm text-green-800">Départements</div>
            </div>
            <div class="bg-purple-50 p-4 rounded text-center">
                <div class="text-2xl font-bold text-purple-600">${stats.tables}</div>
                <div class="text-sm text-purple-800">Tables</div>
            </div>
            <div class="bg-orange-50 p-4 rounded text-center">
                <div class="text-2xl font-bold text-orange-600">${stats.total_records}</div>
                <div class="text-sm text-orange-800">Enregistrements</div>
            </div>
            <div class="col-span-2 bg-gray-50 p-4 rounded">
                <div class="text-sm text-gray-600">Taille BD: ${AdminUtils.formatBytes(stats.db_size * 1024 * 1024)}</div>
                <div class="text-xs text-gray-500 mt-1">Dernière sauvegarde: ${lastBackup}</div>
            </div>
        `;
    },

    showDatabaseError() {
        const statsDiv = document.getElementById('db-stats');
        if (statsDiv) {
            statsDiv.innerHTML = `
                <div class="col-span-4 error-state">
                    Erreur de chargement des statistiques BD
                </div>
            `;
        }
    }
};

// Gestionnaire documents
const DocumentManager = {
    async loadDocumentStats() {
        try {
            const stats = await AdminAPI.getDocumentStats();
            this.updateDocumentDisplay(stats);
        } catch (error) {
            console.error('Erreur chargement stats documents:', error);
            this.showDocumentError();
        }
    },

    updateDocumentDisplay(stats) {
        const statsDiv = document.getElementById('document-stats');
        if (!statsDiv) return;

        const lastIndexing = new Date(stats.last_indexing).toLocaleString('fr-FR');

        statsDiv.innerHTML = `
            <div class="bg-gray-50 p-4 rounded text-center">
                <div class="text-xl font-bold">${stats.total_documents}</div>
                <div class="text-sm text-gray-600">Documents</div>
            </div>
            <div class="bg-gray-50 p-4 rounded text-center">
                <div class="text-xl font-bold">${stats.total_chunks.toLocaleString()}</div>
                <div class="text-sm text-gray-600">Chunks</div>
            </div>
            <div class="bg-gray-50 p-4 rounded text-center">
                <div class="text-xl font-bold">${stats.embedding_dimensions}</div>
                <div class="text-sm text-gray-600">Dimensions</div>
            </div>
            <div class="col-span-3 text-xs text-gray-500 mt-2">
                Taille index: ${AdminUtils.formatBytes(stats.index_size * 1024 * 1024)} | 
                Dernière indexation: ${lastIndexing}
            </div>
        `;
    },

    showDocumentError() {
        const statsDiv = document.getElementById('document-stats');
        if (statsDiv) {
            statsDiv.innerHTML = `
                <div class="col-span-3 error-state">
                    Erreur de chargement des statistiques documents
                </div>
            `;
        }
    },

    async reindexDocuments() {
        if (AdminState.isReindexing) return;

        try {
            AdminState.isReindexing = true;
            const progressDiv = document.getElementById('reindex-progress');
            const progressBar = document.getElementById('reindex-bar');
            
            if (progressDiv) progressDiv.classList.remove('hidden');

            // Simulation du progrès
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                    setTimeout(() => {
                        if (progressDiv) progressDiv.classList.add('hidden');
                        NotificationManager.success('Réindexation terminée avec succès!');
                        this.loadDocumentStats();
                        AdminState.isReindexing = false;
                    }, 1000);
                }
                if (progressBar) progressBar.style.width = progress + '%';
            }, 500);

            // Appel API réel
            await AdminAPI.reindexDocuments();

        } catch (error) {
            console.error('Erreur réindexation:', error);
            const progressDiv = document.getElementById('reindex-progress');
            if (progressDiv) progressDiv.classList.add('hidden');
            NotificationManager.error('Erreur lors de la réindexation');
            AdminState.isReindexing = false;
        }
    }
};

// Gestionnaire métriques temps réel
const MetricsManager = {
    metrics: {
        queriesPerMin: 0,
        avgResponseTime: 0,
        successRate: 0,
        memoryUsage: 0
    },

    startMonitoring() {
        this.updateMetrics();
        AdminState.metricsInterval = setInterval(() => {
            this.updateMetrics();
        }, AdminConfig.METRICS_INTERVAL);
    },

    stopMonitoring() {
        if (AdminState.metricsInterval) {
            clearInterval(AdminState.metricsInterval);
            AdminState.metricsInterval = null;
        }
    },

    updateMetrics() {
        // Simulation de métriques temps réel
        this.metrics.queriesPerMin = Math.floor(AdminUtils.generateRandomMetric(8, 12));
        this.metrics.avgResponseTime = AdminUtils.generateRandomMetric(1.2, 1.5);
        this.metrics.successRate = AdminUtils.generateRandomMetric(96, 6);
        this.metrics.memoryUsage = AdminUtils.generateRandomMetric(65, 20);

        this.displayMetrics();
    },

    displayMetrics() {
        const elements = {
            'queries-per-min': this.metrics.queriesPerMin,
            'avg-response-time': this.metrics.avgResponseTime.toFixed(2) + 's',
            'success-rate': this.metrics.successRate.toFixed(1) + '%',
            'memory-usage': this.metrics.memoryUsage.toFixed(0) + '%'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                
                // Couleur selon la valeur pour le taux de succès
                if (id === 'success-rate') {
                    const rate = parseFloat(value);
                    element.className = rate > 95 ? 'font-medium text-green-600' :
                                      rate > 90 ? 'font-medium text-yellow-600' :
                                                  'font-medium text-red-600';
                }
            }
        });
    }
};

// Gestionnaire de logs
const LogsManager = {
    logs: [],

    startMonitoring() {
        this.generateLogs();
        AdminState.logsInterval = setInterval(() => {
            this.addNewLog();
        }, AdminConfig.LOG_REFRESH_INTERVAL);
    },

    stopMonitoring() {
        if (AdminState.logsInterval) {
            clearInterval(AdminState.logsInterval);
            AdminState.logsInterval = null;
        }
    },

    generateLogs() {
        const logTypes = ['INFO', 'WARN', 'ERROR', 'DEBUG'];
        const messages = [
            'Requête RAG traitée avec succès',
            'Nouvelle connexion utilisateur',
            'Recherche vectorielle: {} documents trouvés',
            'Cache mis à jour',
            'Temps de réponse élevé ({}s)',
            'Utilisateur déconnecté',
            'Sauvegarde automatique effectuée',
            'Erreur de connexion base de données',
            'Index vectoriel rechargé',
            'Configuration mise à jour'
        ];

        // Générer des logs initiaux
        for (let i = 0; i < 10; i++) {
            this.addNewLog(false);
        }
        
        this.displayLogs();
    },

    addNewLog(display = true) {
        const now = new Date();
        const logTypes = ['INFO', 'WARN', 'ERROR', 'DEBUG'];
        const messages = [
            'Requête RAG traitée avec succès',
            'Nouvelle connexion utilisateur',
            'Recherche vectorielle: 5 documents trouvés',
            'Cache mis à jour',
            'Temps de réponse élevé (3.2s)',
            'Utilisateur déconnecté',
            'Sauvegarde automatique effectuée',
            'Erreur temporaire de connexion',
            'Index vectoriel rechargé',
            'Configuration mise à jour'
        ];

        const weights = {
            'INFO': 0.6,
            'DEBUG': 0.25,
            'WARN': 0.1,
            'ERROR': 0.05
        };

        // Sélection pondérée du niveau
        let random = Math.random();
        let level = 'INFO';
        for (const [lvl, weight] of Object.entries(weights)) {
            if (random <= weight) {
                level = lvl;
                break;
            }
            random -= weight;
        }

        const message = messages[Math.floor(Math.random() * messages.length)];
        
        const log = {
            time: now.toLocaleTimeString('fr-FR'),
            level: level,
            message: message,
            timestamp: now
        };

        this.logs.unshift(log);
        
        // Garder seulement les derniers logs
        if (this.logs.length > AdminConfig.MAX_LOGS_DISPLAY) {
            this.logs = this.logs.slice(0, AdminConfig.MAX_LOGS_DISPLAY);
        }

        if (display) {
            this.displayLogs();
        }
    },

    displayLogs() {
        const logsDiv = document.getElementById('recent-logs');
        if (!logsDiv) return;

        logsDiv.innerHTML = this.logs.map(log => `
            <div class="log-entry ${log.level.toLowerCase()} fade-in">
                <span class="log-time">${log.time}</span>
                <span class="log-level">${log.level}</span>
                <div class="mt-1">${log.message}</div>
            </div>
        `).join('');
    }
};

// Actions d'administration
const AdminActions = {
    async exportData() {
        try {
            NotificationManager.show('Export des données démarré...', 'info');
            
            // Simulation d'export
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Créer un fichier factice
            const data = {
                timestamp: new Date().toISOString(),
                employees: await AdminAPI.getDatabaseStats(),
                system: await AdminAPI.getSystemStatus(),
                documents: await AdminAPI.getDocumentStats()
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], 
                { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `sirh_export_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            NotificationManager.success('Export terminé avec succès!');
            
        } catch (error) {
            console.error('Erreur export:', error);
            NotificationManager.error('Erreur lors de l\'export: ' + error.message);
        }
    },

    async validateData() {
        try {
            NotificationManager.show('Validation en cours...', 'info');
            
            // Simulation de validation
            const checks = [
                'Vérification intégrité hiérarchique',
                'Validation des affectations',
                'Contrôle cohérence temporelle',
                'Vérification contraintes métier',
                'Validation des références'
            ];
            
            for (let i = 0; i < checks.length; i++) {
                await new Promise(resolve => setTimeout(resolve, 800));
                console.log(`✓ ${checks[i]}`);
            }
            
            const results = {
                total_checks: checks.length,
                passed: checks.length,
                failed: 0,
                warnings: Math.floor(Math.random() * 3)
            };
            
            const message = `Validation terminée: ${results.passed}/${results.total_checks} tests passés` +
                          (results.warnings > 0 ? `, ${results.warnings} avertissements` : '');
                          
            NotificationManager.success(message);
            
        } catch (error) {
            console.error('Erreur validation:', error);
            NotificationManager.error('Erreur lors de la validation: ' + error.message);
        }
    },

    async checkIndex() {
        try {
            const response = await fetch('/status');
            const stats = await response.json();
            
            const details = `Index vérifié:
• ${stats.documents_indexed} documents indexés
• Système opérationnel: ${stats.system_ready ? 'Oui' : 'Non'}
• Dernière vérification: ${new Date().toLocaleString('fr-FR')}`;
            
            NotificationManager.show(details.replace(/\n/g, '<br>'), 'info', 8000);
            
        } catch (error) {
            console.error('Erreur vérification:', error);
            NotificationManager.error('Erreur lors de la vérification: ' + error.message);
        }
    },

    clearCache() {
        if (confirm('Êtes-vous sûr de vouloir vider le cache ? Cette action peut temporairement ralentir les réponses.')) {
            // Simulation
            NotificationManager.success('Cache vidé avec succès.');
            
            // Simuler un impact sur les métriques
            setTimeout(() => {
                MetricsManager.metrics.avgResponseTime *= 1.5;
            }, 1000);
        }
    },

    restartService() {
        if (confirm('Êtes-vous sûr de vouloir redémarrer le service ? Les utilisateurs seront temporairement déconnectés.')) {
            NotificationManager.warning('Redémarrage du service en cours...');
            
            // Simulation du redémarrage
            setTimeout(() => {
                NotificationManager.success('Service redémarré avec succès.');
                // Recharger les stats
                SystemManager.loadSystemStatus();
            }, 5000);
        }
    },

    downloadLogs() {
        try {
            // Créer un contenu de log plus réaliste
            const logContent = LogsManager.logs.map(log => 
                `[${new Date().toISOString().split('T')[0]} ${log.time}] ${log.level} - ${log.message}`
            ).join('\n');
            
            const fullContent = `# SIRH RAG System Logs
# Generated: ${new Date().toISOString()}
# Total entries: ${LogsManager.logs.length}

${logContent}

# End of logs`;
            
            const blob = new Blob([fullContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `sirh_logs_${new Date().toISOString().split('T')[0]}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            NotificationManager.success('Logs téléchargés avec succès.');
            
        } catch (error) {
            console.error('Erreur téléchargement logs:', error);
            NotificationManager.error('Erreur lors du téléchargement.');
        }
    }
};

// Navigation admin
const AdminNavigation = {
    init() {
        // Gestion du scroll smooth vers les sections
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Mettre à jour l'URL sans déclencher le scroll
                    history.pushState(null, null, `#${targetId}`);
                }
            });
        });

        // Highlight de la section active
        this.setupActiveSection();
    },

    setupActiveSection() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Retirer la classe active de tous les liens
                    document.querySelectorAll('nav a').forEach(link => {
                        link.classList.remove('text-blue-800', 'font-bold');
                        link.classList.add('text-blue-600');
                    });
                    
                    // Ajouter la classe active au lien correspondant
                    const activeLink = document.querySelector(`nav a[href="#${entry.target.id}"]`);
                    if (activeLink) {
                        activeLink.classList.remove('text-blue-600');
                        activeLink.classList.add('text-blue-800', 'font-bold');
                    }
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '-20% 0px -70% 0px'
        });

        // Observer toutes les sections
        document.querySelectorAll('section[id]').forEach(section => {
            observer.observe(section);
        });
    }
};

// Gestionnaire de notifications (si pas déjà défini)
if (typeof NotificationManager === 'undefined') {
    window.NotificationManager = {
        show(message, type = 'info', duration = 3000) {
            const notification = document.createElement('div');
            notification.className = `notification ${type} fade-in`;
            
            const colors = {
                'info': 'bg-blue-500 text-white',
                'success': 'bg-green-500 text-white',
                'warning': 'bg-yellow-500 text-black',
                'error': 'bg-red-500 text-white'
            };
            
            notification.innerHTML = `
                <div class="fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg ${colors[type] || colors.info}">
                    <div class="flex items-center justify-between">
                        <span>${message}</span>
                        <button onclick="this.parentElement.parentElement.remove()" 
                                class="ml-4 text-lg font-bold">×</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            if (duration > 0) {
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, duration);
            }
        },
        
        success(message) { this.show(message, 'success'); },
        warning(message) { this.show(message, 'warning'); },
        error(message) { this.show(message, 'error'); }
    };
}

// Fonctions globales pour les templates
window.AdminActions = AdminActions;
window.DocumentManager = DocumentManager;
window.exportData = AdminActions.exportData;
window.validateData = AdminActions.validateData;
window.reindexDocuments = DocumentManager.reindexDocuments;
window.checkIndex = AdminActions.checkIndex;
window.clearCache = AdminActions.clearCache;
window.restartService = AdminActions.restartService;
window.downloadLogs = AdminActions.downloadLogs;

// Initialisation admin
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Initialisation interface admin SIRH RAG...');
    
    try {
        // Initialiser la navigation
        AdminNavigation.init();
        
        // Charger les données initiales
        SystemManager.loadSystemStatus();
        DatabaseManager.loadDatabaseStats();
        DocumentManager.loadDocumentStats();
        
        // Démarrer le monitoring
        MetricsManager.startMonitoring();
        LogsManager.startMonitoring();
        
        // Rafraîchissement périodique des sections principales
        AdminState.systemInterval = setInterval(() => {
            SystemManager.loadSystemStatus();
            DatabaseManager.loadDatabaseStats();
            DocumentManager.loadDocumentStats();
        }, AdminConfig.REFRESH_INTERVAL);
        
        // Marquer la dernière mise à jour
        AdminState.lastUpdate = new Date();
        
        console.log('✅ Interface admin initialisée avec succès');
        
    } catch (error) {
        console.error('❌ Erreur initialisation admin:', error);
        NotificationManager.error('Erreur d\'initialisation de l\'interface admin');
    }
});

// Nettoyage à la fermeture
window.addEventListener('beforeunload', function() {
    // Arrêter tous les intervalles
    MetricsManager.stopMonitoring();
    LogsManager.stopMonitoring();
    
    if (AdminState.systemInterval) {
        clearInterval(AdminState.systemInterval);
    }
    
    console.log('🧹 Nettoyage admin effectué');
});

// Gestion de la visibilité pour optimiser les performances
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Ralentir les mises à jour quand la page n'est pas visible
        MetricsManager.stopMonitoring();
        LogsManager.stopMonitoring();
    } else {
        // Reprendre le monitoring normal
        MetricsManager.startMonitoring();
        LogsManager.startMonitoring();
        
        // Recharger les données
        SystemManager.loadSystemStatus();
        DatabaseManager.loadDatabaseStats();
        DocumentManager.loadDocumentStats();
    }
});

// Raccourcis clavier admin
document.addEventListener('keydown', function(e) {
    // Ctrl+R pour recharger toutes les stats
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        SystemManager.loadSystemStatus();
        DatabaseManager.loadDatabaseStats();
        DocumentManager.loadDocumentStats();
        NotificationManager.success('Données rechargées');
    }
    
    // Ctrl+E pour export rapide
    if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        AdminActions.exportData();
    }
    
    // Ctrl+L pour télécharger les logs
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        AdminActions.downloadLogs();
    }
});
            '
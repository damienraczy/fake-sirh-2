/* =============================================================================
   RAG SIRH - Chat avec mémoire conversationnelle
   ============================================================================= */

class ChatManager {
    constructor() {
        this.messagesContainer = null;
        this.inputField = null;
        this.sendButton = null;
        this.messageCount = 0;
        this.sessionId = null; // Nouveau : ID de session
        this.conversationLength = 0; // Nouveau : Longueur conversation
        
        this.init();
    }

    init() {
        // Attendre que le DOM soit prêt
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupElements());
        } else {
            this.setupElements();
        }
    }

    setupElements() {
        // Récupérer les éléments DOM
        this.messagesContainer = document.getElementById('messages');
        this.inputField = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');

        if (!this.messagesContainer || !this.inputField || !this.sendButton) {
            console.error('Éléments de chat manquants dans le DOM');
            return;
        }

        // Configurer les événements
        this.setupEventListeners();
        
        // Charger les statistiques
        this.loadStats();
        
        // Afficher info session
        this.showSessionInfo();
    }

    setupEventListeners() {
        // Envoi par Enter
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !AppState.isLoading) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Envoi par bouton
        this.sendButton.addEventListener('click', () => {
            if (!AppState.isLoading) {
                this.sendMessage();
            }
        });

        // Boutons d'exemples
        document.querySelectorAll('.example-button').forEach(button => {
            button.addEventListener('click', () => {
                const question = button.getAttribute('data-question');
                if (question) {
                    this.askQuestion(question);
                }
            });
        });

        // Écouter les changements d'état de chargement
        document.addEventListener('loadingChanged', (e) => {
            this.updateLoadingState(e.detail.loading);
        });
    }

    async sendMessage() {
        const question = this.inputField.value.trim();
        if (!question) return;

        // Afficher le message utilisateur
        this.addMessage('user', question);
        this.inputField.value = '';

        // Démarrer le chargement
        AppState.setLoading(true);

        try {
            // Appeler l'API RAG avec session
            const response = await ApiClient.queryWithSession(question, this.sessionId);
            
            // Mettre à jour l'ID de session si nouveau
            if (!this.sessionId) {
                this.sessionId = response.session_id;
                this.showSessionInfo();
            }
            
            // Mettre à jour la longueur de conversation
            this.conversationLength = response.conversation_length;
            
            // Afficher la réponse
            this.addMessage('assistant', response.answer, response);
            
            // Sauvegarder la dernière requête
            AppState.lastQuery = { question, response };

        } catch (error) {
            console.error('Erreur lors de la requête:', error);
            
            let errorMessage = 'Une erreur est survenue lors du traitement de votre question.';
            if (error.response?.data?.detail) {
                errorMessage = `Erreur: ${error.response.data.detail}`;
            } else if (error.message) {
                errorMessage = `Erreur: ${error.message}`;
            }
            
            this.addMessage('assistant', errorMessage);
            Utils.showNotification('Erreur lors de la requête', 'error');
        } finally {
            AppState.setLoading(false);
        }
    }

    addMessage(role, content, metadata = null) {
        // Supprimer le message de bienvenue lors du premier message
        if (this.messageCount === 0) {
            const welcomeMsg = this.messagesContainer.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.remove();
            }
        }

        // Créer le conteneur du message
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        // Créer la bulle de message
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        // Traitement du contenu selon le rôle
        if (role === 'assistant') {
            // Rendre le markdown pour les réponses de l'assistant
            bubbleDiv.innerHTML = Utils.renderMarkdown(content);
            bubbleDiv.classList.add('markdown-content');
        } else {
            // Texte simple pour les messages utilisateur
            bubbleDiv.textContent = content;
        }

        messageDiv.appendChild(bubbleDiv);

        // Ajouter les métadonnées si disponibles (version étendue)
        if (metadata && role === 'assistant') {
            const metaDiv = this.createMetadataElement(metadata);
            messageDiv.appendChild(metaDiv);
        }

        // Ajouter au conteneur et faire défiler
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        this.messageCount++;
    }

    createMetadataElement(metadata) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-metadata';
        metaDiv.style.cssText = `
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #e2e8f0;
            font-size: 0.75rem;
            color: #64748b;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        `;

        const items = [];
        
        if (metadata.query_type) {
            items.push(`📊 ${metadata.query_type}`);
        }
        
        if (metadata.sources && metadata.sources.length > 0) {
            items.push(`📚 ${metadata.sources.length} source(s)`);
        }
        
        if (metadata.response_time) {
            items.push(`⏱️ ${metadata.response_time}s`);
        }

        // Nouveau : Info conversation
        if (metadata.conversation_length) {
            items.push(`💬 ${metadata.conversation_length} msg`);
        }

        metaDiv.innerHTML = items.map(item => 
            `<span style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${item}</span>`
        ).join('');

        return metaDiv;
    }

    showSessionInfo() {
        // Afficher l'info de session si une session est active
        if (this.sessionId) {
            let sessionInfo = document.getElementById('session-info');
            if (!sessionInfo) {
                sessionInfo = document.createElement('div');
                sessionInfo.id = 'session-info';
                sessionInfo.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.75rem;
                    color: #64748b;
                    z-index: 100;
                `;
                document.body.appendChild(sessionInfo);
            }
            
            sessionInfo.innerHTML = `
                🧠 Session: ${this.sessionId.substring(0, 8)}...
                ${this.conversationLength > 0 ? `| ${this.conversationLength} messages` : ''}
                <button onclick="chatManager.clearSession()" style="margin-left: 8px; background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.75rem;">
                    🗑️ Effacer
                </button>
            `;
        }
    }

    clearSession() {
        if (confirm('Voulez-vous vraiment effacer cette conversation ?')) {
            this.sessionId = null;
            this.conversationLength = 0;
            this.messageCount = 0;
            
            // Vider l'interface
            this.messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <p>Nouvelle conversation démarrée. Posez vos questions sur les données RH.</p>
                </div>
            `;
            
            // Supprimer l'info de session
            const sessionInfo = document.getElementById('session-info');
            if (sessionInfo) {
                sessionInfo.remove();
            }
            
            Utils.showNotification('Conversation effacée');
        }
    }

    askQuestion(question) {
        this.inputField.value = question;
        this.sendMessage();
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateLoadingState(isLoading) {
        // Mettre à jour le bouton d'envoi
        const sendText = this.sendButton.querySelector('.send-text');
        const loadingText = this.sendButton.querySelector('.loading-text');
        
        if (sendText && loadingText) {
            Utils.toggle(sendText, !isLoading);
            Utils.toggle(loadingText, isLoading);
        }
        
        // Désactiver/activer les contrôles
        this.sendButton.disabled = isLoading;
        this.inputField.disabled = isLoading;
        
        // Mettre à jour le placeholder
        if (isLoading) {
            this.inputField.placeholder = 'Traitement en cours...';
        } else {
            this.inputField.placeholder = 'Tapez votre question...';
        }
    }

    async loadStats() {
        try {
            const [status, departments, memoryStats] = await Promise.all([
                ApiClient.getStatus(),
                ApiClient.getDepartments(),
                ApiClient.getMemoryStats()
            ]);

            const stats = {
                employees: departments.reduce((sum, dept) => sum + dept.count, 0),
                departments: departments.length,
                documents: status.documents_indexed,
                systemReady: status.system_ready,
                memoryEnabled: status.memory_enabled,
                totalSessions: memoryStats.total_sessions,
                totalMessages: memoryStats.total_messages
            };

            AppState.setStats(stats);
            this.updateStatsDisplay(stats);

        } catch (error) {
            console.error('Erreur lors du chargement des statistiques:', error);
            this.showStatsError();
        }
    }

    updateStatsDisplay(stats) {
        const statsContainer = document.getElementById('stats');
        if (!statsContainer) return;

        statsContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">👥 Employés</span>
                <span class="stat-value">${Utils.formatNumber(stats.employees)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🏛️ Départements</span>
                <span class="stat-value">${stats.departments}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">📄 Documents</span>
                <span class="stat-value">${Utils.formatNumber(stats.documents)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🧠 Sessions</span>
                <span class="stat-value">${Utils.formatNumber(stats.totalSessions || 0)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">
                    ${stats.systemReady ? '✅' : '⚠️'} Statut
                </span>
                <span class="stat-value ${stats.systemReady ? 'success' : 'error'}">
                    ${stats.systemReady ? 'OK' : 'Init'}
                </span>
            </div>
        `;
    }

    showStatsError() {
        const statsContainer = document.getElementById('stats');
        if (statsContainer) {
            statsContainer.innerHTML = '<div class="error">Erreur de chargement</div>';
        }
    }

    // Nouvelles méthodes pour la gestion de mémoire
    
    async getConversationHistory() {
        if (!this.sessionId) {
            Utils.showNotification('Aucune session active', 'warning');
            return;
        }
        
        try {
            const history = await ApiClient.getConversationHistory(this.sessionId);
            console.log('Historique de conversation:', history);
            return history;
        } catch (error) {
            console.error('Erreur récupération historique:', error);
            Utils.showNotification('Erreur récupération historique', 'error');
        }
    }

    async searchInHistory(query) {
        try {
            const results = await ApiClient.searchConversations(query);
            console.log('Résultats recherche:', results);
            return results;
        } catch (error) {
            console.error('Erreur recherche:', error);
            Utils.showNotification('Erreur de recherche', 'error');
        }
    }
}

// Initialiser le gestionnaire de chat
const chatManager = new ChatManager();

// Export global pour compatibilité
window.ChatManager = chatManager;
window.chatManager = chatManager;
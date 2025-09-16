/* =============================================================================
   RAG SIRH - Logique du chat
   ============================================================================= */

class ChatManager {
    constructor() {
        this.messagesContainer = null;
        this.inputField = null;
        this.sendButton = null;
        this.messageCount = 0;
        
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
            // Appeler l'API RAG
            const response = await ApiClient.query(question);
            
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

        // Ajouter les métadonnées si disponibles
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

        metaDiv.innerHTML = items.map(item => 
            `<span style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${item}</span>`
        ).join('');

        return metaDiv;
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
            const [status, departments] = await Promise.all([
                ApiClient.getStatus(),
                ApiClient.getDepartments()
            ]);

            const stats = {
                employees: departments.reduce((sum, dept) => sum + dept.count, 0),
                departments: departments.length,
                documents: status.documents_indexed,
                systemReady: status.system_ready
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
}

// Initialiser le gestionnaire de chat
const chatManager = new ChatManager();

// Export global pour compatibilité
window.ChatManager = chatManager;
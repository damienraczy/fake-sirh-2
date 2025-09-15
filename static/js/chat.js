// =============================================================================
// static/js/chat.js - Gestionnaire de chat principal
// =============================================================================

const ChatManager = {
    messageCount: 0,
    isLoading: false,

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.loadStats();
            this.setupEventListeners();
        });
    },

    setupEventListeners() {
        const input = document.getElementById('userInput');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !this.isLoading) {
                    this.sendMessage();
                }
            });
        }
    },

    async sendMessage() {
        const input = document.getElementById('userInput');
        const question = input.value.trim();
        
        if (!question || this.isLoading) return;
        
        this.isLoading = true;
        
        // Afficher le message utilisateur
        this.addMessage('user', question);
        input.value = '';
        
        // Afficher le loading
        this.showLoading(true);
        
        try {
            const response = await axios.post('/query', {
                question: question,
                include_sources: true
            });
            
            // Afficher la réponse
            this.addMessage('assistant', response.data.answer, response.data);
            
        } catch (error) {
            console.error('Erreur requête:', error);
            this.addMessage('assistant', 
                `Désolé, une erreur s'est produite: ${error.response?.data?.detail || error.message}`
            );
        } finally {
            this.showLoading(false);
            this.isLoading = false;
        }
    },

    addMessage(role, content, metadata = null) {
        const messagesDiv = document.getElementById('messages');
        
        // Supprimer le message de bienvenue
        if (this.messageCount === 0) {
            messagesDiv.innerHTML = '';
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `mb-4 ${role === 'user' ? 'text-right' : 'text-left'} chat-message`;
        
        let metadataHtml = '';
        if (metadata && role === 'assistant') {
            metadataHtml = `
                <div class="mt-2 text-xs text-gray-500">
                    <span class="bg-gray-200 px-2 py-1 rounded mr-2">📊 ${metadata.query_type}</span>
                    <span class="bg-gray-200 px-2 py-1 rounded mr-2">📚 ${metadata.sources.length} sources</span>
                    <span class="bg-gray-200 px-2 py-1 rounded">⏱️ ${metadata.response_time}s</span>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                role === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white border border-gray-200'
            }">
                ${this.escapeHtml(content)}
                ${metadataHtml}
            </div>
        `;
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        this.messageCount++;
    },

    showLoading(show) {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.toggle('hidden', !show);
        }
    },

    askExample(question) {
        const input = document.getElementById('userInput');
        if (input) {
            input.value = question;
            this.sendMessage();
        }
    },

    async loadStats() {
        try {
            const [statusResponse, deptResponse] = await Promise.all([
                axios.get('/status'),
                axios.get('/departments')
            ]);
            
            const status = statusResponse.data;
            const departments = deptResponse.data;
            
            const statsDiv = document.getElementById('stats');
            if (!statsDiv) return;
            
            const totalEmployees = departments.reduce((sum, dept) => sum + dept.count, 0);
            
            statsDiv.innerHTML = `
                <div class="text-sm space-y-2">
                    <div class="flex justify-between">
                        <span>👥 Employés</span>
                        <span class="font-medium">${totalEmployees}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>🏛️ Départements</span>
                        <span class="font-medium">${departments.length}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>📄 Documents</span>
                        <span class="font-medium">${status.documents_indexed}</span>
                    </div>
                    <div class="mt-2 pt-2 border-t">
                        <span class="text-xs text-green-600">✅ Système opérationnel</span>
                    </div>
                </div>
            `;
            
        } catch (error) {
            console.error('Erreur chargement stats:', error);
            const statsDiv = document.getElementById('stats');
            if (statsDiv) {
                statsDiv.innerHTML = '<div class="text-sm text-red-500">Erreur de chargement</div>';
            }
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialisation
ChatManager.init();

// Export global pour compatibilité
window.ChatManager = ChatManager;

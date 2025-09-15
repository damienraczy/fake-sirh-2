# static/js/chat.js
// Variables globales
let messageCount = 0;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
});

// Envoyer un message
async function sendMessage() {
    const input = document.getElementById('userInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Afficher le message utilisateur
    addMessage('user', question);
    input.value = '';
    
    // Afficher le loading
    showLoading(true);
    
    try {
        const response = await axios.post('/query', {
            question: question,
            include_sources: true
        });
        
        // Afficher la réponse
        addMessage('assistant', response.data.answer, response.data);
        
    } catch (error) {
        addMessage('assistant', 'Désolé, une erreur s\'est produite: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Ajouter un message à l'interface
function addMessage(role, content, metadata = null) {
    const messagesDiv = document.getElementById('messages');
    
    // Supprimer le message de bienvenue si c'est le premier message
    if (messageCount === 0) {
        messagesDiv.innerHTML = '';
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `mb-4 ${role === 'user' ? 'text-right' : 'text-left'}`;
    
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
            ${content}
            ${metadataHtml}
        </div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    messageCount++;
}

// Afficher/masquer le loading
function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.classList.toggle('hidden', !show);
}

// Exemple rapide
function askExample(question) {
    document.getElementById('userInput').value = question;
    sendMessage();
}

// Charger les statistiques
async function loadStats() {
    try {
        const [statusResponse, deptResponse] = await Promise.all([
            axios.get('/status'),
            axios.get('/departments')
        ]);
        
        const status = statusResponse.data;
        const departments = deptResponse.data;
        
        const statsDiv = document.getElementById('stats');
        const totalEmployees = departments.reduce((sum, dept) => sum + dept.count, 0);
        
        statsDiv.innerHTML = `
            <div class="text-sm">
                <div class="font-medium">👥 ${totalEmployees} employés</div>
                <div class="font-medium">🏛️ ${departments.length} départements</div>
                <div class="font-medium">📄 ${status.documents_indexed} documents</div>
                <div class="mt-2 text-xs text-green-600">✅ Système opérationnel</div>
            </div>
        `;
        
    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

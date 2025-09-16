/* =============================================================================
   SIRH - JavaScript commun pour POC
   ============================================================================= */

// API Client simple
const SirhAPI = {
    baseURL: '',
    
    async get(endpoint) {
        try {
            const response = await axios.get(this.baseURL + endpoint);
            return response.data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },
    
    // Méthodes spécifiques
    getStats: () => SirhAPI.get('/api/stats'),
    getEmployees: (search = '') => SirhAPI.get(`/api/employees${search ? `?search=${encodeURIComponent(search)}` : ''}`),
    getEmployee: (id) => SirhAPI.get(`/api/employee/${id}`),
    getDepartments: () => SirhAPI.get('/api/departments'),
    getDepartmentEmployees: (id) => SirhAPI.get(`/api/department/${id}/employees`),
    getSkills: () => SirhAPI.get('/api/skills'),
    getSkillEmployees: (id) => SirhAPI.get(`/api/skill/${id}/employees`),
    getTraining: () => SirhAPI.get('/api/training'),
    getTrainingRecords: (id) => SirhAPI.get(`/api/training/${id}/records`),
    search: (query) => SirhAPI.get(`/api/search?q=${encodeURIComponent(query)}`)
};

// Utilitaires
const Utils = {
    // Formater une date
    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('fr-FR');
    },
    
    // Formater un nombre
    formatNumber(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    },
    
    // Classe CSS pour niveau de compétence
    getSkillLevelClass(level) {
        const classes = {
            'Beginner': 'skill-beginner',
            'Intermediate': 'skill-intermediate', 
            'Advanced': 'skill-advanced',
            'Expert': 'skill-expert'
        };
        return `badge ${classes[level] || 'badge-gray'}`;
    },
    
    // Classe CSS pour score de performance
    getScoreClass(score) {
        return `badge score-${score}`;
    },
    
    // Échapper le HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    // Afficher/masquer des éléments
    show(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) element.classList.remove('hidden');
    },
    
    hide(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) element.classList.add('hidden');
    },
    
    // Loading state
    showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="loading">
                    <div class="loading-spinner"></div>
                    <p class="mt-2">Chargement...</p>
                </div>
            `;
        }
    },
    
    // Message d'erreur
    showError(containerId, message = 'Erreur de chargement') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center">
                    <p class="badge badge-error">${message}</p>
                </div>
            `;
        }
    },
    
    // Message vide
    showEmpty(containerId, message = 'Aucune donnée') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center">
                    <p style="color: var(--gray-500);">${message}</p>
                </div>
            `;
        }
    }
};

// Gestionnaire de navigation active
const Navigation = {
    init() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            const href = link.getAttribute('href');
            if (href === currentPath || 
                (href !== '/' && currentPath.startsWith(href))) {
                link.classList.add('active');
            }
        });
    }
};

// Gestionnaire de recherche globale
const GlobalSearch = {
    init(inputId, resultsId) {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultsId);
        
        if (!input) return;
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch(input.value, resultsId);
            }
        });
        
        // Recherche automatique après 500ms
        let timeout;
        input.addEventListener('input', (e) => {
            clearTimeout(timeout);
            const query = e.target.value.trim();
            
            if (query.length >= 2) {
                timeout = setTimeout(() => {
                    this.performSearch(query, resultsId);
                }, 500);
            } else if (results) {
                Utils.hide(results);
            }
        });
    },
    
    async performSearch(query, resultsId) {
        if (!query.trim()) return;
        
        const resultsContainer = document.getElementById(resultsId);
        if (!resultsContainer) return;
        
        try {
            Utils.showLoading(resultsId);
            Utils.show(resultsContainer);
            
            const data = await SirhAPI.search(query);
            this.displayResults(data, resultsId);
            
        } catch (error) {
            console.error('Erreur recherche:', error);
            Utils.showError(resultsId, 'Erreur de recherche');
        }
    },
    
    displayResults(data, resultsId) {
        const container = document.getElementById(resultsId);
        if (!container) return;
        
        if (data.results.length === 0) {
            Utils.showEmpty(resultsId, 'Aucun résultat trouvé');
            return;
        }
        
        const html = data.results.map(result => {
            const icon = this.getTypeIcon(result.type);
            const url = this.getResultUrl(result);
            
            return `
                <div style="border: 1px solid var(--gray-100); border-radius: 0.375rem; padding: 1rem; margin-bottom: 0.5rem;">
                    <a href="${url}" style="text-decoration: none; color: inherit;">
                        <div class="flex">
                            <span style="margin-right: 0.75rem; font-size: 1.25rem;">${icon}</span>
                            <div>
                                <div style="font-weight: 500; color: var(--gray-900);">${Utils.escapeHtml(result.name)}</div>
                                <div style="font-size: 0.875rem; color: var(--gray-500);">${Utils.escapeHtml(result.detail || '')}</div>
                            </div>
                        </div>
                    </a>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    },
    
    getTypeIcon(type) {
        const icons = {
            employee: '👤',
            skill: '🎯', 
            training: '🎓',
            department: '🏛️'
        };
        return icons[type] || '📄';
    },
    
    getResultUrl(result) {
        switch (result.type) {
            case 'employee': return `/employee/${result.id}`;
            case 'skill': return `/skills#skill-${result.id}`;
            case 'training': return `/training#training-${result.id}`;
            case 'department': return `/departments#dept-${result.id}`;
            default: return '#';
        }
    }
};

// Gestionnaire de tableaux
const TableManager = {
    create(containerId, data, columns, options = {}) {
        const container = document.getElementById(containerId);
        if (!container || !data.length) {
            if (container) Utils.showEmpty(containerId, 'Aucune donnée à afficher');
            return;
        }
        
        const tableHtml = `
            <div class="table-container">
                <table class="table">
                    <thead>
                        <tr>
                            ${columns.map(col => `<th>${col.label}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(row => `
                            <tr>
                                ${columns.map(col => `
                                    <td>${this.renderCell(row, col)}</td>
                                `).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    },
    
    renderCell(row, column) {
        let value = row[column.key];
        
        if (column.render) {
            return column.render(value, row);
        }
        
        if (column.type === 'date') {
            return Utils.formatDate(value);
        }
        
        if (column.type === 'badge') {
            const className = column.badgeClass ? column.badgeClass(value) : 'badge-gray';
            return `<span class="badge ${className}">${Utils.escapeHtml(value || '-')}</span>`;
        }
        
        if (column.type === 'link') {
            const url = column.url ? column.url(row) : '#';
            return `<a href="${url}" style="color: var(--primary); text-decoration: none;">${Utils.escapeHtml(value || '-')}</a>`;
        }
        
        return Utils.escapeHtml(value || '-');
    }
};

// Initialisation globale
document.addEventListener('DOMContentLoaded', () => {
    Navigation.init();
});

// Export global
window.SirhAPI = SirhAPI;
window.Utils = Utils;
window.Navigation = Navigation;
window.GlobalSearch = GlobalSearch;
window.TableManager = TableManager;
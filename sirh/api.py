# =============================================================================
# sirh/api.py - API finale simple de consultation SIRH
# =============================================================================

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import sys
import os
from pathlib import Path
import argparse

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import get_config, load_config
from utils.database import get_connection
import sqlite3

# =============================================================================
# Configuration FastAPI
# =============================================================================

app = FastAPI(
    title="📋 SIRH Consultation",
    description="Interface simple de consultation des données SIRH",
    version="1.0.0"
)

# Templates et fichiers statiques
templates = Jinja2Templates(directory="sirh/templates")
app.mount("/static", StaticFiles(directory="sirh/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Utilitaires
# =============================================================================

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Exécute une requête SQL et retourne les résultats"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    finally:
        conn.close()

def get_template_config():
    """Configuration pour les templates"""
    config_path = os.getenv('FAKE_SIRH_2_CONFIG_FILE')
    load_config(config_path)
    config = get_config()
    return {
        'company_name': config['entreprise']['nom'],
        'company_sector': config['entreprise']['secteur']
    }

# =============================================================================
# Routes Web - Pages
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    config = get_template_config()
    return templates.TemplateResponse("index.html", {"request": request, "config": config})

@app.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request):
    config = get_template_config()
    return templates.TemplateResponse("employees.html", {"request": request, "config": config})

@app.get("/employee/{employee_id}", response_class=HTMLResponse)
async def employee_detail(request: Request, employee_id: int):
    config = get_template_config()
    return templates.TemplateResponse("employee_detail.html", {
        "request": request, 
        "config": config, 
        "employee_id": employee_id
    })

@app.get("/departments", response_class=HTMLResponse)
async def departments_page(request: Request):
    config = get_template_config()
    return templates.TemplateResponse("departments.html", {"request": request, "config": config})

@app.get("/skills", response_class=HTMLResponse)
async def skills_page(request: Request):
    config = get_template_config()
    return templates.TemplateResponse("skills.html", {"request": request, "config": config})

@app.get("/training", response_class=HTMLResponse)
async def training_page(request: Request):
    config = get_template_config()
    return templates.TemplateResponse("training.html", {"request": request, "config": config})

# =============================================================================
# API Routes - Données
# =============================================================================

@app.get("/api/stats")
async def get_basic_stats():
    """Statistiques de base"""
    stats = {}
    
    # Compter les employés
    result = execute_query("SELECT COUNT(*) as count FROM employee")
    stats['employees'] = result[0]['count']
    
    # Compter les départements
    result = execute_query("SELECT COUNT(*) as count FROM organizational_unit")
    stats['departments'] = result[0]['count']
    
    # Compter les compétences
    result = execute_query("SELECT COUNT(*) as count FROM skill")
    stats['skills'] = result[0]['count']
    
    # Compter les formations
    result = execute_query("SELECT COUNT(*) as count FROM training_program")
    stats['training_programs'] = result[0]['count']
    
    return stats

@app.get("/api/employees")
async def get_employees(search: Optional[str] = None, limit: int = 50):
    """Liste des employés"""
    query = """
        SELECT e.id, e.first_name, e.last_name, e.email, e.hire_date,
               p.title as position, ou.name as department
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
    """
    
    params = ()
    if search:
        query += " WHERE e.first_name LIKE ? OR e.last_name LIKE ? OR e.email LIKE ?"
        search_param = f"%{search}%"
        params = (search_param, search_param, search_param)
    
    query += " ORDER BY e.last_name, e.first_name LIMIT ?"
    params = params + (limit,)
    
    return execute_query(query, params)

@app.get("/api/employee/{employee_id}")
async def get_employee_detail(employee_id: int):
    """Détail d'un employé"""
    
    # Info de base
    employee = execute_query("""
        SELECT e.id, e.first_name, e.last_name, e.email, e.hire_date,
               p.title as position, ou.name as department,
               m.first_name || ' ' || m.last_name as manager_name
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        LEFT JOIN employee m ON e.manager_id = m.id
        WHERE e.id = ?
    """, (employee_id,))
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employé non trouvé")
    
    # Compétences
    skills = execute_query("""
        SELECT s.name, s.category, es.level
        FROM skill s
        JOIN employee_skill es ON s.id = es.skill_id
        WHERE es.employee_id = ?
        ORDER BY s.category, s.name
    """, (employee_id,))
    
    # Formations
    training = execute_query("""
        SELECT tp.name, tr.completion_date, tr.score, tr.satisfaction_rating
        FROM training_record tr
        JOIN training_program tp ON tr.training_program_id = tp.id
        WHERE tr.employee_id = ?
        ORDER BY tr.completion_date DESC
    """, (employee_id,))
    
    # Performance
    performance = execute_query("""
        SELECT evaluation_year, score, comments
        FROM performance_review
        WHERE employee_id = ?
        ORDER BY evaluation_year DESC
    """, (employee_id,))
    
    # Équipe (si manager)
    team = execute_query("""
        SELECT id, first_name, last_name, email
        FROM employee
        WHERE manager_id = ?
        ORDER BY last_name, first_name
    """, (employee_id,))
    
    return {
        'employee': employee[0],
        'skills': skills,
        'training': training,
        'performance': performance,
        'team': team
    }

@app.get("/api/departments")
async def get_departments():
    """Liste des départements"""
    return execute_query("""
        SELECT ou.id, ou.name, ou.description,
               COUNT(a.employee_id) as employee_count
        FROM organizational_unit ou
        LEFT JOIN assignment a ON ou.id = a.unit_id AND a.end_date IS NULL
        GROUP BY ou.id, ou.name, ou.description
        ORDER BY ou.name
    """)

@app.get("/api/department/{department_id}/employees")
async def get_department_employees(department_id: int):
    """Employés d'un département"""
    return execute_query("""
        SELECT e.id, e.first_name, e.last_name, e.email, p.title
        FROM employee e
        JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        WHERE a.unit_id = ?
        ORDER BY e.last_name, e.first_name
    """, (department_id,))

@app.get("/api/skills")
async def get_skills():
    """Liste des compétences"""
    return execute_query("""
        SELECT s.id, s.name, s.category,
               COUNT(es.employee_id) as employee_count
        FROM skill s
        LEFT JOIN employee_skill es ON s.id = es.skill_id
        GROUP BY s.id, s.name, s.category
        ORDER BY s.category, s.name
    """)

@app.get("/api/skill/{skill_id}/employees")
async def get_skill_employees(skill_id: int):
    """Employés ayant une compétence"""
    return execute_query("""
        SELECT e.id, e.first_name, e.last_name, es.level, ou.name as department
        FROM employee e
        JOIN employee_skill es ON e.id = es.employee_id
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        WHERE es.skill_id = ?
        ORDER BY 
            CASE es.level
                WHEN 'Expert' THEN 4
                WHEN 'Advanced' THEN 3
                WHEN 'Intermediate' THEN 2
                WHEN 'Beginner' THEN 1
                ELSE 0
            END DESC,
            e.last_name
    """, (skill_id,))

@app.get("/api/training")
async def get_training_programs():
    """Liste des programmes de formation"""
    return execute_query("""
        SELECT tp.id, tp.name, tp.description, tp.duration_hours, tp.cost, tp.provider,
               COUNT(tr.id) as completion_count
        FROM training_program tp
        LEFT JOIN training_record tr ON tp.id = tr.training_program_id
        GROUP BY tp.id, tp.name, tp.description, tp.duration_hours, tp.cost, tp.provider
        ORDER BY tp.name
    """)

@app.get("/api/training/{program_id}/records")
async def get_training_records(program_id: int):
    """Enregistrements d'une formation"""
    return execute_query("""
        SELECT e.first_name, e.last_name, tr.completion_date, tr.score, tr.satisfaction_rating
        FROM training_record tr
        JOIN employee e ON tr.employee_id = e.id
        WHERE tr.training_program_id = ?
        ORDER BY tr.completion_date DESC
    """, (program_id,))

@app.get("/api/search")
async def search(q: str = Query(..., min_length=2)):
    """Recherche simple"""
    results = []
    
    # Recherche employés
    employees = execute_query("""
        SELECT 'employee' as type, id, first_name || ' ' || last_name as name, email as detail
        FROM employee
        WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?
        LIMIT 10
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    results.extend(employees)
    
    # Recherche compétences
    skills = execute_query("""
        SELECT 'skill' as type, id, name, category as detail
        FROM skill
        WHERE name LIKE ?
        LIMIT 10
    """, (f"%{q}%",))
    results.extend(skills)
    
    # Recherche formations
    training = execute_query("""
        SELECT 'training' as type, id, name, provider as detail
        FROM training_program
        WHERE name LIKE ? OR description LIKE ?
        LIMIT 10
    """, (f"%{q}%", f"%{q}%"))
    results.extend(training)
    
    return {'query': q, 'results': results}

if __name__ == "__main__":
    import uvicorn

    ap = argparse.ArgumentParser(description="Interface SIRH")
    # ap.add_argument("steps", nargs='*', help="Étapes (0-7)", default=['0','1','2','3','4','5','6'])
    ap.add_argument("--yaml", default="config.yaml", help="Config YAML")
    ap.add_argument("--port", type=int, default=8001, help="Port API")
    
    args = ap.parse_args()

    os.environ['FAKE_SIRH_2_CONFIG_FILE'] = args.yaml

    uvicorn.run(app, host="127.0.0.1", port=8001)
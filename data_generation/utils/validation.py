# =============================================================================
# utils/validation.py
# =============================================================================

from core.database import get_connection

def validate_database():
    """
    Valide la cohérence de la base de données générée
    """
    print("Validation de la cohérence de la base de données...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    checks = []
    
    # Vérification hiérarchie
    cursor.execute("SELECT COUNT(*) FROM employee WHERE manager_id IS NULL")
    dg_count = cursor.fetchone()[0]
    checks.append(("DG unique", dg_count == 1))
    
    # Vérification cycles hiérarchiques
    cursor.execute("""
        WITH RECURSIVE hierarchy AS (
            SELECT id, manager_id, 0 as level
            FROM employee WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, e.manager_id, h.level + 1
            FROM employee e
            JOIN hierarchy h ON e.manager_id = h.id
            WHERE h.level < 10
        )
        SELECT COUNT(*) FROM employee WHERE id NOT IN (SELECT id FROM hierarchy)
    """)
    orphans = cursor.fetchone()[0]
    checks.append(("Pas de cycles hiérarchiques", orphans == 0))
    
    # Vérification affectations uniques
    cursor.execute("""
        SELECT employee_id, COUNT(*) as active_assignments
        FROM assignment 
        WHERE end_date IS NULL 
        GROUP BY employee_id 
        HAVING COUNT(*) > 1
    """)
    multiple_assignments = cursor.fetchall()
    checks.append(("Affectations uniques par employé", len(multiple_assignments) == 0))
    
    # Vérification cohérence temporelle
    cursor.execute("""
        SELECT COUNT(*) FROM assignment 
        WHERE start_date > end_date AND end_date IS NOT NULL
    """)
    invalid_dates = cursor.fetchone()[0]
    checks.append(("Cohérence temporelle affectations", invalid_dates == 0))
    
    # Affichage des résultats
    print("\nRésultats de validation:")
    all_passed = True
    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {check_name}: {status}")
        if not passed:
            all_passed = False
    
    conn.close()
    
    if all_passed:
        print("\n✓ Toutes les validations sont passées avec succès")
    else:
        print("\n⚠ Certaines validations ont échoué")
    
    return all_passed

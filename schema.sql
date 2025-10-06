CREATE TABLE IF NOT EXISTS employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hire_date DATE NOT NULL,
    manager_id INTEGER,
    conciousness INTEGER, -- de 1 à 5
    cooperation INTEGER, -- de 1 à 5
    flexibility INTEGER, -- de 1 à 5
    FOREIGN KEY (manager_id) REFERENCES employee(id)
);

CREATE TABLE IF NOT EXISTS organizational_unit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS position (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    unit_id INTEGER, -- Clé étrangère vers organizational_unit
    reports_to_position_id INTEGER, -- Lien hiérarchique (auto-référence)
    level TEXT, -- Ex: Executive, Manager, Junior
    FOREIGN KEY (unit_id) REFERENCES organizational_unit (id),
    FOREIGN KEY (reports_to_position_id) REFERENCES position (id)

);

CREATE TABLE IF NOT EXISTS assignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    unit_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (position_id) REFERENCES position(id),
    FOREIGN KEY (unit_id) REFERENCES organizational_unit(id)
);

CREATE TABLE IF NOT EXISTS skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_skill (
    employee_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    level TEXT NOT NULL,
    PRIMARY KEY (employee_id, skill_id),
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (skill_id) REFERENCES skill(id)
);

CREATE TABLE IF NOT EXISTS goal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignee_id INTEGER NOT NULL,
    assigner_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    evaluation_year INTEGER NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (assignee_id) REFERENCES employee(id),
    FOREIGN KEY (assigner_id) REFERENCES employee(id)
);

CREATE TABLE IF NOT EXISTS performance_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    evaluation_year INTEGER NOT NULL,
    score INTEGER NOT NULL,
    comments TEXT,
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (reviewer_id) REFERENCES employee(id)
);

CREATE TABLE IF NOT EXISTS training_program (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    duration_hours INTEGER,
    cost REAL,
    provider TEXT
);

CREATE TABLE IF NOT EXISTS training_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    training_program_id INTEGER NOT NULL,
    completion_date DATE NOT NULL,
    score INTEGER,
    satisfaction_rating INTEGER,
    comments TEXT,
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (training_program_id) REFERENCES training_program(id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_employee_id INTEGER NOT NULL,
    to_employee_id INTEGER NOT NULL,
    feedback_type TEXT NOT NULL,
    content TEXT NOT NULL,
    feedback_date DATE NOT NULL,
    context TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (from_employee_id) REFERENCES employee(id),
    FOREIGN KEY (to_employee_id) REFERENCES employee(id)
);

CREATE TABLE IF NOT EXISTS document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    document_type TEXT NOT NULL,
    uri TEXT NOT NULL,
    creation_date DATE NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_employee_manager ON employee(manager_id);
CREATE INDEX IF NOT EXISTS idx_assignment_employee ON assignment(employee_id);
CREATE INDEX IF NOT EXISTS idx_assignment_active ON assignment(employee_id, end_date);
CREATE INDEX IF NOT EXISTS idx_feedback_to_employee ON feedback(to_employee_id);
CREATE INDEX IF NOT EXISTS idx_document_employee ON document(employee_id);

import sqlite3
import os

from src.core.config import DB_PATH

def initialize_db():
    """Creates the database and the tasks table with financial columns."""
    os.makedirs("data", exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Wipe the old Sprint 1 table clean to apply the new schema
        cursor.execute("DROP TABLE IF EXISTS tasks") 
        cursor.execute('''
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_days INTEGER,
                dependency_id INTEGER,
                planned_value REAL,  -- NEW: Budgeted cost for EVM
                actual_cost REAL,    -- NEW: Money spent so far
                FOREIGN KEY (dependency_id) REFERENCES tasks (id)
            )
        ''')
        conn.commit()
    print(f"[OK] Database initialized at {DB_PATH}")

def seed_data():
    """Seeds the database with a sample schedule including financial data."""
    tasks = [
        # task_name, status, duration, dep_id, planned_value, actual_cost
        ('Site Grading', 'Completed', 5, None, 5000.0, 5200.0),      # Over budget
        ('Foundation Pour', 'In Progress', 3, 1, 10000.0, 11000.0),  # Over budget
        ('Framing', 'Pending', 14, 2, 25000.0, 0.0),
        ('Roofing', 'Pending', 7, 3, 15000.0, 0.0)
    ]
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO tasks (task_name, status, duration_days, dependency_id, planned_value, actual_cost) VALUES (?, ?, ?, ?, ?, ?)", 
            tasks
        )
        conn.commit()
    print("[OK] Sample EVM project data seeded.")

if __name__ == "__main__":
    initialize_db()
    seed_data()
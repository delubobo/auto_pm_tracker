import os

# DB_PATH is used by the raw sqlite3 consumers (cpm.py, services.py, database.py)
DB_PATH = os.getenv("DB_PATH", "data/project_schedule.db")

# DATABASE_URL is used by SQLAlchemy ORM (src/core/db.py)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Guard for the seed-demo admin endpoint
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

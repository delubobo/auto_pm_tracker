from sqlalchemy import Column, Float, Integer, String, Text

from src.core.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    duration_days = Column(Integer)
    dependency_id = Column(Integer, nullable=True)  # legacy single-predecessor FK
    planned_value = Column(Float)
    actual_cost = Column(Float)

    # Phase 2 additions
    predecessor_ids = Column(Text, nullable=False, server_default="[]")
    start_date = Column(String, nullable=True)        # ISO 8601 text
    percent_complete = Column(Float, server_default="0.5")
    project_id = Column(Integer, nullable=True)       # future multi-project support
    task_type = Column(String, nullable=False, server_default="'Task'")
    assignee = Column(String, nullable=True)

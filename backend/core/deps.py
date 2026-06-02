"""FastAPI dependencies"""
from core.database import get_db

# Re-export for convenience
get_db_session = get_db

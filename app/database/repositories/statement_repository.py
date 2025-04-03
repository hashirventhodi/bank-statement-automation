from app.database.db import get_db
from app.models.statement import Statement

def add_statement(statement_data):
    with get_db() as db:
        stmt = Statement(**statement_data)
        db.add(stmt)
        db.commit()
        db.refresh(stmt)
        return stmt

def get_statement(stmt_id):
    with get_db() as db:
        return db.query(Statement).filter(Statement.id == stmt_id).first()

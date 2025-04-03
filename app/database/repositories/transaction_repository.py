from app.database.db import get_db
from app.models.transaction import Transaction

def add_transaction(transaction_data):
    with get_db() as db:
        txn = Transaction(**transaction_data)
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

def get_transaction(txn_id):
    with get_db() as db:
        return db.query(Transaction).filter(Transaction.id == txn_id).first()

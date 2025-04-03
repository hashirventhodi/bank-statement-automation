def validate_transaction(transaction):
    """
    Validate a transaction record. For example, check that required fields exist.
    """
    required_fields = ["date", "amount"]
    for field in required_fields:
        if field not in transaction or transaction[field] is None:
            return False
    return True

def validate_transactions(transactions):
    return [txn for txn in transactions if validate_transaction(txn)]

def normalize_transaction(transaction):
    """
    Normalize a single transaction record.
    Example: standardize date formats, clean description text, etc.
    """
    # Placeholder normalization logic
    transaction["normalized"] = True
    return transaction

def normalize_transactions(transactions):
    return [normalize_transaction(txn) for txn in transactions]

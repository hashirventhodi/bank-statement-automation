from app.core.parsers.transaction_parser import parse_transactions

def test_transaction_parser():
    raw_transactions = [{"date": "01/01/2020", "amount": 100.0, "description": "Test transaction"}]
    parsed = parse_transactions(raw_transactions)
    assert parsed[0].get("parsed") is True

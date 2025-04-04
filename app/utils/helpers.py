from typing import Any, Dict, List, Optional
import json
from datetime import datetime
import hashlib
import re

def clean_string(text: str) -> str:
    """Clean and normalize text string."""
    if not text:
        return ""
    
    # Remove special characters and excess whitespace
    text = re.sub(r'[^\w\s\-.,&/]', ' ', text)
    text = ' '.join(text.split())
    return text.strip()

def format_amount(amount: float) -> str:
    """Format amount with thousand separators and 2 decimal places."""
    try:
        return f"{amount:,.2f}"
    except:
        return str(amount)

def parse_date(date_str: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """Parse date string using multiple formats."""
    if not formats:
        formats = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%y",
            "%y-%m-%d"
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None

def generate_transaction_hash(transaction: Dict[str, Any]) -> str:
    """Generate unique hash for a transaction."""
    # Create a string combining key transaction attributes
    hash_string = f"{transaction.get('date', '')}{transaction.get('amount', '')}"
    hash_string += f"{transaction.get('description', '')}{transaction.get('transaction_type', '')}"
    
    # Generate hash
    return hashlib.md5(hash_string.encode()).hexdigest()

def detect_duplicates(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect potential duplicate transactions."""
    seen_hashes = {}
    result = []
    
    for tx in transactions:
        tx_hash = generate_transaction_hash(tx)
        
        if tx_hash in seen_hashes:
            # Mark as duplicate
            tx["is_duplicate"] = True
            # Add reference to original transaction
            tx["duplicate_of"] = seen_hashes[tx_hash]
        else:
            tx["is_duplicate"] = False
            seen_hashes[tx_hash] = tx.get("id") or len(result)
        
        result.append(tx)
    
    return result

def validate_amount(amount_str: str) -> Optional[float]:
    """Validate and convert amount string to float."""
    try:
        # Remove currency symbols and thousand separators
        cleaned = re.sub(r'[^\d.-]', '', str(amount_str))
        return float(cleaned)
    except:
        return None

def extract_reference_number(description: str) -> Optional[str]:
    """Extract reference number from transaction description."""
    patterns = [
        r'ref:?\s*([A-Za-z0-9]+)',
        r'ref[er]*[en]*ce\s*:?\s*([A-Za-z0-9]+)',
        r'txn\s*(?:id|no)\s*:?\s*([A-Za-z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def calculate_running_balance(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate running balance for a list of transactions."""
    balance = 0.0
    result = []
    
    # Sort transactions by date
    sorted_tx = sorted(transactions, key=lambda x: x.get('date', ''))
    
    for tx in sorted_tx:
        amount = float(tx.get('amount', 0))
        if tx.get('transaction_type') == 'credit':
            balance += amount
        else:
            balance -= amount
        
        tx['running_balance'] = round(balance, 2)
        result.append(tx)
    
    return result

def summarize_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics for transactions."""
    summary = {
        "total_count": len(transactions),
        "credit_count": 0,
        "debit_count": 0,
        "total_credit": 0.0,
        "total_debit": 0.0,
        "net_change": 0.0,
        "date_range": {
            "start": None,
            "end": None
        }
    }
    
    dates = []
    for tx in transactions:
        amount = float(tx.get('amount', 0))
        if tx.get('transaction_type') == 'credit':
            summary['credit_count'] += 1
            summary['total_credit'] += amount
        else:
            summary['debit_count'] += 1
            summary['total_debit'] += amount
        
        if tx.get('date'):
            dates.append(tx['date'])
    
    if dates:
        summary['date_range']['start'] = min(dates)
        summary['date_range']['end'] = max(dates)
    
    summary['net_change'] = round(summary['total_credit'] - summary['total_debit'], 2)
    
    return summary
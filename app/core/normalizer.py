from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import pandas as pd
from app.utils.logger import logger

class TransactionNormalizer:
    """Normalizes and standardizes transaction data."""
    
    def __init__(self):
        self.common_keywords = {
            'ATM': ['atm', 'cash withdrawal'],
            'TRANSFER': ['transfer', 'trf', 'xfer'],
            'SALARY': ['salary', 'pay', 'payroll'],
            'BILL_PAYMENT': ['bill pay', 'utility', 'electricity', 'water', 'gas'],
            'CARD_PAYMENT': ['pos', 'purchase', 'card', 'shop'],
            'INTEREST': ['int', 'interest'],
            'INVESTMENT': ['invest', 'mf', 'mutual fund', 'shares'],
            'LOAN': ['emi', 'loan', 'mortgage'],
            'TAX': ['tax', 'gst', 'vat', 'tds'],
            'FEE': ['fee', 'charge', 'commission']
        }
    
    def normalize_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of normalized transaction dictionaries
        """
        normalized = []
        
        for tx in transactions:
            try:
                normalized_tx = self.normalize_transaction(tx)
                if normalized_tx:
                    normalized.append(normalized_tx)
            except Exception as e:
                logger.error(f"Error normalizing transaction: {str(e)}")
                continue
        
        return normalized
    
    def normalize_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a single transaction."""
        if not transaction:
            return None
            
        try:
            normalized = transaction.copy()
            
            # Normalize date
            if "date" in normalized:
                normalized["date"] = self._normalize_date(normalized["date"])
            
            # Normalize description
            if "description" in normalized:
                normalized["description"] = self._normalize_description(normalized["description"])
            
            # Normalize amount
            if "amount" in normalized:
                normalized["amount"] = self._normalize_amount(normalized["amount"])
            
            # Normalize balance
            if "balance" in normalized:
                normalized["balance"] = self._normalize_amount(normalized["balance"])
            
            # Add normalized category if not present
            if "bank_category" not in normalized or not normalized["bank_category"]:
                normalized["bank_category"] = self._categorize_transaction(normalized)
            
            # Add normalized reference if not present
            if "reference_number" not in normalized or not normalized["reference_number"]:
                normalized["reference_number"] = self._extract_reference(normalized)
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error in transaction normalization: {str(e)}")
            return None
    
    def _normalize_date(self, date_value: Any) -> str:
        """Normalize date to standard format (DD/MM/YYYY)."""
        if not date_value:
            return None
            
        try:
            if isinstance(date_value, (datetime, pd.Timestamp)):
                return date_value.strftime("%d/%m/%Y")
            
            # Try parsing string date
            date_formats = [
                "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y",
                "%d/%m/%y", "%y-%m-%d", "%d-%b-%Y", "%d %b %Y"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(date_value), fmt).strftime("%d/%m/%Y")
                except:
                    continue
            
            return str(date_value)
            
        except Exception as e:
            logger.error(f"Error normalizing date: {str(e)}")
            return str(date_value)
    
    def _normalize_description(self, description: str) -> str:
        """Normalize transaction description."""
        if not description:
            return ""
            
        desc = str(description)
        
        # Remove extra whitespace
        desc = ' '.join(desc.split())
        
        # Remove common noise
        noise_patterns = [
            r'\s+(?:limited|ltd|pvt|private)\b',  # Common company suffixes
            r'\b[A-Z0-9]{20,}\b',                 # Long reference numbers
            r'\s{2,}',                            # Multiple spaces
            r'[^\w\s\-.,&/]'                      # Special characters
        ]
        
        for pattern in noise_patterns:
            desc = re.sub(pattern, ' ', desc, flags=re.IGNORECASE)
        
        # Capitalize first letter of each word
        desc = desc.title()
        
        # Remove leading/trailing whitespace
        return desc.strip()
    
    def _normalize_amount(self, amount: Any) -> float:
        """Normalize amount to float."""
        if not amount:
            return None
            
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            
            # Remove currency symbols and comma
            amount_str = str(amount)
            amount_str = re.sub(r'[^\d.-]', '', amount_str)
            
            return float(amount_str)
            
        except Exception as e:
            logger.error(f"Error normalizing amount: {str(e)}")
            return None
    
    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """Categorize transaction based on description keywords."""
        if not transaction.get("description"):
            return "UNKNOWN"
            
        desc = str(transaction["description"]).lower()
        
        for category, keywords in self.common_keywords.items():
            if any(keyword.lower() in desc for keyword in keywords):
                return category
        
        return "OTHERS"
    
    def _extract_reference(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Extract reference number from transaction description."""
        if not transaction.get("description"):
            return None
            
        desc = str(transaction["description"])
        
        # Common reference patterns
        ref_patterns = [
            r'ref[er]*[en]*ce\s*:?\s*([A-Za-z0-9]+)',
            r'txn\s*(?:id|no)\s*:?\s*([A-Za-z0-9]+)',
            r'utr\s*:?\s*([A-Za-z0-9]+)'
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
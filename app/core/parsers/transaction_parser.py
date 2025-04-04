from typing import Dict, List, Any, Optional
import re
from datetime import datetime
import pandas as pd
from app.models.transaction import TransactionType
from app.utils.logger import logger

class TransactionParser:
    """Base class for parsing bank statement transactions."""
    
    def __init__(self, template: Optional[Dict] = None):
        self.template = template
    
    def parse(self, raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse raw transaction data into standardized format.
        
        Args:
            raw_transactions (List[Dict]): List of raw transaction dictionaries
            
        Returns:
            List[Dict]: Parsed and normalized transactions
        """
        parsed_transactions = []
        
        for raw_tx in raw_transactions:
            try:
                parsed_tx = self._parse_transaction(raw_tx)
                if parsed_tx:
                    parsed_transactions.append(parsed_tx)
            except Exception as e:
                logger.error(f"Error parsing transaction: {str(e)}")
                continue
        
        return parsed_transactions
    
    def _parse_transaction(self, raw_tx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single transaction using template if available."""
        if not raw_tx:
            return None
            
        try:
            parsed_tx = {
                "date": None,
                "description": None,
                "amount": None,
                "transaction_type": None,
                "balance": None,
                "reference_number": None,
                "raw_description": raw_tx.get("description", ""),
                "bank_category": None,
                "confidence_score": 1.0
            }
            
            # Use template if available
            if self.template:
                return self._parse_with_template(raw_tx, parsed_tx)
            
            # Generic parsing
            return self._parse_generic(raw_tx, parsed_tx)
            
        except Exception as e:
            logger.error(f"Error in transaction parsing: {str(e)}")
            return None
    
    def _parse_with_template(self, raw_tx: Dict[str, Any], parsed_tx: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transaction using bank-specific template."""
        template_data = self.template
        
        # Date parsing
        if "date" in raw_tx:
            try:
                date_format = template_data.get("date_format", "%d/%m/%Y")
                if isinstance(raw_tx["date"], (datetime, pd.Timestamp)):
                    parsed_tx["date"] = raw_tx["date"].strftime(date_format)
                else:
                    parsed_tx["date"] = datetime.strptime(str(raw_tx["date"]), date_format).strftime(date_format)
            except:
                parsed_tx["date"] = str(raw_tx["date"])
        
        # Amount and transaction type
        if "transaction_type" in raw_tx:
            parsed_tx["transaction_type"] = raw_tx["transaction_type"]
        elif "debit" in raw_tx and "credit" in raw_tx:
            if raw_tx["debit"] and float(str(raw_tx["debit"]).replace(',', '')) > 0:
                parsed_tx["amount"] = float(str(raw_tx["debit"]).replace(',', ''))
                parsed_tx["transaction_type"] = TransactionType.DEBIT
            elif raw_tx["credit"] and float(str(raw_tx["credit"]).replace(',', '')) > 0:
                parsed_tx["amount"] = float(str(raw_tx["credit"]).replace(',', ''))
                parsed_tx["transaction_type"] = TransactionType.CREDIT
        elif "amount" in raw_tx:
            amount = float(str(raw_tx["amount"]).replace(',', ''))
            parsed_tx["amount"] = abs(amount)
            parsed_tx["transaction_type"] = TransactionType.CREDIT if amount >= 0 else TransactionType.DEBIT
        
        # Description
        if "description" in raw_tx:
            parsed_tx["description"] = self._clean_description(raw_tx["description"], template_data)
        
        # Balance
        if "balance" in raw_tx:
            try:
                parsed_tx["balance"] = float(str(raw_tx["balance"]).replace(',', ''))
            except:
                pass
        
        # Reference number
        if "reference_number" in raw_tx:
            parsed_tx["reference_number"] = raw_tx["reference_number"]
        else:
            # Try to extract reference number from description using template pattern
            ref_pattern = template_data.get("reference_pattern")
            if ref_pattern and parsed_tx["raw_description"]:
                match = re.search(ref_pattern, parsed_tx["raw_description"])
                if match:
                    parsed_tx["reference_number"] = match.group(1)
        
        # Bank category
        if "category" in raw_tx:
            parsed_tx["bank_category"] = raw_tx["category"]
        else:
            # Try to categorize using template rules
            category_rules = template_data.get("category_rules", {})
            for category, patterns in category_rules.items():
                if any(re.search(pattern, parsed_tx["raw_description"], re.IGNORECASE) 
                      for pattern in patterns):
                    parsed_tx["bank_category"] = category
                    break
        
        return parsed_tx
    
    def _parse_generic(self, raw_tx: Dict[str, Any], parsed_tx: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transaction using generic rules."""
        # Date parsing
        if "date" in raw_tx:
            try:
                if isinstance(raw_tx["date"], (datetime, pd.Timestamp)):
                    parsed_tx["date"] = raw_tx["date"].strftime("%d/%m/%Y")
                else:
                    # Try common date formats
                    date_formats = [
                        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y",
                        "%d/%m/%y", "%y-%m-%d", "%d-%b-%Y", "%d %b %Y"
                    ]
                    for fmt in date_formats:
                        try:
                            parsed_tx["date"] = datetime.strptime(str(raw_tx["date"]), fmt).strftime("%d/%m/%Y")
                            break
                        except:
                            continue
                    if not parsed_tx["date"]:
                        parsed_tx["date"] = str(raw_tx["date"])
            except:
                parsed_tx["date"] = str(raw_tx["date"])
        
        # Amount and transaction type
        if "transaction_type" in raw_tx:
            parsed_tx["transaction_type"] = raw_tx["transaction_type"]
        elif "debit" in raw_tx and "credit" in raw_tx:
            if raw_tx["debit"] and float(str(raw_tx["debit"]).replace(',', '')) > 0:
                parsed_tx["amount"] = float(str(raw_tx["debit"]).replace(',', ''))
                parsed_tx["transaction_type"] = TransactionType.DEBIT
            elif raw_tx["credit"] and float(str(raw_tx["credit"]).replace(',', '')) > 0:
                parsed_tx["amount"] = float(str(raw_tx["credit"]).replace(',', ''))
                parsed_tx["transaction_type"] = TransactionType.CREDIT
        elif "amount" in raw_tx:
            amount = float(str(raw_tx["amount"]).replace(',', ''))
            parsed_tx["amount"] = abs(amount)
            parsed_tx["transaction_type"] = TransactionType.CREDIT if amount >= 0 else TransactionType.DEBIT
        
        # Description
        if "description" in raw_tx:
            parsed_tx["description"] = self._clean_description(raw_tx["description"])
        
        # Balance
        if "balance" in raw_tx:
            try:
                parsed_tx["balance"] = float(str(raw_tx["balance"]).replace(',', ''))
            except:
                pass
        
        # Try to extract reference number from description
        if parsed_tx["raw_description"]:
            ref_patterns = [
                r'ref:?\s*([A-Za-z0-9]+)',
                r'ref[er]*[en]*ce\s*:?\s*([A-Za-z0-9]+)',
                r'txn\s*(?:id|no)\s*:?\s*([A-Za-z0-9]+)'
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, parsed_tx["raw_description"], re.IGNORECASE)
                if match:
                    parsed_tx["reference_number"] = match.group(1)
                    break
        
        return parsed_tx
    
    def _clean_description(self, description: str, template_data: Dict = None) -> str:
        """Clean and normalize transaction description."""
        if not description:
            return ""
            
        desc = str(description)
        
        # Remove common noise patterns
        noise_patterns = [
            r'\b[A-Z0-9]{20,}\b',  # Long alphanumeric sequences
            r'\s{2,}',             # Multiple spaces
            r'[^\w\s\-.,&/]'       # Special characters except some common ones
        ]
        
        if template_data:
            # Add bank-specific patterns
            noise_patterns.extend(template_data.get("description_cleanup_patterns", []))
        
        for pattern in noise_patterns:
            desc = re.sub(pattern, ' ', desc)
        
        # Clean up whitespace
        desc = ' '.join(desc.split())
        
        return desc.strip()
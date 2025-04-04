from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from app.models.transaction import Transaction, TransactionStatus
from app.utils.logger import logger

class TransactionValidator:
    """Validates extracted transaction data for accuracy and consistency."""
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize validator.
        
        Args:
            tolerance: Floating point comparison tolerance
        """
        self.tolerance = tolerance
    
    def validate_transactions(self, 
                            transactions: List[Dict[str, Any]], 
                            opening_balance: Optional[float] = None,
                            closing_balance: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Validate a list of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            opening_balance: Expected opening balance
            closing_balance: Expected closing balance
            
        Returns:
            List of validated transactions with status updates
        """
        if not transactions:
            return []
            
        validated = []
        running_balance = opening_balance
        
        # Sort transactions by date
        sorted_txs = sorted(transactions, 
                          key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y') 
                          if isinstance(x['date'], str) else x['date'])
        
        # Track seen transaction references to detect duplicates
        seen_references = set()
        
        for tx in sorted_txs:
            try:
                validation_result = self._validate_transaction(tx, running_balance)
                
                if validation_result["is_valid"]:
                    tx["status"] = TransactionStatus.VERIFIED
                else:
                    tx["status"] = TransactionStatus.FAILED
                    tx["validation_errors"] = validation_result["errors"]
                
                # Check for duplicates
                if tx.get("reference_number"):
                    if tx["reference_number"] in seen_references:
                        tx["is_duplicate"] = True
                        tx["validation_errors"] = tx.get("validation_errors", []) + ["Duplicate reference number"]
                    else:
                        seen_references.add(tx["reference_number"])
                
                # Update running balance
                if validation_result["is_valid"] and tx.get("amount"):
                    if tx["transaction_type"] == "credit":
                        running_balance = (running_balance or 0) + tx["amount"]
                    else:
                        running_balance = (running_balance or 0) - tx["amount"]
                
                validated.append(tx)
                
            except Exception as e:
                logger.error(f"Error validating transaction: {str(e)}")
                tx["status"] = TransactionStatus.FAILED
                tx["validation_errors"] = [str(e)]
                validated.append(tx)
        
        # Validate final balance if provided
        if closing_balance is not None and running_balance is not None:
            if not self._is_close(running_balance, closing_balance):
                logger.warning(f"Final balance mismatch: expected {closing_balance}, got {running_balance}")
                for tx in validated:
                    tx["validation_errors"] = tx.get("validation_errors", []) + ["Statement balance mismatch"]
        
        return validated
    
    def _validate_transaction(self, transaction: Dict[str, Any], running_balance: Optional[float] = None) -> Dict[str, Any]:
        """Validate a single transaction."""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Required fields validation
        required_fields = ["date", "amount", "transaction_type"]
        for field in required_fields:
            if field not in transaction or transaction[field] is None:
                result["errors"].append(f"Missing required field: {field}")
                result["is_valid"] = False
        
        # Date validation
        if "date" in transaction and transaction["date"]:
            if not self._is_valid_date(transaction["date"]):
                result["errors"].append("Invalid date format")
                result["is_valid"] = False
        
        # Amount validation
        if "amount" in transaction and transaction["amount"] is not None:
            try:
                amount = float(transaction["amount"])
                if amount <= 0:
                    result["errors"].append("Amount must be positive")
                    result["is_valid"] = False
            except ValueError:
                result["errors"].append("Invalid amount value")
                result["is_valid"] = False
        
        # Balance validation if provided
        if running_balance is not None and "balance" in transaction and transaction["balance"] is not None:
            expected_balance = running_balance
            if transaction["transaction_type"] == "credit":
                expected_balance += float(transaction["amount"])
            else:
                expected_balance -= float(transaction["amount"])
                
            if not self._is_close(expected_balance, float(transaction["balance"])):
                result["errors"].append("Running balance mismatch")
                result["is_valid"] = False
        
        # Transaction type validation
        if "transaction_type" in transaction:
            if transaction["transaction_type"] not in ["credit", "debit"]:
                result["errors"].append("Invalid transaction type")
                result["is_valid"] = False
        
        return result
    
    def _is_valid_date(self, date_value: Any) -> bool:
        """Check if date is valid."""
        try:
            if isinstance(date_value, (datetime, pd.Timestamp)):
                return True
                
            datetime.strptime(str(date_value), "%d/%m/%Y")
            return True
        except:
            return False
    
    def _is_close(self, a: float, b: float) -> bool:
        """Compare float values with tolerance."""
        return abs(a - b) <= self.tolerance

class StatementValidator:
    """Validates entire bank statements for consistency and completeness."""
    
    def __init__(self, transaction_validator: TransactionValidator):
        self.transaction_validator = transaction_validator
    
    def validate_statement(self, statement_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an entire bank statement.
        
        Args:
            statement_data: Dictionary containing statement metadata and transactions
            
        Returns:
            Validation results dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metadata": statement_data.get("metadata", {}),
            "transactions": []
        }
        
        try:
            # Validate metadata
            metadata_validation = self._validate_metadata(statement_data.get("metadata", {}))
            result["errors"].extend(metadata_validation["errors"])
            result["warnings"].extend(metadata_validation["warnings"])
            
            # Validate transactions
            transactions = statement_data.get("transactions", [])
            opening_balance = statement_data.get("metadata", {}).get("opening_balance")
            closing_balance = statement_data.get("metadata", {}).get("closing_balance")
            
            validated_transactions = self.transaction_validator.validate_transactions(
                transactions,
                opening_balance,
                closing_balance
            )
            
            result["transactions"] = validated_transactions
            
            # Check for statement-level issues
            statement_checks = self._validate_statement_consistency(validated_transactions, statement_data)
            result["errors"].extend(statement_checks["errors"])
            result["warnings"].extend(statement_checks["warnings"])
            
            # Update final validation status
            result["is_valid"] = len(result["errors"]) == 0
            
        except Exception as e:
            logger.error(f"Error validating statement: {str(e)}")
            result["is_valid"] = False
            result["errors"].append(str(e))
        
        return result
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate statement metadata."""
        result = {
            "errors": [],
            "warnings": []
        }
        
        # Required fields
        required_fields = ["account_number", "statement_period"]
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                result["errors"].append(f"Missing required metadata: {field}")
        
        # Validate statement period
        if "statement_period" in metadata and metadata["statement_period"]:
            try:
                # Assuming period format: "DD/MM/YYYY to DD/MM/YYYY"
                start_date, end_date = metadata["statement_period"].split(" to ")
                start = datetime.strptime(start_date.strip(), "%d/%m/%Y")
                end = datetime.strptime(end_date.strip(), "%d/%m/%Y")
                
                if end < start:
                    result["errors"].append("Invalid statement period: end date before start date")
                    
                # Check for unreasonable periods
                period_days = (end - start).days
                if period_days > 366:
                    result["warnings"].append("Unusually long statement period")
                elif period_days < 25:
                    result["warnings"].append("Unusually short statement period")
                    
            except Exception as e:
                result["errors"].append(f"Invalid statement period format: {str(e)}")
        
        # Validate balances
        if "opening_balance" in metadata and "closing_balance" in metadata:
            try:
                opening = float(metadata["opening_balance"])
                closing = float(metadata["closing_balance"])
                
                if opening < 0:
                    result["warnings"].append("Negative opening balance")
                if closing < 0:
                    result["warnings"].append("Negative closing balance")
                    
            except ValueError:
                result["errors"].append("Invalid balance values")
        
        return result
    
    def _validate_statement_consistency(self, transactions: List[Dict[str, Any]], 
                                     statement_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Check overall statement consistency."""
        result = {
            "errors": [],
            "warnings": []
        }
        
        if not transactions:
            result["warnings"].append("No transactions found in statement")
            return result
            
        # Check transaction date range
        metadata = statement_data.get("metadata", {})
        if "statement_period" in metadata:
            try:
                start_date, end_date = metadata["statement_period"].split(" to ")
                period_start = datetime.strptime(start_date.strip(), "%d/%m/%Y")
                period_end = datetime.strptime(end_date.strip(), "%d/%m/%Y")
                
                tx_dates = [datetime.strptime(tx["date"], "%d/%m/%Y") for tx in transactions 
                           if isinstance(tx.get("date"), str)]
                
                if tx_dates:
                    min_tx_date = min(tx_dates)
                    max_tx_date = max(tx_dates)
                    
                    if min_tx_date < period_start:
                        result["errors"].append("Transactions found before statement period")
                    if max_tx_date > period_end:
                        result["errors"].append("Transactions found after statement period")
                        
            except Exception as e:
                logger.error(f"Error checking transaction date range: {str(e)}")
        
        # Check for gaps in transaction dates
        tx_dates = sorted([datetime.strptime(tx["date"], "%d/%m/%Y") for tx in transactions 
                         if isinstance(tx.get("date"), str)])
        
        if tx_dates:
            for i in range(len(tx_dates) - 1):
                gap = (tx_dates[i+1] - tx_dates[i]).days
                if gap > 7:  # Warning for gaps longer than a week
                    result["warnings"].append(f"Unusual gap in transactions: {gap} days")
        
        # Check for unusual patterns
        credit_count = sum(1 for tx in transactions if tx.get("transaction_type") == "credit")
        debit_count = sum(1 for tx in transactions if tx.get("transaction_type") == "debit")
        
        if credit_count == 0:
            result["warnings"].append("No credit transactions found")
        if debit_count == 0:
            result["warnings"].append("No debit transactions found")
        
        # Check for duplicate dates with identical amounts
        tx_signatures = {}
        for tx in transactions:
            sig = (tx.get("date"), tx.get("amount"), tx.get("transaction_type"))
            if None not in sig:
                if sig in tx_signatures:
                    result["warnings"].append("Potential duplicate transactions found")
                    break
                tx_signatures[sig] = True
        
        return result
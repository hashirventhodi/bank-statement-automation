from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.models.transaction import Transaction
from app.models.account import Account

class AccountingSoftwareIntegration(ABC):
    """Abstract base class for accounting software integrations."""
    
    @abstractmethod
    def export_transactions(self, transactions: List[Transaction], account: Account) -> Dict[str, Any]:
        """Export transactions to accounting software."""
        pass
    
    @abstractmethod
    def verify_connection(self) -> bool:
        """Verify connection to accounting software."""
        pass
    
    @abstractmethod
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of available accounts."""
        pass
    
    @abstractmethod
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get list of available transaction categories."""
        pass

class IntegrationFactory:
    """Factory for creating integration instances."""
    
    @staticmethod
    def create_integration(software_type: str, config: Dict[str, Any]) -> AccountingSoftwareIntegration:
        """
        Create appropriate integration instance.
        
        Args:
            software_type: Type of accounting software
            config: Configuration dictionary
            
        Returns:
            Integration instance
        """
        if software_type.lower() == "tally":
            from app.integrations.tally_integration import TallyIntegration
            return TallyIntegration(config)
        # Add other integrations as needed
        raise ValueError(f"Unsupported software type: {software_type}")

class AccountingSoftwareError(Exception):
    """Custom exception for accounting software integration errors."""
    pass